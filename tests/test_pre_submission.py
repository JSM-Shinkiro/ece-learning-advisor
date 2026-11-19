"""Regressions from the pre-submission student workflow review."""

import json
from pathlib import Path
from threading import Event

import pytest
from streamlit.testing.v1 import AppTest

from scripts.check_sources import summarize_checks
from src.catalog import load_runtime_catalog
from src.controller import run_advisor
from src.models import StudentProfile
from src.profiles import import_profile
from src.sources import CatalogRefresh
from test_app import app, open_advisor_tab, settle_advisor, submit


SOLAR_QUESTION = "I want to design a solar energy system"


def test_exploring_form_publishes_both_plans_and_can_accept_the_inferred_direction(app, monkeypatch):
    entered, release = Event(), Event()

    def refresh(catalog, profile, **options):
        assert profile.career_id == "power"
        entered.set()
        assert release.wait(6)
        return CatalogRefresh(catalog)

    monkeypatch.setenv("ECE_REFRESH_SOURCES", "true")
    monkeypatch.setattr("src.controller.refresh_catalog", refresh)
    app.selectbox(key="career_id").set_value("exploring")
    app.multiselect(key="completed_courses").set_value(["ECE101"])
    app.text_input(key="question").set_value(SOLAR_QUESTION)
    next(button for button in app.button if button.label == "Update my roadmap").click().run()
    job = app.session_state["advisor_job"]
    try:
        assert entered.wait(5)
        app.run()
        first = app.session_state["result"]
        assert not app.exception and not app.error
        assert first.trace["source_refresh"]["reason"] == "pending"
        assert first.trace["study_route"] == "Solar PV & Energy Storage"
        assert app.session_state["profile"].career_id == "exploring"
        release.set()
        settle_advisor(app)
        assert app.session_state["result"] is not first
        assert app.session_state["result"].trace["source_refresh"]["enabled"]
        app.button(key="save_matched_direction").click().run()
        settle_advisor(app)
        profile = app.session_state["profile"]
        assert profile.career_id == "power" and profile.question == SOLAR_QUESTION
        assert [course.course_code for course in profile.completed] == ["ECE101"]
    finally:
        release.set()
        assert job.wait(5)


def test_conflicting_direction_waits_for_student_choice_and_keeps_the_question(app):
    app.text_input(key="question").set_value(SOLAR_QUESTION)
    submit(app)
    assert app.session_state["profile"].career_id == "ai_ml"
    assert not app.session_state["result"].context.allowed_record_ids
    assert app.session_state["result"].direction_choices == ("power",)
    app.button(key="use_direction_power").click().run()
    assert app.session_state["profile"].career_id == "power"
    assert app.session_state["profile"].question == SOLAR_QUESTION
    assert app.session_state["result"].trace["study_route"] == "Solar PV & Energy Storage"


def test_open_ended_interest_recognizes_ai_and_offers_choices_for_mixed_interests():
    catalog = load_runtime_catalog()
    profile = StudentProfile(career_id="exploring", question="I want to study computer vision")
    plan = run_advisor(catalog, profile, refresh_sources=False)
    assert plan.context.profile.career_id == "ai_ml"
    assert plan.trace["study_route"] == "Computer Vision & Perception"
    mixed = profile.model_copy(update={"question": "I am interested in optical imaging and industrial automation"})
    choice = run_advisor(catalog, mixed, refresh_sources=False)
    assert set(choice.direction_choices) == {"photonics", "controls"}
    assert choice.context.profile == mixed and not choice.context.allowed_record_ids


def test_mixed_interest_switch_preserves_the_submitted_profile(app):
    question = "How to combine AI and Robotics?"
    interests = "robotics with edge AI controls and OS"
    app.selectbox(key="career_id").set_value("controls")
    app.text_input(key="question").set_value(question)
    app.text_area(key="interests").set_value(interests)
    app.multiselect(key="completed_courses").set_value(["ECE220"])
    app.multiselect(key="current_courses").set_value(["ECE320A"])
    submit(app)

    current = app.session_state["profile"]
    plan = app.session_state["result"]
    assert not app.exception and not app.error and plan.trace["study_route"] == "Robotics & Autonomy"
    assert any("AI can help a robot interpret camera images." in item.value for item in app.markdown)
    assert any("catalog.arizona.edu/courses/0435981" in item.value and
               "catalog.arizona.edu/courses/0363511" in item.value for item in app.caption)
    assert "uofa:ECE441A:2026-2027" in plan.context.allowed_record_ids
    app.button(key="use_direction_ai_ml").click().run()
    settle_advisor(app)
    assert not app.exception and not app.error
    assert app.session_state["profile"] == current.model_copy(update={"career_id": "ai_ml"})
    assert app.text_input(key="question").value == question
    assert app.button(key="use_direction_controls").label == "Use Controls & Robotics"
    assert "uofa:ECE425:2026-2027" in app.session_state["result"].context.allowed_record_ids


@pytest.mark.parametrize(("question", "kind", "url"), [
    ("Is ECE 425 offered next spring on Tuesday?", "schedule", "https://studentcenter.arizona.edu/app/ui/public/select-campus"),
    ("Can I take ECE425 on Tuesday?", "schedule", "https://studentcenter.arizona.edu/app/ui/public/select-campus"),
    ("How much tuition does ECE425 cost?", "tuition", "https://bursar.arizona.edu/tuition"),
    ("When is the midterm for ECE 425?", "syllabus", "https://d2l.arizona.edu/"),
])
def test_administrative_question_links_to_official_information_and_keeps_the_course(app, monkeypatch, question, kind, url):
    def forbidden(*args, **kwargs):
        pytest.fail("Section and tuition questions should make no source or model requests")

    monkeypatch.setenv("GEMINI_API_KEY", "controlled")
    monkeypatch.setenv("ECE_REFRESH_SOURCES", "true")
    monkeypatch.setattr("src.controller.refresh_catalog", forbidden)
    monkeypatch.setattr("src.controller.GeminiProvider", forbidden)
    app.run()
    app.checkbox(key="use_ai").set_value(True)
    app.text_input(key="question").set_value(question)
    submit(app)
    assert not app.exception and not app.error
    result = app.session_state["result"]
    assert result.course_question.kind == kind and result.course_question.codes == ("ECE425",)
    assert not result.hits and result.trace["model_calls"] == 0 and not result.context.allowed_record_ids
    assert any(link.proto.url == url for link in app.get("link_button"))
    assert any(item.value.startswith("**ECE425 · ") for item in app.markdown)


def test_past_course_day_does_not_replace_learning_request_with_class_search():
    profile = StudentProfile(question="I finished ECE425 on Tuesday. How do I learn computer vision?")
    plan = run_advisor(load_runtime_catalog(), profile, refresh_sources=False)
    assert not plan.course_question and plan.trace["study_route"] == "Computer Vision & Perception"


@pytest.mark.parametrize(("entered", "status"), [("2026–27", "satisfied"), ("2026-2027", "satisfied"),
                                                   ("2025–26", "unknown"), ("Not sure", "unknown")])
def test_imported_catalog_year_controls_the_reviewed_prerequisite(entered, status):
    profile = import_profile(json.dumps({
        "catalog_version": entered, "question": "What do I need to take CSC120?",
        "completed": [{"course_code": "ECE101", "grade": "B"}],
    }).encode())
    result = run_advisor(load_runtime_catalog(), profile, refresh_sources=False)
    assert result.context.rule_results["uofa:CSC120:2026-2027"].status == status


def test_build_roadmap_opens_main_profile_and_lazy_tabs_keep_browsing_state(monkeypatch):
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    monkeypatch.setenv("ECE_REFRESH_SOURCES", "false")
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py").run()
    next(b for b in app.button if b.label == "Build my roadmap").click().run()
    assert not app.exception and app.selectbox(key="catalog_version").value == "Not sure"
    assert not any(panel.key and panel.key.startswith("collection_record_") for panel in app.expander)
    assert not any(button.label == "Available Opportunities" for button in app.button)
    app.text_input(key="question").set_value("A draft about ECE425")
    open_advisor_tab(app, "Courses & Resources")
    app.text_input(key="collection_query").set_value("ECE425").run()
    panel_key = "collection_record_uofa:ECE425:2026-2027"
    app.session_state[panel_key] = True
    app.run()
    open_advisor_tab(app, "Opportunities")
    assert not any(panel.key == panel_key for panel in app.expander)
    open_advisor_tab(app, "Courses & Resources")
    assert app.text_input(key="collection_query").value == "ECE425"
    assert app.session_state[panel_key] and app.text_input(key="question").value == "A draft about ECE425"
    assert "result" not in app.session_state


def test_source_monitor_separates_budget_skips_from_failed_checks():
    checks = [{"status": "skipped"}, {"status": "updated", "rule_status": "verified"}]
    summary = summarize_checks(checks)
    assert summary == {"attempted": 1, "skipped": 1, "failed_sources": 0, "rules": {"verified": 1},
                       "discovery": {}, "passed": True}
    checks.append({"status": "updated", "discovery_status": "unavailable"})
    summary = summarize_checks(checks)
    assert not summary["passed"] and summary["failed_sources"] == 0 and summary["discovery"] == {"unavailable": 1}
