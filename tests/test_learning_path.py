"""The instructor's lesson sequence works without live services or profile edits."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.catalog import load_runtime_catalog
from src.learning_lab import PRESETS, build_lab_index, run_experiment


def test_learning_path_to_advisor_and_saved_comparison(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("The lesson must run offline")

    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    monkeypatch.setattr("httpx.Client.send", forbidden)
    monkeypatch.setenv("ECE_REFRESH_SOURCES", "false")
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "ECE_DEVELOPMENT_MODE"):
        monkeypatch.delenv(key, raising=False)
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=20).run()
    assert not app.exception and app.session_state["view"] == "Beginner"
    assert not app.text_area
    assert any("Question to evidence flowchart" in item.proto.body for item in app.get("html"))

    app.radio(key="learn_foundations_answer").set_value("The official requirements and my completed coursework").run()
    assert app.session_state["lesson_beginner"]
    next(button for button in app.button if button.label == "Try a preset experiment").click().run()
    assert not app.exception and app.session_state["view"] == "Intermediate"
    assert len(app.get("plotly_chart")) == 1

    index = build_lab_index(load_runtime_catalog().model_dump_json())
    first = run_experiment(index, PRESETS["Program a sensor"], "keyword").hits[0].record_id
    app.selectbox(key="learn_rank_answer").set_value(first).run()
    assert app.session_state["lesson_intermediate"]
    app.session_state["lesson_preset_code"] = True
    app.run()
    assert any("def plot_experiment" in item.value for item in app.code)
    next(button for button in app.button if button.label == "Create your variation").click().run()
    assert not app.exception and app.session_state["view"] == "Advanced"

    app.text_input(key="learn_variation_query").set_value(PRESETS["Learn image classification"])
    target = next(record.record_id for record in index.catalog.records if record.code == "ECE425")
    app.multiselect(key="learn_expected_records").set_value([target])
    next(button for button in app.button if button.label == "Compare with preset").click().run()
    assert not app.exception
    assert [item.value for item in app.metric] == ["0 / 1", "1 / 1"]
    app.text_area(key="learn_observation").set_value("The neural terms moved ECE425 into the top three.").run()
    next(button for button in app.button if button.label == "Save my observation").click().run()
    assert app.session_state["lesson_advanced"]
    assert any(item.proto.label == "Download my comparison" for item in app.get("download_button"))
    assert "profile" not in app.session_state

    next(button for button in app.button if button.label == "Open the advisor").click().run()
    assert not app.exception and app.session_state["view"] == "Advisor"
    assert any(button.label == "Update my roadmap" for button in app.button)
    next(button for button in app.button if button.label == "Update my roadmap").click().run()
    assert not app.exception and app.session_state["result"].context.allowed_record_ids
    app.session_state["plan_inspector"] = True
    app.run()
    assert not app.code
    app.session_state["plan_visualization_code"] = True
    app.run()
    assert not app.exception
    assert any("def ranking_html" in item.value and "def project_embeddings" in item.value for item in app.code)
