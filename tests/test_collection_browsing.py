"""Local browsing returns actual collection records and preserves profile work."""

import pytest

from src.catalog import load_runtime_catalog
from src.collection_filters import filter_collection
from test_app import app,submit


def test_collection_search_handles_code_spaces_case_and_combined_filters():
    catalog=load_runtime_catalog();before=catalog.model_dump_json()
    assert len(filter_collection(catalog))==28
    assert [r.code for r in filter_collection(catalog,"ece 372a","course","embedded")]==["ECE372A"]
    assert [r.record_id for r in filter_collection(catalog,"PICO","resource","embedded")]==["resource:pico"]
    assert filter_collection(catalog,"PICO","resource","ai_ml")==[]
    assert catalog.model_dump_json()==before


def test_search_is_literal_and_all_query_words_must_match():
    catalog=load_runtime_catalog()
    assert filter_collection(catalog,"[.*]")==[]
    assert filter_collection(catalog,"Pico impossible-no-match")==[]
    assert [r.record_id for r in filter_collection(catalog,"Pico SDK")]==["resource:pico"]
    assert len(filter_collection(catalog,"   "))==28


@pytest.fixture
def runtime_app(app,monkeypatch):
    monkeypatch.setattr("src.catalog.load_runtime_catalog",load_runtime_catalog)
    return app.run()


def collection_panels(app):
    return [item for item in app.expander if item.key and item.key.startswith("collection_record_")]


def test_collection_details_are_lazy_and_search_does_not_start_a_request(runtime_app,monkeypatch):
    app=runtime_app
    def forbidden(*a,**k):pytest.fail("Collection controls must not run source or model requests")
    monkeypatch.setattr("src.controller.run_advisor",forbidden)
    monkeypatch.setattr("httpx.Client.send",forbidden)
    before=app.session_state["profile"].model_dump_json()
    assert len(collection_panels(app))==28
    assert not any("Saved source snapshot" in c.value for c in app.caption)
    app.text_input(key="collection_query").set_value("ece 372a").run()
    assert not app.exception and len(collection_panels(app))==1
    assert collection_panels(app)[0].label.startswith("ECE372A · ")
    app.session_state["collection_record_uofa:ECE372A:2026-2027"]=True;app.run()
    assert not app.exception and any("Saved source snapshot" in c.value for c in app.caption)
    assert before==app.session_state["profile"].model_dump_json() and "result" not in app.session_state


def test_empty_filters_reset_and_profile_transition_preserves_browsing(runtime_app):
    app=runtime_app
    app.selectbox(key="collection_kind").set_value("resource")
    app.selectbox(key="collection_direction").set_value("embedded")
    app.text_input(key="collection_query").set_value("pico").run()
    assert len(collection_panels(app))==1 and collection_panels(app)[0].label.startswith("Raspberry Pi Pico")
    app.selectbox(key="career_id").set_value("embedded");submit(app)
    assert app.text_input(key="collection_query").value=="pico"
    assert app.selectbox(key="collection_kind").value=="resource" and len(collection_panels(app))==1
    app.text_input(key="collection_query").set_value("[.*]").run()
    assert not collection_panels(app) and any("No courses or resources match" in i.value for i in app.info)
    app.button(key="collection_reset").click().run()
    assert not app.exception and len(collection_panels(app))==28
    assert app.text_input(key="collection_query").value=="" and app.selectbox(key="collection_direction").value=="all"
