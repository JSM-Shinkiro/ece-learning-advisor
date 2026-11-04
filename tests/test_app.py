import pytest
from pathlib import Path
from streamlit.testing.v1 import AppTest


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr("dotenv.load_dotenv",lambda *a,**k:False)
    monkeypatch.setenv("ECE_REFRESH_SOURCES", "false")
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
        item = answer.recommendations[0]
        extra = next(s for s in context.allowed_statements if s.record_id == item.record_id and s.statement_id not in item.statement_ids)
        item.statement_ids.append(extra.statement_id)
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
    assert app.session_state["result"].statement_validation_passed
    assert any(expander.label == "Available explanation statements" for expander in app.expander)
    table = next(item.value for item in app.dataframe if "statement" in item.value.columns)
    assert table["selected"].sum() == 2
    assert set(table[table["selected"]]["statement"]) == set(app.session_state["result"].selected_statement_ids)


def test_rejected_explanation_keeps_sources_and_never_displays_its_prose(app, monkeypatch, fake_provider):
    from src.models import GeneratedAnswer, Reason, Recommendation
    def legacy(context):
        rid = context.allowed_record_ids[0]
        return GeneratedAnswer(status="answered", recommendations=[Recommendation(record_id=rid,
            reasons=[Reason(text="Guaranteed internship from this course.", claim_type="recommendation",
                evidence_ids=[rid + ":overview"])])])
    fake_provider.generate = legacy
    fake_provider.close = lambda: None
    monkeypatch.setattr("src.controller.GeminiProvider", lambda *a, **k: fake_provider)
    monkeypatch.setenv("GEMINI_API_KEY", "fixture-key")
    app.run()
    app.checkbox(key="use_ai").set_value(True).run()
    submit(app)
    assert not app.exception and app.warning
    result = app.session_state["result"]
    assert result.answer is None and result.trace["validation_error"] == "unsupported_output"
    assert any(button.key == "complete_ECE101" for button in app.button)
    assert not any("Guaranteed internship" in item.value for item in app.markdown)
    assert not any("AI explanation available" in item.value for item in app.caption)


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
    from src.models import ExplanationSelection
    fake_provider.generate=lambda _:ExplanationSelection(status="insufficient_evidence",clarification_code="more_details")
    fake_provider.close=lambda:None
    monkeypatch.setattr("src.controller.GeminiProvider",lambda *a,**k:fake_provider)
    monkeypatch.setenv("GEMINI_API_KEY","dummy")
    app.run()
    app.checkbox(key="use_ai").set_value(True).run()
    submit(app)
    assert not app.exception
    assert any("Please add a learning goal" in message.value for message in app.info)
    assert not any("AI explanation available" in message.value for message in app.caption)
    assert not any(button.key and button.key.startswith("complete_") for button in app.button)


def test_live_sources_run_on_submission_and_render_the_active_catalog(app, monkeypatch):
    from datetime import datetime, timezone
    from src.sources import CatalogRefresh

    calls = []
    def refresh(catalog, profile, **kwargs):
        calls.append(profile.career_id)
        active = catalog.model_copy(deep=True)
        next(r for r in active.records if r.code == "ECE101").title = "Live HTTP fixture programming"
        source = next(s for s in active.sources if s.source_id == "catalog:ECE101")
        source.last_checked_at = datetime(2026, 11, 4, 3, tzinfo=timezone.utc)
        source.verification_status = "verified"
        return CatalogRefresh(active)

    monkeypatch.setattr("src.controller.refresh_catalog", refresh)
    monkeypatch.setenv("ECE_REFRESH_SOURCES", "true")
    app.run()
    assert calls == []
    submit(app)
    assert not app.exception and calls == ["ai_ml"]
    assert any("Live HTTP fixture programming" in item.value for item in app.markdown)
    assert any("Checked 2026-11-03 20:00 MST" in item.value for item in app.caption)
    app.run()
    assert calls == ["ai_ml"]
    app.selectbox(key="career_id").set_value("embedded")
    submit(app)
    assert not app.exception and calls == ["ai_ml", "embedded"]


def test_changed_prerequisite_replaces_approval_in_cards_and_inspector(app, monkeypatch):
    from src.sources import CatalogRefresh

    changed = False
    def refresh(catalog, profile, **kwargs):
        active = catalog.model_copy(deep=True)
        course = next(r for r in active.records if r.code == "CSC120")
        proof = course.rule_evidence[0]
        course.rule_verification = proof.verification_status = "changed" if changed else "verified"
        if changed:
            proof.observed_text = "Changed fixture statement awaiting review."
        for source in active.sources:
            if source.source_id in course.source_ids:
                source.verification_status = "verified"
        return CatalogRefresh(active)

    monkeypatch.setattr("src.controller.refresh_catalog", refresh)
    monkeypatch.setenv("ECE_REFRESH_SOURCES", "true")
    app.text_area(key="course_text").set_value("ECE101:B")
    submit(app)
    assert not app.exception
    assert any("Recorded prerequisites satisfied" in caption.value for caption in app.caption)
    changed = True
    submit(app)
    assert not app.exception
    assert not any("Recorded prerequisites satisfied" in caption.value for caption in app.caption)
    assert any("Enrollment requirements unverified" in caption.value for caption in app.caption)
    assert any("prerequisite evidence or interpretation needs review" in item.value for item in app.markdown)
    assert any("Changed fixture statement awaiting review." in item.value for item in app.text)
    assert any("uofa:CSC120:2026-2027:rule:R1299-L40" in item.value for item in app.markdown)


def test_discovered_sources_reach_collection_picker_and_trace(app, monkeypatch, catalog, tmp_path):
    from src.discovery import load_discovery_plans
    from src.models import Record
    from src.sources import refresh_catalog
    from test_discovery import client_for

    plans = load_discovery_plans()
    new_courses = {identity: Record(record_id="fixture:" + code, kind="course", code=code,
        title="Discovered fixture " + code, summary="Fixture programming and hardware.", credits=3,
        source_ids=["fixture"], catalog_version="2026-2027")
        for identity, code in zip(['7654321', '7654322', '7654323', '7654324'],
                                  ['ECE175', 'ECE275', 'ECE274A', 'CSC110'])}
    seen = []
    def refresh(catalog, profile, **kwargs):
        assert len(kwargs.pop('discovery_plans')) == 2
        with client_for(catalog, plans, new_courses, seen=seen) as client:
            return refresh_catalog(catalog, profile, client=client, discovery_plans=plans,
                                   cache_dir=tmp_path / 'sources')
    monkeypatch.setattr('src.controller.refresh_catalog', refresh)
    monkeypatch.setenv('ECE_REFRESH_SOURCES', 'true')
    submit(app)
    assert not app.exception
    assert any('8 courses' in caption.value for caption in app.caption)
    assert any('Discovered fixture CSC110' in item.label for item in app.expander)
    assert len(app.session_state['result'].trace['source_refresh']['discovered_courses']) == 3
    calls = len(seen)
    app.run()
    assert len(seen) == calls
    assert any(option.startswith('CSC110 · ') for option in app.multiselect(key='completed_courses').options)


def test_resource_sources_render_versions_and_update_only_on_submission(app, monkeypatch, tmp_path):
    import httpx
    from src.sources import refresh_catalog
    from src.resource_sources import RESOURCE_URLS
    from test_resource_sources import INTRO, resource_page

    changed = False
    seen = []
    def respond(request):
        url = str(request.url)
        seen.append(url)
        rid = next((rid for rid, known in RESOURCE_URLS.items() if known == url), None)
        if rid is None:
            return httpx.Response(503)
        intro = 'Changed fixture resource introduction describes updated programming examples and study material.' if changed else INTRO
        return httpx.Response(200, text=resource_page(rid, intro=intro), headers={'Content-Type': 'text/html'})
    def refresh(catalog, profile, **kwargs):
        assert kwargs['resource_checks'] is True
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            return refresh_catalog(catalog, profile, client=client, resource_checks=True,
                                   cache_dir=tmp_path / 'sources')
    monkeypatch.setattr('src.controller.refresh_catalog', refresh)
    monkeypatch.setenv('ECE_REFRESH_SOURCES', 'true')
    submit(app)
    assert not app.exception
    assert any(INTRO in item.value for item in app.markdown)
    assert any('Version: 2.99.0+fixture' in item.value for item in app.caption)
    assert app.session_state['result'].trace['resource_versions']['resource:cs50'] == '2026'
    count = len(seen)
    app.run()
    assert len(seen) == count
    changed = True
    submit(app)
    assert not app.exception
    assert any('Changed fixture resource introduction' in item.value for item in app.markdown)
