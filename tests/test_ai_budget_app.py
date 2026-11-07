"""Time-limited explanations preserve the submitted student's source roadmap."""

import pytest

from conftest import FakeProvider
from test_app import app, submit


class ControlledTimeout(FakeProvider):
    def __init__(self, stage=None):
        super().__init__()
        self.stage, self.closed = stage, 0

    def set_request_budget(self, budget): self.budget = budget

    def expire(self, stage):
        if self.stage == stage:
            self.budget.clock = lambda: self.budget.started + self.budget.seconds + 1
            self.budget.remaining()

    def embed_document(self, chunk):
        self.expire("embedding")
        return super().embed_document(chunk)

    def generate(self, context):
        self.expire("generation")
        return super().generate(context)

    def close(self): self.closed += 1


@pytest.mark.parametrize("stage", ["embedding", "generation"])
def test_time_limit_shows_current_source_cards_and_explicit_budget_notice(app, monkeypatch, tmp_path, stage):
    provider = ControlledTimeout(stage)
    monkeypatch.setenv("GEMINI_API_KEY", "controlled-placeholder")
    monkeypatch.setenv("AI_TIME_BUDGET_SECONDS", "5")
    monkeypatch.setenv("ECE_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr("src.controller.GeminiProvider", lambda *a, **k: provider)
    app.run()
    app.checkbox(key="use_ai").set_value(True).run()
    app.multiselect(key="current_courses").select("ECE101")
    app.selectbox(key="career_id").set_value("embedded")
    submit(app)
    assert not app.exception
    assert app.session_state["profile"].current_enrollment == ["ECE101"]
    result = app.session_state["result"]
    assert result.context.profile.career_id == "embedded" and result.generation_status == "time_budget_exceeded"
    assert "uofa:ECE101:2026-2027" not in result.context.allowed_record_ids
    assert any("AI time limit reached" in warning.value for warning in app.warning)
    assert any("AI time budget: 5 s" in caption.value for caption in app.caption)
    assert not any("AI explanation available" in caption.value for caption in app.caption)
    assert provider.closed == 1 and any(button.key.startswith("complete_") for button in app.button)


def test_a_new_submission_gets_a_fresh_budget_and_can_recover(app, monkeypatch, tmp_path):
    providers = []
    def factory(*args, **kwargs):
        provider = ControlledTimeout("generation" if not providers else None)
        providers.append(provider)
        return provider
    monkeypatch.setenv("GEMINI_API_KEY", "controlled-placeholder")
    monkeypatch.setenv("AI_TIME_BUDGET_SECONDS", "5")
    monkeypatch.setenv("ECE_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr("src.controller.GeminiProvider", factory)
    app.run()
    app.checkbox(key="use_ai").set_value(True).run()
    submit(app)
    assert app.session_state["result"].generation_status == "time_budget_exceeded"
    app.text_area(key="interests").set_value("robotics and hardware")
    submit(app)
    assert not app.exception and app.session_state["result"].generation_complete
    assert app.session_state["result"].context.profile.interests == "robotics and hardware"
    assert providers[0].budget is not providers[1].budget and all(p.closed == 1 for p in providers)
    assert not any("AI time limit reached" in warning.value for warning in app.warning)


def test_invalid_host_budget_is_recoverable_without_exposing_input(app, monkeypatch):
    monkeypatch.setenv("AI_TIME_BUDGET_SECONDS", "controlled-private-invalid")
    app.run()
    assert not app.exception and any("AI_TIME_BUDGET_SECONDS" in error.value for error in app.error)
    assert not any("controlled-private-invalid" in error.value for error in app.error)
    monkeypatch.setenv("AI_TIME_BUDGET_SECONDS", "45")
    app.run()
    submit(app)
    assert not app.exception and app.session_state["result"].context.allowed_record_ids
