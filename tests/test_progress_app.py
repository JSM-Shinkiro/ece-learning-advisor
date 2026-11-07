"""Student-visible stage feedback reflects preview, clarification, and failures."""

from conftest import FakeProvider
from test_app import app, submit


def test_preview_has_completed_status_and_stage_history(app):
    submit(app)
    status = app.status[0]
    assert status.label == "Learning plan ready" and status.proto.icon == ":material/check:"
    assert [m.value for m in status.markdown] == ["Checking your learning goal", "Using saved source snapshots",
                                                "Finding learning options", "Checking recorded preparation"]
    assert app.session_state["result"].trace["request_phases"]["phases"]


def test_unsupported_request_finishes_with_clarification_status(app):
    app.text_input(key="question").set_value("marine biology and ocean fieldwork")
    submit(app)
    assert app.status[0].label == "More detail needed"
    assert not any(m.value == "Preparing AI explanations" for m in app.status[0].markdown)


def test_model_abstention_finishes_with_clarification_status(app, monkeypatch, tmp_path):
    from src.models import ExplanationSelection
    provider = FakeProvider()
    provider.close = lambda: None
    provider.generate = lambda _: ExplanationSelection(status="insufficient_evidence", clarification_code="more_details")
    monkeypatch.setenv("GEMINI_API_KEY", "controlled-placeholder")
    monkeypatch.setenv("ECE_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr("src.controller.GeminiProvider", lambda *a, **k: provider)
    app.run()
    app.checkbox(key="use_ai").set_value(True).run()
    submit(app)
    assert not app.exception and app.status[0].label == "More detail needed"


def test_failed_request_uses_error_status_and_hides_raw_diagnostics(app, monkeypatch):
    def broken(*a, **k): raise OSError("private-fixture-diagnostic")
    monkeypatch.setattr("src.controller.run_advisor", broken)
    submit(app)
    assert not app.exception and app.error
    assert app.status[0].label == "The plan could not be updated"
    assert app.status[0].proto.icon == ":material/error:"
    assert not any("private-fixture-diagnostic" in m.value for m in app.markdown)
