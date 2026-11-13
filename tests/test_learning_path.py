"""Learning progress, draft handoff and evidence checks through the app controls."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.catalog import load_runtime_catalog
from src.learning_lab import PRESETS, build_lab_index, run_experiment
from test_app import settle_advisor


@pytest.fixture
def lesson_app(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("The lesson must run offline")

    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    monkeypatch.setattr("httpx.Client.send", forbidden)
    monkeypatch.setenv("ECE_REFRESH_SOURCES", "false")
    monkeypatch.setenv("ECE_CACHE_DIR", str(tmp_path))
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "ECE_DEVELOPMENT_MODE"):
        monkeypatch.delenv(key, raising=False)
    return AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=20).run()


def click(app, label):
    next(button for button in app.button if button.label == label).click().run()
    assert not app.exception


def navigate(app, stage):
    app.segmented_control(key="view").set_value(stage).run()
    assert not app.exception and app.session_state["view"] == stage


def test_learning_path_to_advisor_and_saved_comparison(lesson_app):
    app = lesson_app
    assert not app.exception and app.session_state["view"] == "Beginner"
    assert not app.text_area
    assert any("Question to evidence flowchart" in item.proto.body for item in app.get("html"))

    app.radio(key="learn_foundations_answer").set_value("The official requirements and my completed coursework").run()
    assert app.session_state["lesson_beginner"]
    click(app, "Try a preset experiment")
    assert not app.exception and app.session_state["view"] == "Intermediate"
    assert len(app.get("plotly_chart")) == 1

    index = build_lab_index(load_runtime_catalog().model_dump_json())
    first = run_experiment(index, PRESETS["Program a sensor"], "keyword").hits[0].record_id
    app.selectbox(key="learn_rank_answer").set_value(first).run()
    assert app.session_state["lesson_intermediate"]
    app.session_state["lesson_preset_code"] = True
    app.run()
    assert any("def plot_experiment" in item.value for item in app.code)
    app.selectbox(key="learn_method").set_value("hybrid").run()
    click(app, "Create your variation")
    assert not app.exception and app.session_state["view"] == "Advanced"

    app.text_input(key="learn_variation_query").set_value(PRESETS["Learn image classification"])
    target = next(record.record_id for record in index.catalog.records if record.code == "ECE425")
    app.multiselect(key="learn_expected_records").set_value([target])
    click(app, "Compare with preset")
    assert [item.value for item in app.metric] == ["0 / 1", "1 / 1"]
    app.selectbox(key="learn_observation_record").set_value(target).run()
    app.selectbox(key="learn_observation_movement").set_value("Entered the ranking")
    app.text_area(key="learn_observation").set_value("ECE425 covers neural networks relevant to image classification.").run()
    click(app, "Save my observation")
    assert app.session_state["lesson_advanced"]
    assert any(item.proto.label == "Download my comparison" for item in app.get("download_button"))
    assert "profile" not in app.session_state

    click(app, "Use this question in Advisor")
    assert not app.exception and app.session_state["view"] == "Advisor"
    assert app.text_input(key="question").value == PRESETS["Learn image classification"]
    assert not app.session_state["profile"].question and "result" not in app.session_state
    click(app, "Update my roadmap")
    assert app.session_state["result"].context.allowed_record_ids
    app.session_state["plan_inspector"] = True
    app.run()
    assert not app.code
    app.session_state["plan_visualization_code"] = True
    app.run()
    assert not app.exception
    assert any("def ranking_html" in item.value and "def project_embeddings" in item.value for item in app.code)


@pytest.mark.parametrize(("preset", "method"), list(zip(PRESETS, ("hybrid", "semantic", "keyword"))))
def test_advanced_inherits_settings_and_preserves_draft(lesson_app, preset, method):
    app = lesson_app
    navigate(app, "Intermediate")
    app.selectbox(key="learn_preset").set_value(preset)
    app.selectbox(key="learn_method").set_value(method)
    click(app, "Create your variation")
    assert app.selectbox(key="learn_baseline").value == preset
    assert app.selectbox(key="learn_variant_method").value == method

    changed_method = "keyword" if method != "keyword" else "hybrid"
    question = "How do I program in C?"
    record = "uofa:ECE101:2026-2027"
    app.selectbox(key="learn_variant_method").set_value(changed_method)
    app.text_input(key="learn_variation_query").set_value(question)
    app.multiselect(key="learn_expected_records").set_value([record])
    navigate(app, "Beginner")
    navigate(app, "Advanced")
    assert app.selectbox(key="learn_baseline").value == preset
    assert app.selectbox(key="learn_variant_method").value == changed_method
    assert app.text_input(key="learn_variation_query").value == question
    assert app.multiselect(key="learn_expected_records").value == [record]
    assert "learn_variation" not in app.session_state
    navigate(app, "Intermediate")
    assert app.selectbox(key="learn_preset").value == preset
    assert app.selectbox(key="learn_method").value == method


def test_question_recovery_and_reflection_feedback(lesson_app):
    app = lesson_app
    navigate(app, "Advanced")
    question = PRESETS["Learn image classification"]
    target = "uofa:ECE425:2026-2027"
    app.text_input(key="learn_variation_query").set_value(question)
    app.multiselect(key="learn_expected_records").set_value([target])
    click(app, "Compare with preset")
    app.selectbox(key="learn_observation_record").set_value(target).run()
    app.selectbox(key="learn_observation_movement").set_value("Moved down")
    app.text_area(key="learn_observation").set_value("ECE425 covers neural networks.").run()
    click(app, "Save my observation")
    assert any("Check the two ranks" in item.value for item in app.warning)
    assert not app.session_state.get("lesson_advanced", False)

    app.selectbox(key="learn_observation_movement").set_value("Entered the ranking")
    app.text_area(key="learn_observation").set_value("x")
    click(app, "Save my observation")
    assert any("short explanation" in item.value for item in app.warning)
    assert not app.session_state.get("lesson_advanced", False)

    app.text_input(key="learn_variation_query").set_value("How do I study marine biology and coral reefs?")
    click(app, "Compare with preset")
    assert any("no match" in item.value for item in app.error)
    assert any("Showing your last comparison" in item.value for item in app.info)
    assert app.session_state["learn_variation"][2] == question

    app.text_input(key="learn_variation_query").set_value("Which instruction set should I learn?")
    click(app, "Compare with preset")
    assert any("Both rankings use Keyword" in item.value for item in app.info)
    assert app.selectbox(key="learn_observation_record").value is None


def test_carried_question_uses_existing_profile_and_neural_vectors(lesson_app, monkeypatch, fake_provider):
    app = lesson_app
    fake_provider.close = lambda: None
    monkeypatch.setenv("GEMINI_API_KEY", "controlled-placeholder")
    monkeypatch.setattr("src.controller.GeminiProvider", lambda *args, **kwargs: fake_provider)
    navigate(app, "Advisor")
    app.multiselect(key="completed_courses").set_value(["ECE101"])
    app.multiselect(key="current_courses").set_value(["ECE369A"])
    click(app, "Update my roadmap")
    profile = app.session_state["profile"].model_copy(deep=True)

    navigate(app, "Advanced")
    question = "I want to learn computer vision"
    app.text_input(key="learn_variation_query").set_value(question)
    app.multiselect(key="learn_expected_records").set_value(["uofa:ECE425:2026-2027"])
    click(app, "Compare with preset")
    assert any("Recognized topics · Machine learning" in item.value for item in app.caption)
    click(app, "Use this question in Advisor")
    assert app.session_state["profile"] == profile and fake_provider.document_calls == 0
    assert app.text_input(key="question").value == question

    navigate(app, "Advanced")
    assert app.text_input(key="learn_variation_query").value == question
    assert app.multiselect(key="learn_expected_records").value == ["uofa:ECE425:2026-2027"]
    navigate(app, "Advisor")
    assert app.text_input(key="question").value == question
    app.checkbox(key="use_ai").set_value(True).run()
    app.selectbox(key="ranking_method").set_value("semantic").run()
    click(app, "Update my roadmap")
    settle_advisor(app)
    assert app.session_state["profile"] == profile.model_copy(update={"question": question})
    app.session_state["plan_inspector"] = True
    app.session_state["lesson_embedding_comparison"] = True
    app.run()
    assert not app.exception
    assert any("embedding dimensions from fixture-vectors" in item.value for item in app.caption)
    table = next(table.value for table in app.dataframe if "Neural rank" in table.value.columns)
    assert len(table) == 7 and set(table["Neural rank"]) == set(range(1, 8))
    assert fake_provider.context.query == app.session_state["result"].context.query


@pytest.mark.parametrize(("question", "expected"), [
    ("How do I build a robot?", "ECE372A"),
    ("Can I use Arduino for robotics?", "ECE372A"),
    ("How can I teach a model to recognise pictures?", "ECE425"),
    ("I want to learn computer vision", "ECE425"),
    ("How do I program in C?", "ECE101"),
])
def test_supported_custom_questions_rank_relevant_records(question, expected):
    index = build_lab_index(load_runtime_catalog().model_dump_json())
    result = run_experiment(index, question, "hybrid")
    assert result.method == "hybrid"
    assert any(hit.record_id == f"uofa:{expected}:2026-2027" for hit in result.hits[:3])
