"""Student interactions for current coursework; all sources/providers controlled."""

import pytest

from src.models import Completion, StudentProfile
from src.profiles import export_profile, import_profile
from test_app import app, open_inspector, submit


def test_current_picker_and_other_codes_update_only_after_submission(app):
    app.multiselect(key="current_courses").select("ECE101")
    app.text_area(key="current_course_text").set_value("MATH 129")
    assert app.session_state["profile"].current_enrollment == []
    assert "result" not in app.session_state
    submit(app)
    assert not app.exception
    assert app.session_state["profile"].current_enrollment == ["ECE101", "MATH129"]
    assert "uofa:ECE101:2026-2027" not in app.session_state["result"].context.allowed_record_ids
    assert any(item.label == "Currently taking (2)" for item in app.expander)
    assert any("2 currently taking" in item.value for item in app.caption)
    assert app.button(key="finish_MATH129")
    previous = app.session_state["result"]
    app.run()
    assert app.session_state["result"] is previous


def test_finishing_current_course_moves_pickers_and_waits_for_required_grade(app):
    app.multiselect(key="current_courses").select("ECE101")
    app.text_area(key="current_course_text").set_value("MATH129")
    submit(app)
    app.button(key="finish_ECE101").click().run()
    assert not app.exception
    profile = app.session_state["profile"]
    assert profile.current_enrollment == ["MATH129"]
    assert profile.completed == [Completion(course_code="ECE101")]
    assert app.multiselect(key="current_courses").value == []
    assert "ECE101" in app.multiselect(key="completed_courses").value
    # The real browser needs an explicit value update, not just changed defaults.
    assert app.multiselect(key="current_courses").proto.set_value
    assert app.multiselect(key="completed_courses").proto.set_value
    assert not app.multiselect(key="current_courses").proto.raw_values
    assert any(value.startswith("ECE101 · ") for value in app.multiselect(key="completed_courses").proto.raw_values)
    assert app.text_area(key="current_course_text").value == "MATH129"
    csc120 = "uofa:CSC120:2026-2027"
    assert app.session_state["result"].context.rule_results[csc120].status == "unknown"
    app.selectbox(key="grade_ECE101").set_value("B")
    submit(app)
    assert not app.exception
    assert app.session_state["result"].context.rule_results[csc120].status == "satisfied"
    assert app.session_state["profile"].current_enrollment == ["MATH129"]


@pytest.mark.parametrize("invalid", ["both_statuses", "duplicate", "grade_in_current"])
def test_invalid_current_form_keeps_previous_profile_and_result(app, invalid):
    app.multiselect(key="current_courses").select("ECE101")
    submit(app)
    profile, result = app.session_state["profile"], app.session_state["result"]
    if invalid == "both_statuses":
        app.multiselect(key="completed_courses").select("ECE101")
    else:
        app.text_area(key="current_course_text").set_value("ece 101" if invalid == "duplicate" else "MATH129:B")
    submit(app)
    assert not app.exception and app.error
    assert app.session_state["profile"] == profile
    assert app.session_state["result"] is result


def test_restored_current_courses_survive_goal_edits_and_can_be_removed(app):
    profile = StudentProfile(current_enrollment=["ECE101", "MATH129"], consents=["permission"])
    app.session_state["profile"] = import_profile(export_profile(profile).encode())
    app.session_state["reset_profile_widgets"] = True
    app.session_state["refresh_pending"] = True
    app.run()
    assert not app.exception
    assert app.multiselect(key="current_courses").value == ["ECE101"]
    assert app.text_area(key="current_course_text").value == "MATH129"
    app.selectbox(key="career_id").set_value("embedded")
    submit(app)
    assert app.session_state["profile"].current_enrollment == ["ECE101", "MATH129"]
    assert app.session_state["profile"].consents == ["permission"]
    app.multiselect(key="current_courses").unselect("ECE101")
    app.text_area(key="current_course_text").set_value("")
    submit(app)
    assert not app.exception
    assert app.session_state["profile"].current_enrollment == []
    assert "uofa:ECE101:2026-2027" in app.session_state["result"].context.allowed_record_ids
    assert any("Removed from currently taking" in item.value for item in app.caption)


def test_current_discovery_omissions_are_visible_without_promoting_completion(app, monkeypatch, tmp_path):
    from test_ece_core import core_refresh
    calls = []
    def refresh(catalog, profile, **kwargs):
        calls.append(profile)
        return core_refresh(catalog, tmp_path, profile)
    monkeypatch.setattr("src.controller.refresh_catalog", refresh)
    monkeypatch.setenv("ECE_REFRESH_SOURCES", "true")
    app.run()
    app.selectbox(key="career_id").set_value("embedded")
    app.text_area(key="current_course_text").set_value("ECE201, ECE220, ECE274A")
    submit(app)
    open_inspector(app)
    assert not app.exception and len(calls) == 1
    assert app.session_state["profile"].completed == []
    assert app.session_state["result"].trace["source_refresh"]["discovery_selection"]["skipped_enrolled_codes"] == [
        "ECE201", "ECE220", "ECE274A"]
    assert any("Discovery slots skip courses recorded as currently taking" in item.value for item in app.caption)
