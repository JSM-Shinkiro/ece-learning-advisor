"""Reviewed phrase routing is request policy, not a new source of course facts."""

import json

import pytest
from pydantic import ValidationError

from src.controller import run_advisor
from src.discovery import DiscoveryPlan, load_discovery_plans, match_course_requests
from src.models import StudentProfile
from src.planning import coverage_message
from test_discovery_priority import added, priority_refresh, request_status


@pytest.mark.parametrize("text,code", [
    ("Introduction to Computer Programming I", "CSC110"),
    ("discrete mathematics for computer science i", "CSC144"),
    ("discrete math", "CSC144"),
    ("predicate logic", "CSC144"),
    ("Software Development", "CSC210"),
    ("unit testing", "CSC210"),
    ("version control", "CSC210"),
    ("Programming 2", "ECE201"),
    ("object-oriented programming", "ECE201"),
    ("OBJECT–ORIENTED   PROGRAMMING", "ECE201"),
    ("C++ programming", "ECE201"),
    ("data abstraction", "ECE201"),
    ("Basic Circuits", "ECE220"),
    ("circuit analysis", "ECE220"),
    ("phasors", "ECE220"),
    ("Digital Logic", "ECE274A"),
    ("register transfer language", "ECE274A"),
])
def test_reviewed_titles_and_topics_match_whole_phrases(text, code):
    result = match_course_requests(StudentProfile(question=text), load_discovery_plans())
    assert result.codes == [code] and result.phrases[code]


@pytest.mark.parametrize("text", ["metaphasors", "unit testings", "C programming", "C# programming",
    "logic programming software engineering math", "unit unrelated testing", "quantum chemistry"])
def test_substrings_broad_words_and_unreviewed_phrases_do_not_route(text):
    assert not match_course_requests(StudentProfile(question=text), load_discovery_plans()).codes


def test_explicit_codes_win_then_phrases_follow_mention_order_and_deduplicate():
    result = match_course_requests(StudentProfile(question="unit testing, phasors, ECE201, then design patterns"),
        load_discovery_plans())
    assert result.codes == ["ECE201", "CSC210", "ECE220"]
    assert result.phrases == {"CSC210": ["unit testing", "design patterns"], "ECE220": ["phasors"]}


def test_question_precedence_career_and_edition_constrain_phrase_matching():
    plans = load_discovery_plans()
    assert match_course_requests(StudentProfile(question=" ", interests="phasors"), plans).codes == ["ECE220"]
    assert not match_course_requests(StudentProfile(question="unrelated", interests="phasors"), plans).codes
    assert not match_course_requests(StudentProfile(career_id="embedded", question="unit testing"), plans).codes
    assert not match_course_requests(StudentProfile(catalog_version="2025-2026", question="phasors"), plans).codes


def test_combined_phrase_and_code_requests_keep_the_existing_mention_cap():
    question = " ".join("ECE" + str(i) for i in range(100, 116)) + " phasors"
    result = match_course_requests(StudentProfile(question=question), load_discovery_plans())
    assert len(result.codes) == 16 and result.truncated and not result.phrases


@pytest.mark.parametrize("phrases", [
    {"CSC499": ["heap analysis"]}, {"CSC210": ["programming"]}, {"CSC210": ["---"]},
    {"CSC210": ["unit testing", "UNIT-TESTING"]}, {"CSC210": ["x" * 81]},
    {"CSC210": ["topic number " + str(i) for i in range(9)]},
    {"CSC110": ["unit testing"], "CSC210": ["unit testing"]},
])
def test_phrases_need_specific_bounded_unambiguous_identity_bindings(phrases):
    data = load_discovery_plans()[0].model_dump(mode="json")
    data["course_phrases"] = phrases
    with pytest.raises(ValidationError):
        DiscoveryPlan.model_validate(data)


def test_ambiguous_phrases_across_programs_are_rejected(tmp_path):
    data = [plan.model_dump(mode="json") for plan in load_discovery_plans()]
    data[0]["course_phrases"]["CSC210"].append("basic circuits")
    path = tmp_path / "plans.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Ambiguous"):
        load_discovery_plans(path)


@pytest.mark.parametrize("phrase,code", [("phasors", "ECE220"), ("unit testing", "CSC210"),
    ("object-oriented programming", "ECE201")])
def test_phrase_reaches_sources_retrieval_and_grounded_generation(catalog, tmp_path, fake_provider, phrase, code):
    fake_provider.close = lambda: None
    def refresh(catalog, profile, **kwargs):
        return priority_refresh(catalog, tmp_path / "sources", profile)
    result = run_advisor(catalog, StudentProfile(question=phrase), source_refresher=refresh,
        use_ai=True, api_key="fixture", provider_factory=lambda *a, **k: fake_provider, cache_dir=tmp_path / "vectors")
    rid = "uofa:" + code + ":2026-2027"
    assert not result.coverage_notice and result.generation_complete and result.statement_validation_passed
    assert result.trace["focused_record_ids"] == [rid]
    assert code in result.trace["discovery_query_terms"] and code in result.context.query
    assert rid in result.context.allowed_record_ids
    assert result.context.rule_results[rid].status == "unknown"
    selection = result.trace["source_refresh"]["discovery_selection"]
    assert selection["selected"][0]["reason"] == "reviewed_phrase"
    assert selection["requests"][0]["status"] == "added"
    assert fake_provider.context.field_sources[rid]["summary"] == "catalog:" + code


def test_outside_saved_vocabulary_can_fetch_only_through_reviewed_phrase_policy(catalog, tmp_path):
    profile = StudentProfile(question="phasors")
    assert coverage_message(catalog, profile, profile.question, allow_course_discovery=True)
    calls = []
    def refresh(catalog, profile, **kwargs):
        calls.append(profile.question)
        return priority_refresh(catalog, tmp_path, profile)
    result = run_advisor(catalog, profile, source_refresher=refresh)
    assert calls == ["phasors"] and not result.coverage_notice


@pytest.mark.parametrize("options", [{"programs": {"ECEBSECE": 503}}, {"courses": {"0120881": 503}}])
def test_phrase_hint_cannot_bypass_a_failed_target_into_generation(catalog, tmp_path, options):
    def refresh(catalog, profile, **kwargs):
        return priority_refresh(catalog, tmp_path, profile, **options)
    def forbidden(*args, **kwargs):
        pytest.fail("No validated matching record exists for this phrase")
    result = run_advisor(catalog, StudentProfile(question="phasors"), source_refresher=refresh,
        use_ai=True, api_key="fixture", provider_factory=forbidden)
    assert result.coverage_notice and not result.context.allowed_record_ids


def test_phrase_does_not_change_career_source_scope(catalog, tmp_path):
    seen = []
    def refresh(catalog, profile, **kwargs):
        return priority_refresh(catalog, tmp_path, profile, seen=seen)
    result = run_advisor(catalog, StudentProfile(career_id="embedded", question="unit testing"), source_refresher=refresh)
    assert not any("/COSCBS/" in url for url in seen)
    assert "uofa:CSC210:2026-2027" not in result.context.allowed_record_ids


def test_offline_mode_does_not_turn_unfetched_phrase_hints_into_evidence(catalog):
    def forbidden(*args, **kwargs):
        pytest.fail("Unfetched phrase hints are not offline evidence")
    result = run_advisor(catalog, StudentProfile(question="phasors"), refresh_sources=False,
        use_ai=True, api_key="fixture", provider_factory=forbidden)
    assert result.coverage_notice and not result.context.evidence


def test_phrase_priority_uses_no_extra_slot_or_source_request(catalog, tmp_path):
    seen = []
    result = priority_refresh(catalog, tmp_path, StudentProfile(question="phasors and unit testing"), seen=seen)
    assert added(result) == ["ECE220", "CSC210", "CSC110"]
    assert len([url for url in seen if "/courses/" in url]) == 6
    assert len([url for url in seen if "/programs/" in url]) == 2


def test_alias_priority_recomputes_on_304_and_does_not_enter_public_caches(catalog, tmp_path):
    question = "routing-private-phrase-sentinel phasors"
    first = priority_refresh(catalog, tmp_path, StudentProfile(question=question), headers={"ETag": '"fixture"'})
    second = priority_refresh(catalog, tmp_path, StudentProfile(question="unit testing"),
        programs={"COSCBS": 304, "ECEBSECE": 304})
    assert added(first)[0] == "ECE220" and added(second)[0] == "CSC210"
    assert request_status(second, "CSC210") == "added"
    assert all("routing-private-phrase-sentinel" not in p.read_text() for p in tmp_path.rglob("*.json"))
