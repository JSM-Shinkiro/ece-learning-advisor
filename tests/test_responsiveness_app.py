"""Closed inspector and explicit refresh controls preserve current session state."""

from test_app import app, open_inspector, submit


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
    assert len(app.get("plotly_chart"))==1 and app.json and app.dataframe
    app.session_state["plan_inspector"]=False; app.run()
    assert not app.exception and not app.get("plotly_chart") and not app.json
    assert calls==[1] and app.session_state["result"] is result


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
