"""Reviewer interactions use explicit controlled fixtures, never human-quality results."""

from datetime import datetime, timezone
import json

import pytest
from streamlit.testing.v1 import AppTest

from src.catalog import ROOT
from src.review import make_packet
from src.review_workspace import review_progress


def widget(app, kind, label):
    return next(item for item in getattr(app, kind) if item.label == label)


def grade(app, value):
    widget(app, "radio", "Relevance grade").set_value(value)
    return widget(app, "button", "Save grade and next").click().run()


@pytest.fixture
def review_app(catalog, tmp_path, monkeypatch):
    packet = make_packet(catalog, now=datetime(2026, 11, 5, tzinfo=timezone.utc),
                         questions=[{"case_id": "fixture", "query": "How do interrupts work?"}])
    (tmp_path / "packet.json").write_text(packet.model_dump_json())
    (tmp_path / "catalog_snapshot.json").write_text(catalog.model_dump_json())
    monkeypatch.setenv("ECE_REVIEW_PACKET_DIR", str(tmp_path))
    def forbidden(*a, **k): pytest.fail("Reviewing must not call a provider, retrieve ranks, or fetch sources")
    monkeypatch.setattr("httpx.Client.send", forbidden)
    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr("src.review.Retriever", forbidden)
    monkeypatch.setattr("src.providers.GeminiProvider", forbidden)
    return AppTest.from_file(ROOT / "reviewer_app.py", default_timeout=20).run()


def test_default_runtime_workspace_starts_with_all_408_ratings_blank(monkeypatch):
    monkeypatch.delenv("ECE_REVIEW_PACKET_DIR", raising=False)
    app = AppTest.from_file(ROOT / "reviewer_app.py", default_timeout=20).run()
    assert not app.exception and review_progress(app.session_state["review_form"]) == (0, 408)
    assert widget(app, "radio", "Relevance grade").value is None
    assert widget(app, "radio", "Reviewer role").value is None
    assert not app.dataframe


def test_empty_save_does_not_create_a_zero_grade_or_advance(review_app):
    app = review_app
    widget(app, "button", "Save grade and next").click().run()
    assert not app.exception and app.warning
    assert review_progress(app.session_state["review_form"]) == (0, 10)
    assert app.session_state["review_positions"]["fixture"] == 0


def test_explicit_grade_advances_and_previous_evidence_retains_the_saved_value(review_app):
    app = grade(review_app, 0)
    assert not app.exception and review_progress(app.session_state["review_form"]) == (1, 10)
    assert widget(app, "radio", "Relevance grade").value is None
    widget(app, "button", "Previous evidence").click().run()
    assert widget(app, "radio", "Relevance grade").value == 0
    grade(app, 3)
    assert review_progress(app.session_state["review_form"]) == (1, 10)


def test_clear_grade_updates_the_client_and_preserves_alias_and_role(review_app):
    app = grade(review_app, 2)
    widget(app, "text_input", "Reviewer alias").set_value("fixture-alias").run()
    widget(app, "radio", "Reviewer role").set_value("controlled_fixture").run()
    widget(app, "button", "Previous evidence").click().run()
    widget(app, "button", "Clear this grade").click().run()
    assert not app.exception and widget(app, "radio", "Relevance grade").value is None
    assert widget(app, "radio", "Relevance grade").proto.set_value
    assert review_progress(app.session_state["review_form"]) == (0, 10)
    assert widget(app, "text_input", "Reviewer alias").value == "fixture-alias"
    assert widget(app, "radio", "Reviewer role").value == "controlled_fixture"


def test_completed_export_requires_all_choices_and_is_invalidated_by_an_edit(review_app):
    app = review_app
    widget(app, "text_input", "Reviewer alias").set_value("fixture").run()
    widget(app, "radio", "Reviewer role").set_value("controlled_fixture").run()
    widget(app, "button", "Prepare completed review").click().run()
    assert "review_completed_json" not in app.session_state
    for _ in range(10): grade(app, 0)
    widget(app, "button", "Prepare completed review").click().run()
    assert not app.exception
    completed = json.loads(app.session_state["review_completed_json"])
    assert completed["reviewer_role"] == "controlled_fixture" and completed["reviewed_at"]
    grade(app, 2)
    assert "review_completed_json" not in app.session_state


def test_invalid_packet_directory_is_a_redacted_load_error(tmp_path, monkeypatch):
    private = tmp_path / "private-fixture-path"
    monkeypatch.setenv("ECE_REVIEW_PACKET_DIR", str(private))
    app = AppTest.from_file(ROOT / "reviewer_app.py", default_timeout=20).run()
    assert not app.exception and app.error
    assert not any(str(private) in item.value for item in app.error)
