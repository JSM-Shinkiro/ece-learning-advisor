"""Interactive plans remain usable while controlled AI is deliberately blocked."""

from threading import Event

import pytest

from conftest import FakeProvider
from test_app import app, settle_advisor, submit


@pytest.fixture
def providers(monkeypatch,tmp_path):
    created=[]
    class Provider(FakeProvider):
        def __init__(self):
            super().__init__()
            self.entered,self.release,self.closed_event=Event(),Event(),Event()
            self.closed=0
        def generate(self,context):
            if not created.index(self):
                self.entered.set()
                assert self.release.wait(10)
            return super().generate(context)
        def close(self):
            self.closed+=1
            self.closed_event.set()
    def factory(*a,**k):
        provider=Provider();created.append(provider);return provider
    monkeypatch.setattr("src.controller.GeminiProvider",factory)
    monkeypatch.setenv("GEMINI_API_KEY","controlled-private-placeholder")
    monkeypatch.setenv("ECE_CACHE_DIR",str(tmp_path))
    yield created
    for provider in created:provider.release.set()
    for provider in created:assert provider.closed_event.wait(5)


def begin(app,providers,current=None):
    app.run();app.checkbox(key="use_ai").set_value(True).run()
    app.selectbox(key="ranking_method").set_value("keyword").run()
    if current:
        app.multiselect(key="current_courses").select(current)
    next(b for b in app.button if b.label=="Update my roadmap").click().run()
    job=app.session_state["advisor_job"]
    assert providers[0].entered.wait(5)
    app.run()
    assert not app.exception
    return job


def test_usable_source_plan_and_explicit_stop_reject_late_ai(app,providers):
    job=begin(app,providers)
    preview=app.session_state["result"]
    assert not preview.generation_complete and any(b.key.startswith("complete_") for b in app.button)
    assert any("Source plan ready" in c.value for c in app.caption)
    next(b for b in app.button if b.label=="Keep source plan").click().run()
    assert "advisor_job" not in app.session_state and app.session_state["result"] is preview
    providers[0].release.set();assert job.wait(5);app.run()
    assert not app.exception and app.session_state["result"] is preview and not preview.generation_complete
    assert providers[0].closed==1 and any("AI assistance stopped" in i.value for i in app.info)


def test_new_profile_can_finish_before_old_provider_and_remains_authoritative(app,providers):
    old=begin(app,providers)
    app.selectbox(key="career_id").set_value("embedded")
    app.text_area(key="interests").set_value("New embedded robotics profile")
    submit(app)
    latest=app.session_state["result"]
    assert latest.generation_complete and latest.context.profile.career_id=="embedded"
    assert len(providers)==2 and old.is_cancelled()
    providers[0].release.set();assert old.wait(5);app.run()
    assert not app.exception and app.session_state["result"] is latest
    assert latest.context.profile.interests=="New embedded robotics profile" and all(p.closed==1 for p in providers)


def test_other_controls_do_not_restart_the_pending_request(app,providers):
    begin(app,providers)
    job=app.session_state["advisor_job"]
    app.selectbox(key="ranking_method").set_value("hybrid").run()
    assert app.session_state["advisor_job"] is job and len(providers)==1
    providers[0].release.set();settle_advisor(app)
    assert not app.exception and app.selectbox(key="ranking_method").value=="hybrid"
    assert app.session_state["result"].generation_complete and len(providers)==1


def test_completion_during_ai_rebuilds_profile_and_discards_old_answer(app,providers):
    old=begin(app,providers,current="ECE101")
    app.button(key="finish_ECE101").click().run();settle_advisor(app)
    profile=app.session_state["profile"];latest=app.session_state["result"]
    assert not profile.current_enrollment and profile.completed[0].course_code=="ECE101"
    assert profile.completed[0].grade is None and "uofa:ECE101:2026-2027" not in latest.context.allowed_record_ids
    providers[0].release.set();assert old.wait(5);app.run()
    assert app.session_state["result"] is latest and latest.generation_complete


def test_unexpected_ai_failure_keeps_the_early_source_plan(app,providers,monkeypatch):
    old=begin(app,providers);preview=app.session_state["result"]
    def fail(*args):
        assert providers[0].release.wait(5)
        raise RuntimeError("controlled-private-error")
    # The first call is already waiting in the original method. Make its
    # application-owned materialization fail after that wait instead.
    monkeypatch.setattr("src.service.materialize_answer",fail)
    providers[0].release.set();settle_advisor(app)
    assert old.wait(5) and app.session_state["result"] is preview
    assert any("AI assistance could not finish" in item.value for item in app.info)
    assert not app.error and not app.exception and providers[0].closed==1
    assert not any("private-error" in str(item.value) for item in app.markdown)


def test_busy_ai_capacity_returns_a_source_plan_without_retrying_ai(app,providers,monkeypatch):
    from src.advisor_jobs import AdvisorBusy
    def busy(*a,**k):raise AdvisorBusy()
    monkeypatch.setattr("src.advisor_jobs.start_advisor_job",busy)
    app.run();app.checkbox(key="use_ai").set_value(True).run();submit(app)
    assert not app.exception and not providers and "advisor_job" not in app.session_state
    assert app.session_state["result"].context.allowed_record_ids
    assert any("AI assistance is busy" in warning.value for warning in app.warning)
