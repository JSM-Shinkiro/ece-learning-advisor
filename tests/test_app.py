import pytest
from pathlib import Path
from streamlit.testing.v1 import AppTest


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr("dotenv.load_dotenv",lambda *a,**k:False)
    for name in ["GEMINI_API_KEY","GOOGLE_API_KEY","ADZUNA_APP_ID","ADZUNA_APP_KEY","ECE_DEVELOPMENT_MODE"]:
        monkeypatch.delenv(name,raising=False)
    return AppTest.from_file(Path(__file__).resolve().parents[1]/"app.py",default_timeout=20).run()


def submit(app):
    next(b for b in app.button if b.label=="Update my roadmap").click()
    return app.run()


def test_profile_to_roadmap_and_goal_change(app):
    assert not app.exception
    submit(app)
    assert not app.exception
    assert any("ECE425" in h.value for h in app.markdown)
    assert any(h.value=="Later goals" for h in app.subheader)
    assert app.session_state["result"].context.allowed_record_ids[0]=="uofa:ECE101:2026-2027"
    app.selectbox(key="career_id").set_value("embedded")
    app.selectbox(key="programming_background").set_value("experienced")
    submit(app)
    assert not app.exception
    assert app.session_state["profile"].career_id=="embedded"
    assert app.session_state["profile"].programming_background=="experienced"
    assert app.session_state["result"].context.allowed_record_ids[0]=="uofa:ECE372A:2026-2027"
    assert not app.session_state["result"].generation_complete


def test_completed_course_updates_ui(app):
    app.selectbox(key="career_id").set_value("embedded")
    app.text_area(key="course_text").set_value("ECE372A:B")
    submit(app)
    assert not app.exception
    assert "uofa:ECE372A:2026-2027" not in app.session_state["result"].context.allowed_record_ids


def test_invalid_profile_is_visible_error(app):
    app.text_area(key="course_text").set_value("ECE101, ECE 101")
    submit(app)
    assert not app.exception
    assert app.error


def test_unconfigured_jobs_have_clear_state(app):
    assert next(b for b in app.button if b.label=="Available Opportunities").disabled
    assert not app.exception
    assert any("not configured" in x.value for x in app.info)


def test_live_ui_with_controlled_provider(app,monkeypatch,fake_provider):
    import src.controller
    original=fake_provider.generate
    def with_multiple_reasons(context):
        answer=original(context)
        answer.recommendations[0].reasons.append(answer.recommendations[0].reasons[0].model_copy())
        return answer
    fake_provider.generate=with_multiple_reasons
    fake_provider.close=lambda:None
    monkeypatch.setattr(src.controller,"GeminiProvider",lambda *a,**k:fake_provider)
    monkeypatch.setenv("GEMINI_API_KEY","fixture-key")
    app.run()
    app.checkbox(key="use_ai").set_value(True)
    app.run()
    submit(app)
    assert not app.exception
    assert app.session_state["result"].generation_complete
    assert fake_provider.context is app.session_state["result"].context


def test_server_key_never_populates_widget(app,monkeypatch):
    secret="dummy-server-secret"
    monkeypatch.setenv("GEMINI_API_KEY",secret)
    monkeypatch.setenv("ECE_DEVELOPMENT_MODE","true")
    app.run()
    assert not app.exception
    assert all(w.value!=secret for w in app.text_input)
    assert not any(w.key=="gemini_key" for w in app.text_input)


def test_initialization_failure_updates_profile_and_roadmap_together(app,monkeypatch):
    from src.providers import ProviderError
    submit(app)
    assert app.session_state["result"].context.profile.career_id=="ai_ml"
    monkeypatch.setenv("GEMINI_API_KEY","dummy")
    app.run()
    app.checkbox(key="use_ai").set_value(True).run()
    def fail(*args,**kwargs):
        raise ProviderError("Test failure")
    monkeypatch.setattr("src.controller.GeminiProvider",fail)
    app.selectbox(key="career_id").set_value("embedded")
    submit(app)
    assert not app.exception
    assert app.session_state["profile"].career_id=="embedded"
    assert app.session_state["result"].context.profile.career_id=="embedded"
    assert app.warning


def test_imported_fields_survive_form_edit(app):
    from src.models import StudentProfile
    app.session_state["profile"]=StudentProfile(current_enrollment=["MATH129"],consents=["permission"])
    app.session_state["reset_profile_widgets"]=True
    app.run()
    app.text_area(key="interests").set_value("robotics")
    submit(app)
    assert not app.exception
    assert app.session_state["profile"].current_enrollment==["MATH129"]
    assert app.session_state["profile"].consents==["permission"]


def test_mark_completed_refreshes_plan_and_visible_picker(app):
    submit(app)
    app.button(key="complete_ECE101").click().run()
    assert not app.exception
    assert "ECE101" in app.multiselect(key="completed_courses").value
    assert "uofa:ECE101:2026-2027" not in app.session_state["result"].context.allowed_record_ids
    assert any("Added to completed" in caption.value for caption in app.caption)


def test_exploring_offers_both_goals_and_selectable_direction(app):
    app.selectbox(key="career_id").set_value("exploring")
    app.text_area(key="interests").set_value("AI and Hardware Integration")
    submit(app)
    assert not app.exception
    allowed=app.session_state["result"].context.allowed_record_ids
    assert {"uofa:ECE425:2026-2027","uofa:ECE372A:2026-2027"} <= set(allowed)
    app.button(key="choose_embedded").click().run()
    assert not app.exception
    assert app.session_state["profile"].career_id=="embedded"
    assert app.selectbox(key="career_id").value=="embedded"


def test_unsupported_question_shows_clarification_instead_of_courses(app):
    app.text_input(key="question").set_value("I want a marine biology degree and ocean fieldwork")
    submit(app)
    assert not app.exception
    assert app.session_state["result"].coverage_notice
    assert not any(button.key and button.key.startswith("complete_") for button in app.button)


def test_ai_abstention_does_not_show_success_or_recommendations(app,monkeypatch,fake_provider):
    from src.models import GeneratedAnswer
    fake_provider.generate=lambda _:GeneratedAnswer(status="insufficient_evidence",clarification="Please clarify the topic.")
    fake_provider.close=lambda:None
    monkeypatch.setattr("src.controller.GeminiProvider",lambda *a,**k:fake_provider)
    monkeypatch.setenv("GEMINI_API_KEY","dummy")
    app.run()
    app.checkbox(key="use_ai").set_value(True).run()
    submit(app)
    assert not app.exception
    assert any("Please clarify" in message.value for message in app.info)
    assert not any("AI explanation available" in message.value for message in app.caption)
    assert not any(button.key and button.key.startswith("complete_") for button in app.button)
