"""Current coursework stays separate from successful completions and next steps."""

import pytest

from src.catalog import load_runtime_catalog
from src.models import Completion, Rule, StudentProfile
from src.planning import needs_programming_foundations, requested_record_ids
from src.profiles import edit_profile, export_profile, import_profile, parse_current_courses
from src.rules import evaluate_course, evaluate_rule
from src.service import recommend
from src.session import apply_profile, choose_direction, complete_course, restore_profile


def test_current_course_is_not_recommended_again(catalog):
    result = recommend(catalog, StudentProfile(current_enrollment=["ECE101"]))
    assert "uofa:ECE101:2026-2027" not in result.context.allowed_record_ids


def test_course_cannot_be_both_current_and_completed():
    with pytest.raises(ValueError, match="both completed and currently taking"):
        StudentProfile(completed=[Completion(course_code="ECE101", grade="B")],
                       current_enrollment=["ECE 101"])


def test_current_courses_normalize_and_roundtrip_with_other_profile_fields():
    profile = StudentProfile(current_enrollment=[" ece 101 ", "math 129", "PHYS261h"],
        completed=[Completion(course_code="CSC110", grade="B")], consents=["recorded permission"])
    assert profile.current_enrollment == ["ECE101", "MATH129", "PHYS261H"]
    assert import_profile(export_profile(profile).encode()) == profile
    assert edit_profile(profile, interests="robotics").current_enrollment == profile.current_enrollment
    assert import_profile(b'{"career_id":"embedded"}').current_enrollment == []


@pytest.mark.parametrize("codes", [["ECE101", "ece 101"], ["ECE10"], ["ECE101:B"],
    ["<script>"], ["MATH 129 extra"], [""], ["ECE101", None],
    ["MATH" + str(number) for number in range(100, 201)]])
def test_invalid_or_ambiguous_current_histories_are_rejected_on_restore(codes):
    import json
    with pytest.raises(ValueError):
        import_profile(json.dumps({"current_enrollment": codes}).encode())


def test_manual_current_courses_accept_separators_without_recording_grades():
    assert parse_current_courses(" ece 101 ; MATH129\nPHYS 241, ") == ["ECE101", "MATH129", "PHYS241"]
    assert parse_current_courses(" , \n") == []
    with pytest.raises(ValueError):
        parse_current_courses("ECE101:B")


@pytest.mark.parametrize("career", ["ai_ml", "embedded", "exploring"])
@pytest.mark.parametrize("background", ["new", "experienced"])
def test_all_roadmap_paths_exclude_current_courses(catalog, career, background):
    profile = StudentProfile(career_id=career, programming_background=background,
        current_enrollment=["ECE101", "ECE425", "ECE372A"], question="ECE101 ECE425 ECE372A")
    result = recommend(catalog, profile, preferred_course_codes=["ECE101", "ECE425", "ECE372A"])
    assert result.context.allowed_record_ids
    assert not set(result.context.allowed_record_ids) & {
        "uofa:" + code + ":2026-2027" for code in profile.current_enrollment}
    assert not set(result.trace["focused_record_ids"]) & {
        "uofa:" + code + ":2026-2027" for code in profile.current_enrollment}
    assert requested_record_ids(catalog, profile, profile.current_enrollment) == []


@pytest.mark.parametrize("method", ["keyword", "semantic", "hybrid"])
def test_generator_receives_current_state_without_current_recommendations(catalog, fake_provider, tmp_path, method):
    profile = StudentProfile(current_enrollment=["ECE101"])
    result = recommend(catalog, profile, provider=fake_provider, method=method, cache_dir=tmp_path)
    assert result.generation_complete
    assert fake_provider.context.profile.current_enrollment == ["ECE101"]
    assert all(r.record_id != "uofa:ECE101:2026-2027" for r in result.answer.recommendations)
    # Current coursework can still be supporting source evidence for another course.
    assert "uofa:ECE101:2026-2027:overview" in {e.chunk_id for e in result.context.evidence}


@pytest.mark.parametrize("complete_history,expected", [(False, "unknown"), (True, "unsatisfied")])
def test_current_course_only_satisfies_an_explicit_concurrent_condition(complete_history, expected):
    profile = StudentProfile(current_enrollment=["ECE101"], history_complete=complete_history)
    assert needs_programming_foundations(profile)
    assert evaluate_rule(Rule(type="completed", course_code="ECE101", minimum_grade="C"), profile).status == expected
    assert evaluate_rule(Rule(type="completed_or_concurrent", course_code="ECE101"), profile).status == "satisfied"
    catalog = load_runtime_catalog()
    csc120 = next(r for r in catalog.records if r.code == "CSC120")
    assert evaluate_course(csc120, profile).status == expected
    assert evaluate_course(next(r for r in catalog.records if r.code == "ECE425"), profile).status == "unknown"


def test_finish_course_moves_status_clears_results_and_leaves_needed_grade_unknown(catalog):
    profile = StudentProfile(current_enrollment=["ECE101", "MATH129"], consents=["permission"])
    state = {"profile": profile, "current_courses": ["ECE101"], "current_course_text": "MATH129",
        "grade_ECE101": "A", **{key: object() for key in ["result", "jobs_cache", "job_result", "job_detail"]}}
    complete_course(state, "ece 101")
    updated = state["profile"]
    assert updated.current_enrollment == ["MATH129"]
    assert updated.completed == [Completion(course_code="ECE101")]
    assert updated.consents == ["permission"] and state["refresh_pending"]
    assert all(key not in state for key in ["result", "jobs_cache", "job_result", "job_detail",
        "current_courses", "current_course_text", "grade_ECE101"])
    csc120 = next(r for r in catalog.records if r.code == "CSC120")
    assert evaluate_course(csc120, updated).status == "unknown"
    graded = edit_profile(updated, completed=[Completion(course_code="ECE101", grade="B")])
    assert evaluate_course(csc120, graded).status == "satisfied"
    complete_course(state, "ECE101")
    assert state["profile"] == updated


def test_direction_restore_and_invalid_restore_keep_current_profile_consistent():
    profile = StudentProfile(current_enrollment=["ECE101", "MATH129"])
    state = {"profile": profile, "current_courses": ["stale"], "current_course_text": "stale"}
    choose_direction(state, "embedded")
    assert state["profile"].current_enrollment == profile.current_enrollment
    assert "current_courses" not in state and "current_course_text" not in state
    saved = export_profile(state["profile"]).encode()
    restore_profile(state, saved)
    before = dict(state)
    with pytest.raises(ValueError):
        restore_profile(state, b'{"current_enrollment":["ECE101", "ECE 101"]}')
    assert state == before
    apply_profile(state, edit_profile(state["profile"], current_enrollment=[]))
    assert any("Removed from currently taking" in note for note in state["profile_notices"])


def test_discovery_uses_download_slots_for_courses_outside_current_history(catalog, tmp_path):
    from test_ece_core import added, core_refresh
    profile = StudentProfile(career_id="embedded", current_enrollment=["ECE201", "ECE220", "ECE274A"],
        question="ECE310")
    seen = []
    result = core_refresh(catalog, tmp_path, profile, seen=seen)
    selection = result.trace()["discovery_selection"]
    assert selection["skipped_enrolled_codes"] == ["ECE201", "ECE220", "ECE274A"]
    assert selection["requests"][0]["status"] == "added"
    assert len(added(result)) == 3 and added(result)[0] == "ECE310"
    assert not set(added(result)) & set(profile.current_enrollment)
    assert len([url for url in seen if "/courses/" in url]) <= 8
    assert [item.course_code for item in profile.completed] == []


def test_explicit_current_course_can_supply_description_without_becoming_a_recommendation(catalog, tmp_path):
    from src.controller import run_advisor
    from test_ece_core import core_refresh
    profile = StudentProfile(career_id="embedded", current_enrollment=["ECE201"], question="ECE201")
    def refresh(catalog, profile, **kwargs):
        return core_refresh(catalog, tmp_path, profile)
    result = run_advisor(catalog, profile, source_refresher=refresh)
    request = result.trace["source_refresh"]["discovery_selection"]["requests"][0]
    assert request["status"] == "added" and request["coursework_status"] == "in_progress"
    course = next(r for r in result.catalog.records if r.code == "ECE201")
    assert course.record_id not in result.context.allowed_record_ids
    assert course.record_id not in result.trace["focused_record_ids"]


def test_saved_course_source_priority_retains_explicit_and_reviewed_checks(tmp_path):
    from src.discovery import load_discovery_plans
    from src.sources import MAX_SOURCES, refresh_catalog
    from test_runtime_catalog import runtime_client
    from test_sources import NOW
    catalog = load_runtime_catalog()
    seen = []
    profile = StudentProfile(career_id="embedded", current_enrollment=["ECE101", "ECE369A", "ECE372A"],
        question="ECE372A")
    with runtime_client(catalog, seen) as client:
        result = refresh_catalog(catalog, profile, discovery_plans=load_discovery_plans(),
            client=client, cache_dir=tmp_path, now=NOW)
    selection = result.trace()["course_check_selection"]
    assert selection["selected_codes"][0] == "ECE372A"
    assert selection["current_enrollment_codes"] == profile.current_enrollment
    assert len(selection["selected_codes"]) == MAX_SOURCES
    assert "ECE369A" in selection["snapshot_codes"]
    assert not set(selection["reviewed_rule_codes"]) - set(selection["selected_codes"])
    assert len([url for url in seen if "/courses/" in url]) == MAX_SOURCES
