"""Catalog breadth cannot silently become eligibility, mapping or unbounded RAG work."""

from datetime import datetime, timezone

import pytest
import httpx

from src.catalog import build_evidence, corpus_hash, load_runtime_catalog
from src.controller import run_advisor
from src.course_directory import (add_requested_courses, build_directory,
                                  filter_directory, load_course_directory)
from src.models import Completion, StudentProfile
from src.sources import refresh_catalog
from test_app import app, submit


@pytest.fixture
def directory_app(app,monkeypatch):
    # Historical interaction cases keep their original five-course fixture;
    # these cases explicitly enable the new published catalog.
    monkeypatch.setattr("src.course_directory.load_course_directory",load_course_directory)
    return app.run()


def test_published_inventory_covers_every_saved_ece_and_preserves_variable_credits():
    directory = load_course_directory()
    lookup = {c.code:c for c in directory.courses}
    assert directory.catalog_version == "2026-2027" and len(lookup) == 78
    assert directory.published_ece_total == 186 and directory.excluded_non_undergraduate == 108
    assert [(p.skip,p.received) for p in directory.pages] == [(0,100),(100,86)]
    assert {r.code for r in load_runtime_catalog().records if r.code and r.code.startswith("ECE")} <= set(lookup)
    assert lookup["ECE498A"].credits_label == "2–3 credits"
    assert lookup["ECE493"].credits_label == "1–12 credits"
    assert lookup["ECE413"].url == "https://catalog.arizona.edu/courses/0396851"
    assert all(c.code[3] in "1234" for c in directory.courses)


def raw_course(code="ECE413", identity="0433021", career="Undergraduate"):
    return dict(code=code, courseGroupId=identity, subjectCode="ECE", career=career, status="Active",
        catalogPrint=True, courseApproved="Approved", longName="Synthetic directory test course",
        description="<p>A test description.</p>", credits={"creditHours":{"min":2,"max":3}},
        effectiveStartDate="2026-08-01", requirementGroup="12345")


def build(pages):
    return build_directory(pages, catalog_version="2026-2027", catalog_id="test",
        effective_dates="2027-01-13,2027-01-13", retrieved_at=datetime(2026,11,8,tzinfo=timezone.utc), filters={})


def test_inventory_builder_requires_all_pages_and_retains_source_ranges():
    pages = [dict(skip=0,listLength=2,data=[raw_course()]),
             dict(skip=1,listLength=2,data=[raw_course("ECE513","0433022","Graduate")])]
    with pytest.raises(ValueError, match="incomplete"):
        build(pages[:1])
    directory = build(pages)
    assert len(directory.courses)==1 and directory.excluded_non_undergraduate==1
    assert directory.courses[0].summary=="A test description."
    assert directory.courses[0].credits_label=="2–3 credits"


@pytest.mark.parametrize("change",["duplicate","subject","career","total","overlap","unpublished","range","boolean"])
def test_inventory_rejects_identity_pagination_and_credit_failures(change):
    pages=[dict(skip=0,listLength=2,data=[raw_course()]),
           dict(skip=1,listLength=2,data=[raw_course("ECE414A","0433022")])]
    target=pages[1]["data"][0]
    if change=="duplicate":target["courseGroupId"]="0433021"
    elif change=="subject":target["subjectCode"]="CSC"
    elif change=="career":target["career"]="Graduate"
    elif change=="total":pages[1]["listLength"]=3
    elif change=="overlap":pages[1]["skip"]=0
    elif change=="unpublished":target["catalogPrint"]=False
    elif change=="range":target["credits"]["creditHours"]={"min":5,"max":2}
    else:target["credits"]["creditHours"]["min"]=True
    with pytest.raises(ValueError):build(pages)


def test_directory_search_is_literal_handles_spaced_codes_and_level_filter():
    directory=load_course_directory()
    assert [c.code for c in filter_directory(directory,"ece 413","4")]==["ECE413"]
    assert filter_directory(directory,"ECE413","3")==[]
    assert filter_directory(directory,"[.*]")==[]
    assert filter_directory(directory,"circuits impossible-no-match")==[]
    assert all(c.code[3]=="2" for c in filter_directory(directory,level="2"))


def test_requested_catalog_overlay_is_bounded_edition_bound_and_does_not_change_baseline():
    catalog=load_runtime_catalog(); before=catalog.model_dump_json(); old_hash=corpus_hash(catalog)
    profile=StudentProfile(question="ECE 413, ECE414A, ECE415, ECE417 and ECE413")
    active, trace=add_requested_courses(catalog,load_course_directory(),profile)
    assert trace["added"]==["ECE413","ECE414A","ECE415"] and trace["omitted"]==["ECE417"]
    assert len(build_evidence(active))==37
    new=[r for r in active.records if r.code in trace["added"]]
    assert all(r.rule.type=="unknown" and not r.rule_reviewed and not r.rule_evidence
               and not r.career_ids and r.study_stage=="unreviewed" for r in new)
    assert catalog.model_dump_json()==before and corpus_hash(catalog)==old_hash
    other=profile.model_copy(update={"catalog_version":"2025-2026"})
    unchanged,trace=add_requested_courses(catalog,load_course_directory(),other)
    assert unchanged is catalog and trace["reason"]=="different_catalog_edition"


def test_unrequested_and_recorded_catalog_courses_stay_out_of_advisor_index():
    catalog=load_runtime_catalog();directory=load_course_directory()
    assert add_requested_courses(catalog,directory,StudentProfile(question="circuits"))[0] is catalog
    profile=StudentProfile(question="ECE413 ECE414A ECE415",completed=[Completion(course_code="ECE413")],
        current_enrollment=["ECE414A"])
    active,trace=add_requested_courses(catalog,directory,profile)
    assert trace["added"]==["ECE415"] and len(build_evidence(active))==35


def test_expanded_directory_requests_share_the_existing_eight_course_check_budget(tmp_path):
    requests=[]
    def failed(request):
        requests.append(str(request.url))
        return httpx.Response(404,request=request)
    with httpx.Client(transport=httpx.MockTransport(failed)) as client:
        def refresh(catalog,profile,**kw):
            return refresh_catalog(catalog,profile,client=client,**kw)
        result=run_advisor(load_runtime_catalog(),StudentProfile(question="ECE413 ECE414A ECE415 ECE417"),
            course_directory=load_course_directory(),source_refresher=refresh,
            source_cache_dir=tmp_path/"sources",cache_dir=tmp_path/"embeddings")
    course_requests=[url for url in requests if "/courses/" in url]
    assert len(course_requests)==8 and len(set(course_requests))==8
    assert {c.url for c in load_course_directory().courses if c.code in {"ECE413","ECE414A","ECE415"}} <= set(course_requests)
    assert result.trace["course_directory"]["omitted"]==["ECE417"]
    assert any("three additional courses" in issue for issue in result.issues)
    assert all(r.rule.type=="unknown" for r in result.catalog.records if r.study_stage=="unreviewed")


@pytest.mark.parametrize("code,credits",[("ECE413",3),("ECE493",None)])
def test_advisor_handles_requested_unmapped_and_variable_credit_course_without_clearance(code,credits,tmp_path):
    result=run_advisor(load_runtime_catalog(),StudentProfile(question="What can I learn in "+code+"?"),
        refresh_sources=False,course_directory=load_course_directory(),cache_dir=tmp_path)
    rid=f"uofa:{code}:2026-2027"
    assert not result.coverage_notice and rid in result.context.allowed_record_ids
    assert result.context.rule_results[rid].status=="unknown"
    assert result.context.suggested_phases[rid]=="explore"
    assert next(r for r in result.catalog.records if r.record_id==rid).credits==credits
    stage=next(s for s in result.context.allowed_statements if s.record_id==rid and s.field=="learning_stage")
    assert "have not been reviewed" in stage.text
    assert result.trace["course_directory"]["added"]==[code]


NEW_CODES = sorted({c.code for c in load_course_directory().courses}
                   - {r.code for r in load_runtime_catalog().records if r.kind=="course"})


@pytest.mark.parametrize("code",NEW_CODES)
def test_every_new_published_course_is_reachable_as_unverified_exploration(code,tmp_path):
    result=run_advisor(load_runtime_catalog(),StudentProfile(question="Explore "+code),refresh_sources=False,
        course_directory=load_course_directory(),cache_dir=tmp_path)
    rid=f"uofa:{code}:2026-2027"
    assert rid in result.context.allowed_record_ids and result.context.suggested_phases[rid]=="explore"
    assert result.context.rule_results[rid].status=="unknown"
    assert result.trace["course_directory"]["added"]==[code]


def test_production_preflight_rejects_a_broken_directory_without_exposing_parser_details(tmp_path,monkeypatch):
    from src.deployment import check_deployment
    def fail(*a,**kw):raise ValueError("private-parser-detail")
    monkeypatch.setattr("src.deployment.load_course_directory",fail)
    report=check_deployment(environ={"ECE_CACHE_DIR":str(tmp_path)})
    assert not report["passed"] and "private-parser-detail" not in str(report)


def test_directory_browsing_is_local_paged_and_does_not_touch_profile_or_plan(directory_app,monkeypatch):
    app=directory_app
    def forbidden(*a,**kw):pytest.fail("Local directory browsing must not call HTTP or advisor")
    monkeypatch.setattr("src.controller.run_advisor",forbidden)
    monkeypatch.setattr("httpx.Client.send",forbidden)
    profile=app.session_state["profile"].model_dump_json()
    app.radio(key="collection_scope").set_value("ece").run()
    panels=lambda:[x for x in app.expander if x.key and x.key.startswith("directory_record_")]
    assert len(panels())==15 and "78 matching courses · Page 1 of 6" in " ".join(c.value for c in app.caption)
    app.button(key="directory_next").click().run()
    assert not app.exception and "Page 2 of 6" in " ".join(c.value for c in app.caption)
    app.text_input(key="directory_query").set_value("ece 493").run()
    assert not app.exception and len(panels())==1
    assert "Page 1 of 1" in " ".join(c.value for c in app.caption)
    app.session_state["directory_record_ECE493"]=True;app.run()
    assert any("1–12 credits" in c.value for c in app.caption)
    assert app.session_state["profile"].model_dump_json()==profile and "result" not in app.session_state


def test_directory_course_pick_and_completion_survive_profile_export(directory_app):
    app=directory_app
    from src.profiles import export_profile, import_profile
    assert any("ECE413" in x for x in app.multiselect(key="completed_courses").options)
    app.multiselect(key="current_courses").set_value(["ECE413"])
    submit(app)
    assert not app.exception and app.session_state["profile"].current_enrollment==["ECE413"]
    app.button(key="finish_ECE413").click().run()
    assert not app.exception and any(c.course_code=="ECE413" for c in app.session_state["profile"].completed)
    assert app.multiselect(key="completed_courses").value==["ECE413"]
    assert import_profile(export_profile(app.session_state["profile"]).encode())==app.session_state["profile"]


def test_explore_from_catalog_creates_grounded_unknown_preparation_card(directory_app):
    app=directory_app
    app.radio(key="collection_scope").set_value("ece").run()
    app.text_input(key="directory_query").set_value("ECE413").run()
    app.session_state["directory_record_ECE413"]=True;app.run()
    app.button(key="directory_ask_ECE413").click().run()
    assert not app.exception
    result=app.session_state["result"];rid="uofa:ECE413:2026-2027"
    assert rid in result.context.allowed_record_ids and result.context.suggested_phases[rid]=="explore"
    assert any(h.value=="Explore requested courses" for h in app.subheader)
    assert app.session_state["profile"].question=="What can I learn in ECE413?"
    assert app.text_input(key="directory_query").value=="ECE413"
