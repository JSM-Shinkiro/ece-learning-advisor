"""Authored domain-alias and end-to-end coverage regressions, not held-out data."""

import json
from pathlib import Path

import pytest

from src.catalog import build_evidence
from src.controller import run_advisor
from src.evaluation import evaluate_suite, load_suite, report_markdown
from src.models import Completion, StudentProfile
from src.planning import coverage_message
from src.query import MAX_ADDED_TERMS, QUERY_POLICY_VERSION, interpret_query
from src.retrieval import Retriever, tokenize
from src.service import build_query, recommend
from src.sources import CatalogRefresh

EXAMPLES = [
    ("train computers to pick out patterns from pictures", "ai_ml", "ECE425", "visual_learning"),
    ("Which classes help a computer recognize photographs?", "ai_ml", "ECE425", "visual_recognition"),
    ("I want image classification from photos", "ai_ml", "ECE425", "visual_recognition"),
    ("Can machines learn patterns in images?", "ai_ml", "ECE425", "visual_learning"),
    ("make a little board react when a button is pressed without polling", "embedded", "ECE372A", "board_events"),
    ("Teach a microcontroller to respond when a switch is pressed", "embedded", "ECE372A", "board_events"),
    ("How do I use GPIO on a small board?", "embedded", "ECE372A", "microcontroller_io"),
    ("Help me communicate over UART", "embedded", "ECE372A", "microcontroller_io"),
    ("Explain ADC readings", "embedded", "ECE372A", "microcontroller_io"),
    ("how a chip speaks with memory and executes machine instructions", "embedded", "ECE369A", "chip_execution"),
    ("CPU opcodes and RAM", "embedded", "ECE369A", "processor_execution"),
    ("Why does a processor have caches?", "embedded", "ECE369A", "processor_memory"),
    ("I want to learn to code from scratch", "ai_ml", "ECE101", "coding_foundations"),
    ("Where do I start with coding basics?", "ai_ml", "ECE101", "coding_foundations"),
    ("practice tensors minibatches optimization weights outside university coursework", "ai_ml", "ECE425", "tensor_practice"),
]
UNSUPPORTED = [
    "I want a marine biology degree and ocean fieldwork",
    "I want marathon training for a race",
    "Photography training with holiday pictures",
    "Instructions for cooking potato chips",
    "Baking chocolate chip cookies",
    "Travel by train with pictures of mountains",
    "Button decorations on a sewing board",
    "How to fix a camera shutter button",
    "Fashion model training",
    "Fashion models learn posing from pictures",
    "Strength training and weights at the gym",
    "Photo albums and holiday memories",
    "Wood board and button craft project",
    "Medical school anatomy and physiology",
    "GPIOLOGY UARTS and buttoning",
]


@pytest.mark.parametrize("question,career,code,alias", EXAMPLES)
def test_student_paraphrases_reach_relevant_evidence_and_cards(catalog, question, career, code, alias):
    profile = StudentProfile(career_id=career, programming_background="experienced")
    interpretation = interpret_query(question, catalog)
    assert alias in interpretation.matched_aliases
    assert interpretation.added_terms
    direct = Retriever(build_evidence(catalog)).keyword(interpretation.expand(question), limit=5)
    rid = f"uofa:{code}:2026-2027"
    assert rid in [h.record_id for h in direct]
    result = recommend(catalog, profile, question)
    assert not result.coverage_notice and rid in result.context.allowed_record_ids
    assert result.context.profile == profile and result.context.question == question
    assert result.trace["query_interpretation"] == interpretation.trace()
    assert result.trace["query_interpretation"]["version"] == QUERY_POLICY_VERSION
    assert all(term in result.context.query for term in interpretation.added_terms)
    assert not result.generation_complete and result.answer is None


@pytest.mark.parametrize("question", UNSUPPORTED)
def test_unrelated_topics_never_start_sources_or_a_provider(catalog, question):
    def forbidden(*args, **kwargs):
        pytest.fail("Unsupported wording must not initialize a provider or fetch sources")
    assert not interpret_query(question, catalog).matched_aliases
    result = run_advisor(catalog, StudentProfile(question=question), use_ai=True, api_key="fixture",
                         source_refresher=forbidden, provider_factory=forbidden)
    assert result.coverage_notice and result.context.allowed_record_ids == []
    assert result.trace["model_calls"] == 0
    assert result.trace["source_refresh"]["reason"] == "outside_supported_collection"


@pytest.mark.parametrize("question,career,code,alias", [EXAMPLES[0], EXAMPLES[4], EXAMPLES[9]])
def test_source_prefilter_and_generation_share_the_same_paraphrase_policy(catalog, fake_provider, tmp_path,
                                                                        question, career, code, alias):
    calls = []
    def refresh(active, profile, **kwargs):
        calls.append(profile.question)
        return CatalogRefresh(active.model_copy(deep=True))
    fake_provider.close = lambda: None
    result = run_advisor(catalog, StudentProfile(career_id=career, question=question), source_refresher=refresh,
        use_ai=True, api_key="fixture", method="keyword", provider_factory=lambda *a, **k: fake_provider,
        cache_dir=tmp_path)
    assert calls == [question] and result.generation_complete
    assert result.statement_validation_passed is True
    assert fake_provider.context is result.context
    assert f"uofa:{code}:2026-2027" in result.context.allowed_record_ids
    assert fake_provider.document_calls == 0


@pytest.mark.parametrize("question,code", [(EXAMPLES[0][0], "ECE425"), (EXAMPLES[4][0], "ECE372A"),
                                          (EXAMPLES[9][0], "ECE369A")])
def test_specific_exploring_question_keeps_its_course_and_novice_foundation(catalog, question, code):
    result = recommend(catalog, StudentProfile(career_id="exploring"), question)
    rid = f"uofa:{code}:2026-2027"
    assert result.context.allowed_record_ids[0] == "uofa:ECE101:2026-2027"
    assert rid in result.context.allowed_record_ids
    assert result.context.rule_results[rid].status == "unknown"
    assert result.context.suggested_phases[rid] != "next"


def test_completed_focus_course_cannot_be_recommended_again(catalog):
    profile = StudentProfile(career_id="embedded", completed=[Completion(course_code="ECE369A", grade="B")])
    result = recommend(catalog, profile, EXAMPLES[9][0])
    assert "uofa:ECE369A:2026-2027" not in result.context.allowed_record_ids


def test_aliases_do_not_switch_the_selected_career(catalog):
    result = recommend(catalog, StudentProfile(career_id="ai_ml"), EXAMPLES[4][0])
    assert result.context.profile.career_id == "ai_ml"
    assert "uofa:ECE372A:2026-2027" not in result.context.allowed_record_ids


def test_interest_only_paraphrase_is_supported_without_changing_the_profile(catalog):
    profile = StudentProfile(interests=EXAMPLES[0][0])
    before = profile.model_dump()
    result = recommend(catalog, profile)
    assert not result.coverage_notice and "visual_learning" in result.trace["query_interpretation"]["matched_aliases"]
    assert result.context.query.endswith("computer vision deep learning neural networks")
    assert profile.model_dump() == before


def test_explicit_unrelated_question_is_not_rescued_by_profile_interests(catalog):
    profile = StudentProfile(interests=EXAMPLES[0][0], experience="neural networks and GPIO")
    assert recommend(catalog, profile, UNSUPPORTED[0]).coverage_notice


def test_legitimate_computing_application_is_not_blocked_by_its_subject(catalog):
    question = "Train computers to recognize images of marine animals"
    assert not recommend(catalog, StudentProfile(), question).coverage_notice


def test_aliases_cannot_invent_coverage_missing_from_the_active_catalog(catalog):
    catalog.records = [r for r in catalog.records if r.record_id == "uofa:ECE101:2026-2027"]
    interpretation = interpret_query(EXAMPLES[0][0], catalog)
    assert interpretation.matched_aliases == () and interpretation.added_terms == ()
    assert coverage_message(catalog, StudentProfile(), EXAMPLES[0][0])


def test_terms_are_bounded_deduplicated_and_already_present_in_sources(catalog):
    text = " ".join(row[0] for row in EXAMPLES)
    interpretation = interpret_query(text, catalog)
    assert len(interpretation.added_terms) == MAX_ADDED_TERMS
    assert len(set(interpretation.added_terms)) == len(interpretation.added_terms)
    vocabulary = set(tokenize(" ".join(r.title + " " + r.summary + " " + " ".join(r.topics) for r in catalog.records)))
    assert all(set(tokenize(term)) <= vocabulary for term in interpretation.added_terms)
    assert interpretation == interpret_query(text.upper(), catalog)


def test_maximum_profile_reserves_query_room_for_aliases(catalog):
    question = EXAMPLES[0][0] + " " + "a" * (1200 - len(EXAMPLES[0][0]) - 1)
    profile = StudentProfile(interests="x" * 1500, experience="y" * 2000)
    query = build_query(catalog, profile, question)
    assert len(query) <= 5000
    assert query.endswith("computer vision deep learning neural networks")


def test_query_aliases_never_change_catalog_evidence_or_credits(catalog):
    before = catalog.model_dump()
    evidence = build_evidence(catalog)
    recommend(catalog, StudentProfile(), EXAMPLES[0][0])
    assert catalog.model_dump() == before and build_evidence(catalog) == evidence


def test_generic_requests_and_known_spaced_codes_still_work(catalog):
    for question in ["", "What should I learn next?", "ECE 425"]:
        result = recommend(catalog, StudentProfile(), question)
        assert result.context.allowed_record_ids and not result.coverage_notice
        assert not result.trace["query_interpretation"]["added_terms"]


def test_unknown_course_aliases_do_not_invent_a_course(catalog):
    result = recommend(catalog, StudentProfile(), "ECE499")
    assert result.coverage_notice and not result.context.allowed_record_ids


def test_exploring_retains_a_directly_named_course_and_its_condition_evidence(catalog):
    result = recommend(catalog, StudentProfile(career_id="exploring"), "Do I need both ECE101 and CSC110 before CSC120?")
    assert "uofa:CSC120:2026-2027" in result.context.allowed_record_ids
    assert any(e.chunk_id == "uofa:CSC120:2026-2027:rule:R1299-L40" for e in result.context.evidence)
    assert result.context.rule_results["uofa:CSC120:2026-2027"].status == "unknown"


def test_specific_source_wording_is_not_displaced_by_general_exploring_goals(catalog):
    result = recommend(catalog, StudentProfile(career_id="exploring"), "lists stacks queues trees searching sorting exceptions")
    assert "uofa:CSC120:2026-2027" in result.context.allowed_record_ids
    assert "uofa:ECE101:2026-2027" in result.context.allowed_record_ids
    assert result.trace["focused_record_ids"] == ["uofa:CSC120:2026-2027"]


@pytest.mark.parametrize("question", ["", "What should I learn next?"])
def test_general_exploration_keeps_both_directions(catalog, question):
    result = recommend(catalog, StudentProfile(career_id="exploring"), question)
    assert {"uofa:ECE425:2026-2027", "uofa:ECE372A:2026-2027"} <= set(result.context.allowed_record_ids)
    assert not result.trace["focused_record_ids"]


def test_raw_reference_metrics_and_labels_keep_the_original_identity(catalog):
    suite = load_suite(catalog)
    before = Path("data/evaluation/reviewed_v1.json").read_bytes()
    report = evaluate_suite(catalog, suite)
    baseline = json.loads(Path("docs/evidence/reviewed_evaluation_2026-11-03.json").read_text())
    assert report["retrieval_summary"] == baseline["retrieval_summary"]
    assert report["suite_hash"] == baseline["suite_hash"]
    assert report["query_mode"] == "raw"
    assert all(row["effective_query"] == row["query"] for row in report["retrieval_cases"])
    assert Path("data/evaluation/reviewed_v1.json").read_bytes() == before


def test_expanded_evaluation_keeps_original_queries_and_qualifies_tuning(catalog):
    report = evaluate_suite(catalog, load_suite(catalog), query_mode="expanded")
    row = next(r for r in report["retrieval_cases"] if r["case_id"] == "retrieval_pictures_paraphrase")
    assert row["query"] == EXAMPLES[0][0]
    assert row["effective_query"].startswith(row["query"])
    assert "computer vision" in row["effective_query"]
    assert report["query_mode"] == "expanded" and report["runtime_query_policy"] == QUERY_POLICY_VERSION
    assert "development tuning, not held-out validation" in report_markdown(report)
    assert report["generation_calls"] == report["source_refresh_calls"] == 0
    assert report["regression_checks_passed"]


def test_neural_comparison_uses_the_same_expanded_query_and_no_extra_calls(catalog, fake_provider, tmp_path):
    captured = []
    original = fake_provider.embed_query
    def record(query):
        captured.append(query)
        return original(query)
    fake_provider.embed_query = record
    def forbidden(*args):
        pytest.fail("The evaluator must not generate answers")
    fake_provider.generate = forbidden
    report = evaluate_suite(catalog, load_suite(catalog), methods=["semantic", "hybrid"], embedder=fake_provider,
        embedding_origin="controlled_fixture", query_mode="expanded", cache_dir=tmp_path)
    assert captured == [row["effective_query"] for row in report["retrieval_cases"] if row["method"] == "semantic"]
    assert report["embedding"]["query_calls"] == 16 and report["generation_calls"] == 0


def test_invalid_query_mode_fails_before_provider_calls(catalog, fake_provider):
    with pytest.raises(ValueError, match="raw or expanded"):
        evaluate_suite(catalog, load_suite(catalog), query_mode="unknown", embedder=fake_provider)
    assert fake_provider.document_calls == 0


def test_cli_exposes_expansion_as_a_separate_offline_measurement(catalog, monkeypatch, tmp_path):
    from scripts import evaluate_reviewed as cli
    output = tmp_path / "expanded.json"
    monkeypatch.setattr("sys.argv", ["evaluate_reviewed", "--query-mode", "expanded", "--output", str(output)])
    assert cli.main() == 0
    assert json.loads(output.read_text())["query_mode"] == "expanded"
