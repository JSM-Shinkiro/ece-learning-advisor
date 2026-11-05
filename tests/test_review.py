"""Reviewer input integrity, unscored exports, and reproducible offline metrics."""

from datetime import datetime, timedelta, timezone
import json

import pytest
from pydantic import ValidationError

from src.catalog import corpus_hash
from src.evaluation import load_suite
from src.review import (MAX_REVIEW_BYTES, ReviewForm, ReviewPacket, blank_form,
                        fingerprint, load_review_json, make_packet, packet_hash, packet_markdown,
                        score_review, validate_packet)

NOW = datetime(2026, 11, 5, 23, 0, tzinfo=timezone.utc)


@pytest.fixture
def packet(catalog):
    return make_packet(catalog, now=NOW)


def fixture_form(packet, catalog):
    """Existing authored labels are controlled test data, never human results."""
    form = blank_form(packet)
    form.reviewer_id = "fixture-only"
    form.reviewer_role = "controlled_fixture"
    form.reviewed_at = NOW + timedelta(minutes=1)
    labels = {case.case_id: case.relevance for case in load_suite(catalog).retrieval_cases}
    for case in form.cases:
        case.relevance = dict(labels[case.case_id])
    return form


def rehash(data):
    data["packet_hash"] = packet_hash(data)
    return ReviewPacket.model_validate(data)


def test_export_omits_previous_judgments_rankings_and_interpretation(packet):
    assert len(packet.questions) == 16 and len(packet.evidence) == 10
    assert packet.question_origin == "existing_development_questions"
    assert packet.source_suite_hash
    export = packet.model_dump_json()
    for name in ['"relevance"', '"split"', '"rationale"', '"scores"', '"ranked_chunk_ids"', '"added_terms"']:
        assert name not in export
    form = blank_form(packet)
    assert form.reviewer_id is form.reviewer_role is form.reviewed_at is None
    assert all(grade is None for case in form.cases for grade in case.relevance.values())
    assert list(form.cases[0].relevance) == packet.questions[0].candidate_ids


def test_candidate_shuffle_is_repeatable_and_independent_of_retriever(catalog, packet, monkeypatch):
    monkeypatch.setattr("src.review.Retriever", lambda *a, **k: pytest.fail("Review export must never rank evidence"))
    same = make_packet(catalog, seed=7, now=NOW)
    different = make_packet(catalog, seed=8, now=NOW)
    assert same == packet and different.packet_hash != packet.packet_hash
    assert different.questions[0].candidate_ids != packet.questions[0].candidate_ids
    assert all(set(q.candidate_ids) == {e.chunk_id for e in packet.evidence} for q in packet.questions)
    assert len({tuple(q.candidate_ids) for q in packet.questions}) > 1


def test_custom_questions_do_not_claim_verified_origin_or_load_previous_labels(catalog, monkeypatch):
    monkeypatch.setattr("src.review.load_suite", lambda *a: pytest.fail("Custom questions must not load old labels"))
    custom = make_packet(catalog, questions=[{"case_id": "new-question", "query": "How do interrupts work?"}], now=NOW)
    assert custom.question_origin == "custom_questions_unverified" and custom.source_suite_hash is None
    assert len(custom.questions) == 1


@pytest.mark.parametrize("questions", [[], [{"case_id": "q", "query": " "}],
    [{"case_id": "q", "query": "alpha"}, {"case_id": "q", "query": "beta"}],
    [{"case_id": "q1", "query": "Learn C"}, {"case_id": "q2", "query": " LEARN   c "}],
    [{"case_id": "q", "query": "x" * 1201}],
    [{"case_id": "q", "query": "valid", "relevance": {"hint": 3}}],
    [{"case_id": "../unsafe", "query": "valid"}]])
def test_invalid_or_duplicate_questions_fail(catalog, questions):
    with pytest.raises(ValueError):
        make_packet(catalog, questions=questions, now=NOW)


@pytest.mark.parametrize("seed", [-1, 2**32, True, 1.2])
def test_invalid_shuffle_seed_fails(catalog, seed):
    with pytest.raises((ValueError, TypeError)):
        make_packet(catalog, seed=seed, now=NOW)


def test_guide_includes_exact_evidence_and_source_links_with_no_answer_key(packet):
    guide = packet_markdown(packet)
    assert "not ranked" in guide and "not held out" in guide and "null means unfinished" in guide
    for chunk in packet.evidence:
        assert chunk.chunk_id in guide and chunk.text in guide
    for source in packet.sources:
        assert source.url in guide
    assert "ranked_chunk_ids" not in guide and "reference_reviews" not in guide


def test_packet_fingerprint_detects_changes_to_questions(packet, catalog):
    packet.questions[0].query = "Altered question"
    with pytest.raises(ValueError, match="fingerprint"):
        validate_packet(packet, catalog)


@pytest.mark.parametrize("change", ["summary", "freshness", "rule", "source_url"])
def test_stale_review_snapshot_is_rejected(packet, catalog, change):
    if change == "summary": catalog.records[0].summary = "A changed summary"
    elif change == "freshness": catalog.sources[0].last_checked_at = NOW
    elif change == "rule": catalog.records[0].rule.note = "Changed policy"
    else: catalog.sources[0].url = "https://catalog.arizona.edu/courses/9999999"
    with pytest.raises(ValueError, match="snapshot"):
        validate_packet(packet, catalog)


@pytest.mark.parametrize("change", ["text", "url", "missing_candidate", "duplicate_candidate", "wrong_candidate", "origin"])
def test_rehashing_altered_payload_cannot_bypass_catalog_or_candidate_binding(packet, catalog, change):
    data = packet.model_dump(mode="json")
    if change == "text": data["evidence"][0]["text"] = "An unrelated evidence payload"
    elif change == "url": data["sources"][0]["url"] = "https://example.com/wrong"
    elif change == "missing_candidate": data["questions"][0]["candidate_ids"].pop()
    elif change == "duplicate_candidate": data["questions"][0]["candidate_ids"][0] = data["questions"][0]["candidate_ids"][1]
    elif change == "wrong_candidate": data["questions"][0]["candidate_ids"][0] = "missing-evidence"
    else: data["source_suite_hash"] = "f" * 64
    with pytest.raises(ValueError):
        validate_packet(rehash(data), catalog)


def test_incomplete_form_has_no_scores(packet, catalog):
    with pytest.raises(ValueError, match="reviewer"):
        score_review(catalog, packet, blank_form(packet))


@pytest.mark.parametrize("change", ["packet", "missing_case", "duplicate_case", "unknown_case", "missing_grade", "unknown_chunk", "null_grade", "timestamp", "alias", "role"])
def test_invalid_review_cannot_be_scored(packet, catalog, change):
    form = fixture_form(packet, catalog)
    if change == "packet": form.packet_hash = "f" * 64
    elif change == "missing_case": form.cases.pop()
    elif change == "duplicate_case": form.cases[0] = form.cases[1]
    elif change == "unknown_case": form.cases[0].case_id = "unrelated"
    elif change == "missing_grade": form.cases[0].relevance.pop(next(iter(form.cases[0].relevance)))
    elif change == "unknown_chunk": form.cases[0].relevance["missing"] = 3
    elif change == "null_grade": form.cases[0].relevance[next(iter(form.cases[0].relevance))] = None
    elif change == "timestamp": form.reviewed_at = NOW - timedelta(seconds=1)
    elif change == "alias": form.reviewer_id = None
    else: form.reviewer_role = None
    with pytest.raises(ValueError):
        score_review(catalog, packet, form)


@pytest.mark.parametrize("grade", [True, -1, 4, 2.5, "2", 2.0])
def test_grades_require_explicit_integers(packet, catalog, grade):
    form = fixture_form(packet, catalog)
    form.cases[0].relevance[next(iter(form.cases[0].relevance))] = grade
    with pytest.raises(ValidationError):
        score_review(catalog, packet, form)


def test_timezone_is_required_for_completion(packet, catalog):
    data = fixture_form(packet, catalog).model_dump(mode="json")
    data["reviewed_at"] = "2026-11-05T23:01:00"
    with pytest.raises(ValidationError):
        ReviewForm.model_validate(data)


@pytest.mark.parametrize("k", [0, 101, True, "5"])
def test_invalid_cutoff_is_rejected_before_ranking(packet, catalog, monkeypatch, k):
    monkeypatch.setattr("src.review.Retriever", lambda *a: pytest.fail("Invalid input must not rank"))
    with pytest.raises(ValueError, match="cutoff"):
        score_review(catalog, packet, fixture_form(packet, catalog), k=k)


def test_offline_review_scoring_reproduces_old_metric_with_controlled_labels(packet, catalog, monkeypatch):
    def forbidden(*a, **k): pytest.fail("Review workflow must not use network or providers")
    monkeypatch.setattr("httpx.Client.send", forbidden)
    monkeypatch.setattr("src.providers.GeminiProvider", forbidden)
    before = corpus_hash(catalog)
    report = score_review(catalog, packet, fixture_form(packet, catalog))
    assert report["summary"]["recall"] == pytest.approx(.8229166666666666)
    assert report["summary"]["cases"] == 16
    assert report["reviewer"]["self_reported_role"] == "controlled_fixture"
    assert report["embedding_calls"] == report["generation_calls"] == report["source_refresh_calls"] == 0
    assert report["packet_hash"] == packet.packet_hash and report["corpus_hash"] == before == corpus_hash(catalog)
    assert "not authenticated" in report["limitations"]
    assert set(report["implementation"]) >= {"src/review.py", "src/retrieval.py", "src/query.py"}


def test_raw_and_expanded_treatments_use_same_completed_judgments(packet, catalog):
    form = fixture_form(packet, catalog)
    before = fingerprint(form)
    raw = score_review(catalog, packet, form)
    expanded = score_review(catalog, packet, form, query_mode="expanded")
    assert raw["review_hash"] == expanded["review_hash"] == before == fingerprint(form)
    assert expanded["summary"]["recall"] == pytest.approx(.9479166666666666)
    assert all(row["query_interpretation"] is None for row in raw["cases"])
    assert any(row["query_interpretation"]["added_terms"] for row in expanded["cases"])
    with pytest.raises(ValueError, match="raw or expanded"):
        score_review(catalog, packet, form, query_mode="unlisted")


def test_no_relevant_evidence_remains_visible_with_undefined_metric_counts(packet, catalog):
    form = fixture_form(packet, catalog)
    for case in form.cases:
        case.relevance = {key: 0 for key in case.relevance}
    report = score_review(catalog, packet, form)
    summary = report["summary"]
    assert summary["cases"] == summary["queries_without_relevant_evidence"] == 16
    assert summary["precision"] == summary["precision_ceiling"] == 0
    assert summary["recall"] is summary["reciprocal_rank"] is summary["ndcg"] is None
    assert summary["defined_cases"] == {"precision": 16, "recall": 0, "reciprocal_rank": 0, "ndcg": 0}


def test_unknown_reviewer_independence_is_never_inferred(packet, catalog):
    form = fixture_form(packet, catalog)
    form.reviewer_role = "independent_reviewer"
    report = score_review(catalog, packet, form)
    assert report["reviewer"]["self_reported_role"] == "independent_reviewer"
    assert report["question_origin"] == "existing_development_questions"
    assert "not held out" in report["limitations"] and "not authenticated" in report["limitations"]


@pytest.mark.parametrize("content", ['{"x": 1, "x": 2}', '{"case": {"grade": 1, "grade": 3}}', '{bad json}', '"\udcff"'])
def test_malformed_and_duplicate_key_json_fails(tmp_path, content):
    path = tmp_path / "input.json"
    path.write_bytes(content.encode("utf-8", errors="surrogatepass"))
    with pytest.raises(ValueError):
        load_review_json(path)


def test_oversized_input_is_bounded(tmp_path):
    path = tmp_path / "too-big.json"
    path.write_bytes(b" " * (MAX_REVIEW_BYTES + 1))
    with pytest.raises(ValueError, match="size limit"):
        load_review_json(path)


def test_cli_roundtrip_rejects_blank_grades_and_preserves_existing_files(monkeypatch, tmp_path, catalog):
    from scripts import review_retrieval as cli
    dest = tmp_path / "packet"
    monkeypatch.setattr("sys.argv", ["review", "prepare", "--output", str(dest)])
    assert cli.main() == 0
    packet_path = dest / "packet.json"
    template_path = dest / "review_template.json"
    original = template_path.read_bytes()
    assert cli.main() == 2 and template_path.read_bytes() == original
    output = tmp_path / "score.json"
    command = ["review", "score", "--packet", str(packet_path), "--review", str(template_path), "--output", str(output)]
    monkeypatch.setattr("sys.argv", command)
    assert cli.main() == 2 and not output.exists()
    packet = ReviewPacket.model_validate(load_review_json(packet_path))
    form = fixture_form(packet, catalog)
    form.reviewed_at = datetime.now(timezone.utc) + timedelta(seconds=1)
    completed = dest / "review_fixture.json"
    completed.write_text(form.model_dump_json(), encoding="utf-8")
    command[command.index("--review") + 1] = str(completed)
    assert cli.main() == 0
    report = json.loads(output.read_text())
    assert report["reviewer"]["self_reported_role"] == "controlled_fixture"
    before = output.read_bytes()
    assert cli.main() == 2 and output.read_bytes() == before
    assert template_path.read_bytes() == original


def test_cli_custom_questions_and_sanitized_failures(monkeypatch, tmp_path, capsys):
    from scripts import review_retrieval as cli
    source = tmp_path / "questions.json"
    source.write_text('[{"case_id":"custom-1","query":"What is a CPU?"}]')
    dest = tmp_path / "custom"
    monkeypatch.setattr("sys.argv", ["review", "prepare", "--questions", str(source), "--output", str(dest)])
    assert cli.main() == 0
    assert json.loads((dest / "packet.json").read_text())["question_origin"] == "custom_questions_unverified"
    private_input = "private-parser-input"
    source.write_text(private_input)
    assert cli.main() == 2
    assert private_input not in capsys.readouterr().err
