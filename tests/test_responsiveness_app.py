"""Closed inspector and explicit refresh controls preserve current session state."""

from threading import Event

import pytest

from src.models import SourceCheck
from src.sources import CatalogRefresh
from test_app import app, open_inspector, settle_advisor, submit
from test_sources import NOW


@pytest.fixture
def blocked_sources(app, monkeypatch):
    started, release = Event(), Event()
    calls, jobs = [], []

    def refresh(catalog, profile, **options):
        calls.append(profile.question)
        source = catalog.sources[0]
        source.verification_status = "verified"
        source.last_checked_at = NOW
        if not profile.question:
            started.set()
            assert release.wait(10)
        check = SourceCheck(source_id=source.source_id, code="ECE101", url=source.url,
                            status="unchanged", attempted_at=NOW, last_checked_at=NOW)
        return CatalogRefresh(catalog, checks=[check])

    monkeypatch.setenv("ECE_REFRESH_SOURCES", "true")
    monkeypatch.setattr("src.controller.refresh_catalog", refresh)
    app.run()
    yield started, release, calls, jobs
    release.set()
    for job in jobs:
        assert job.wait(5)


def begin_source_update(app, blocked_sources):
    started, _, _, jobs = blocked_sources
    next(b for b in app.button if b.label == "Update my roadmap").click().run()
    job = app.session_state["advisor_job"]
    jobs.append(job)
    assert started.wait(5)
    app.run()
    assert not app.exception and not job.wait()
    return job


def test_preview_uses_saved_evidence_until_source_update_finishes(app, blocked_sources, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Preview mode must not initialize the model")

    monkeypatch.setattr("src.controller.GeminiProvider", forbidden)
    job = begin_source_update(app, blocked_sources)
    _, release, calls, _ = blocked_sources
    preview = app.session_state["result"]
    assert preview.context.allowed_record_ids
    assert preview.trace["source_refresh"] == {"enabled": False, "reason": "pending"}
    assert all(source.verification_status == "snapshot" for source in preview.catalog.sources)
    assert preview.catalog.sources[0].last_checked_at != NOW
    assert any(button.key.startswith("complete_") for button in app.button)
    assert app.status[0].label == "Saved-data plan ready · checking official sources"
    assert not any("AI assistance" in caption.value for caption in app.caption)

    open_inspector(app)
    assert any("Saved-data plan built in" in caption.value for caption in app.caption)
    assert app.session_state["result"] is preview and calls == [""]
    release.set()
    assert job.wait(5)
    settle_advisor(app)
    result = app.session_state["result"]
    assert result.catalog.sources[0].verification_status == "verified"
    assert result.trace["initial_plan"]["ready_seconds"] <= result.timings["total"]
    assert result.trace["source_refresh"]["checks"][0]["status"] == "unchanged"
    assert preview.catalog.sources[0].verification_status == "snapshot"
    assert calls == [""] and not app.exception


@pytest.mark.parametrize("keep_saved", [False, True])
def test_delayed_source_checks_cannot_replace_a_kept_or_newer_plan(app, blocked_sources, keep_saved):
    job = begin_source_update(app, blocked_sources)
    _, release, calls, _ = blocked_sources
    if keep_saved:
        next(b for b in app.button if b.label == "Keep saved-data plan").click().run()
        assert any("Source checks stopped. Your saved-data plan" in item.value for item in app.info)
    else:
        app.text_input(key="question").set_value("ECE101")
        submit(app)
    latest = app.session_state["result"]
    assert latest.context.profile.question == ("" if keep_saved else "ECE101")
    assert job.is_cancelled()
    release.set()
    assert job.wait(5)
    app.run()
    assert not app.exception and app.session_state["result"] is latest
    assert calls == ([""] if keep_saved else ["", "ECE101"])


def test_full_worker_pool_uses_saved_data_without_source_calls(app, monkeypatch):
    from src.advisor_jobs import AdvisorBusy

    def busy(*args, **kwargs):
        raise AdvisorBusy()

    def forbidden(*args, **kwargs):
        pytest.fail("An overloaded update should use the local catalog")

    monkeypatch.setenv("ECE_REFRESH_SOURCES", "true")
    monkeypatch.setattr("src.advisor_jobs.start_advisor_job", busy)
    monkeypatch.setattr("src.controller.refresh_catalog", forbidden)
    submit(app)
    assert not app.exception and "advisor_job" not in app.session_state
    assert app.session_state["result"].context.allowed_record_ids
    assert any("Roadmap updates are busy" in warning.value for warning in app.warning)


def test_inspector_builds_nothing_until_open_and_hides_it_again(app, monkeypatch):
    import src.controller
    original=src.controller.run_advisor
    calls=[]
    def run(*args,**kwargs):
        calls.append(1)
        return original(*args,**kwargs)
    monkeypatch.setattr(src.controller,"run_advisor",run)
    submit(app)
    result=app.session_state["result"]
    assert not app.get("plotly_chart") and not app.json and not app.dataframe
    open_inspector(app)
    assert not app.get("plotly_chart") and app.json and app.dataframe
    assert any('data-ece-ranking="html"' in item.proto.body for item in app.get("html"))
    app.session_state["plan_inspector"]=False; app.run()
    assert not app.exception and not app.get("plotly_chart") and not app.json
    assert calls==[1] and app.session_state["result"] is result


def test_vector_inspection_preserves_coordinates_and_actual_cosine(app, monkeypatch, fake_provider, tmp_path):
    import json
    import numpy as np
    import src.controller
    from src.retrieval import project_embeddings
    fake_provider.close=lambda:None
    monkeypatch.setattr(src.controller,"GeminiProvider",lambda *a,**k:fake_provider)
    monkeypatch.setenv("GEMINI_API_KEY","fixture-key")
    monkeypatch.setenv("ECE_CACHE_DIR",str(tmp_path))
    app.run();app.checkbox(key="use_ai").set_value(True).run()
    app.selectbox(key="ranking_method").set_value("hybrid").run()
    submit(app);open_inspector(app)
    assert not app.exception
    result=app.session_state["result"]
    assert result.vectors is not None and len(app.get("plotly_chart"))==1
    figure=json.loads(app.get("plotly_chart")[0].proto.spec)
    assert figure['data'][1]['name']=='Your query'
    _,query_point=project_embeddings(result.vectors,result.query_vector)
    assert np.allclose([figure['data'][1]['x'][0],figure['data'][1]['y'][0]],query_point)
    details=next(json.loads(item.value) for item in app.json if 'cosine_similarity' in item.value)
    q,v=result.query_vector,result.vectors[0]
    assert np.isclose(details['cosine_similarity'],np.dot(q,v)/(np.linalg.norm(q)*np.linalg.norm(v)))
    # Inspector selection and closing keep the exact saved result rather than regenerating it.
    next(s for s in app.selectbox if s.label=='Inspect a record vector').select_index(1).run()
    assert not app.exception and app.session_state['result'] is result
    details=next(json.loads(item.value) for item in app.json if 'cosine_similarity' in item.value)
    v=result.vectors[1]
    assert np.isclose(details['cosine_similarity'],np.dot(q,v)/(np.linalg.norm(q)*np.linalg.norm(v)))


def test_force_check_applies_profile_and_is_one_shot(app, monkeypatch):
    from src.sources import CatalogRefresh
    calls=[]
    def refresh(catalog,profile,**kwargs):
        calls.append((profile.interests,kwargs["reuse_seconds"]))
        return CatalogRefresh(catalog.model_copy(deep=True))
    monkeypatch.setattr("src.controller.refresh_catalog",refresh)
    monkeypatch.setenv("ECE_REFRESH_SOURCES","true")
    app.run()
    app.text_area(key="interests").set_value("Microcontrollers")
    next(b for b in app.button if b.label=="Check sources again").click().run()
    settle_advisor(app)
    assert not app.exception and calls==[("Microcontrollers",0)]
    app.run(); assert len(calls)==1
    submit(app)
    assert calls==[("Microcontrollers",0),("Microcontrollers",300)]


def test_offline_source_refresh_control_is_disabled(app):
    assert next(b for b in app.button if b.label=="Check sources again").disabled


def test_recent_source_notice_is_visible_without_opening_inspector(app, monkeypatch):
    from src.models import SourceCheck
    from src.sources import CatalogRefresh
    from test_sources import NOW
    def refresh(catalog,profile,**kwargs):
        source=catalog.sources[0]
        return CatalogRefresh(catalog.model_copy(deep=True),checks=[SourceCheck(source_id=source.source_id,
            code="ECE101",url=source.url,status="recent_cache",attempted_at=NOW,last_checked_at=NOW)])
    monkeypatch.setattr("src.controller.refresh_catalog",refresh)
    monkeypatch.setenv("ECE_REFRESH_SOURCES","true")
    submit(app)
    assert not app.exception
    assert any("Used 1 recent source checks for this update" in c.value for c in app.caption)
    assert not app.get("plotly_chart")
