"""Reviewed track snapshots, source-section preparation labels, and MIT offerings."""

from datetime import timedelta

import httpx
import pytest

from src.catalog import build_evidence, load_catalog, load_runtime_catalog
from src.controller import run_advisor
from src.discovery import DiscoveryPlan, load_discovery_plans, match_course_requests
from src.models import Record, StudentProfile
from src.planning import learning_phase
from src.resource_sources import ResourceSnapshot, RESOURCE_URLS, extract_resource
from src.rules import evaluate_course
from src.sources import refresh_catalog
from test_discovery import client_for, program_page
from test_expanded_resources import only_resource
from test_runtime_catalog import runtime_client
from test_sources import NOW


MIT = {
    "resource:mit_algorithms": ("6.006", "Introduction to Algorithms", "Spring 2020"),
    "resource:mit_structures": ("6.004", "Computation Structures", "Spring 2017"),
}
INTRO = "Controlled course description connects foundational concepts with practical design and analysis exercises."


def mit_page(rid):
    number, title, term = MIT[rid]
    return (f'<html><head><title>Syllabus | {title} | Electrical Engineering and Computer Science | MIT OpenCourseWare</title>'
        f'<link rel="canonical" href="{RESOURCE_URLS[rid]}"></head><body>'
        '<nav><p>Unselected navigation.</p></nav><div id="course-banner">'
        f'<span class="course-number-term-detail">{number} | {term} | Undergraduate</span><h1>{title}</h1></div>'
        '<div id="course-title"><h2>Syllabus</h2></div><main id="course-content-section">'
        '<h3>Prerequisites</h3><p>Unselected prerequisite paragraph must not become the description.</p>'
        '<h3>Course Description</h3><aside><p>Unselected notice that resembles a course introduction.</p></aside>'
        '<div hidden><p>Hidden instructions must never be included in retrieved evidence.</p></div>'
        f'<p>{INTRO}</p><h3>Other section</h3><p>Unselected later material.</p></main></body></html>')


@pytest.mark.parametrize("rid", MIT)
def test_mit_offering_has_exact_number_term_and_description_scope(rid):
    data = extract_resource(mit_page(rid), rid, RESOURCE_URLS[rid])
    number, title, term = MIT[rid]
    assert data.title == "MIT " + number + " — " + title
    assert data.resource_version == term and data.summary == INTRO
    assert ResourceSnapshot.model_validate(data.model_dump()) == data


@pytest.mark.parametrize("rid", MIT)
@pytest.mark.parametrize("bad", ["document_title", "banner_title", "number", "term", "level", "hidden_banner", "duplicate_banner",
    "unscoped_banner", "root", "canonical", "description", "hidden_description", "duplicate_description", "script_only"])
def test_mit_identity_or_section_drift_keeps_content_unverified(rid, bad):
    number, title, term = MIT[rid]
    page = mit_page(rid)
    if bad == "document_title": page = page.replace('<title>Syllabus |', '<title>Different page |')
    elif bad == "banner_title": page = page.replace('<h1>' + title, '<h1>Different course')
    elif bad == "number": page = page.replace(number + ' |', '9.999 |')
    elif bad == "term": page = page.replace(term, 'Spring 2026')
    elif bad == "level": page = page.replace('| Undergraduate', '| Graduate')
    elif bad == "hidden_banner": page = page.replace('id="course-banner"', 'id="course-banner" hidden')
    elif bad == "duplicate_banner": page += f'<div id="course-banner"><h1>{title}</h1></div>'
    elif bad == "unscoped_banner": page = page.replace('id="course-banner"', 'id="unrelated-banner"')
    elif bad == "root": page = page.replace('id="course-content-section"', 'id="unrelated-content"')
    elif bad == "canonical": page = page.replace(RESOURCE_URLS[rid], RESOURCE_URLS[next(key for key in MIT if key != rid)])
    elif bad == "description": page = page.replace('<h3>Course Description', '<h3>Different section')
    elif bad == "hidden_description": page = page.replace('<p>' + INTRO + '</p>', '<p hidden>' + INTRO + '</p>')
    elif bad == "duplicate_description": page = page.replace('<h3>Other section', '<h3>Course Description')
    elif bad == "script_only": page = page.replace('<p>' + INTRO + '</p>', '<script>' + INTRO + '</script>')
    with pytest.raises(ValueError): extract_resource(page, rid, RESOURCE_URLS[rid])


@pytest.mark.parametrize("rid", MIT)
def test_mit_cache_rechecks_and_retains_dates_on_failure(rid, tmp_path):
    catalog = only_resource(rid)
    status = [200]
    calls = []
    def respond(request):
        calls.append(request)
        if status[0] == 200:
            return httpx.Response(200, text=mit_page(rid), headers={"Content-Type": "text/html", "ETag": '"mit-v1"'})
        return httpx.Response(status[0])
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        kwargs = dict(client=client, cache_dir=tmp_path, resource_checks=True)
        first = refresh_catalog(catalog, StudentProfile(), now=NOW, **kwargs)
        status[0] = 304
        second = refresh_catalog(catalog, StudentProfile(), now=NOW + timedelta(hours=1), **kwargs)
        status[0] = 404
        failed = refresh_catalog(catalog, StudentProfile(), now=NOW + timedelta(hours=2), **kwargs)
    assert len(calls) == 3 and calls[1].headers["if-none-match"] == '"mit-v1"'
    assert [r.checks[0].status for r in [first, second, failed]] == ["updated", "not_modified", "stale_cache"]
    assert second.catalog.sources[0].retrieved_at == NOW
    assert failed.catalog.sources[0].last_checked_at == NOW + timedelta(hours=1)
    assert failed.catalog.sources[0].verification_status == "stale"
    record = second.catalog.records[0]
    assert record.catalog_version is None and record.credits is None and record.resource_version == MIT[rid][2]
    assert "course equivalency" in build_evidence(second.catalog)[0].text


@pytest.mark.parametrize("code,identity,section", [("ECE352", "0121181", "R15487/L30"),
    ("ECE381A", "0375981", "R15487/L30"), ("CSC372", "0098011", "R15487/L20")])
def test_track_snapshot_retains_edition_identity_and_unknown_enrollment(code, identity, section):
    catalog = load_runtime_catalog()
    record = next(r for r in catalog.records if r.code == code)
    assert record.discovery.course_id == identity and record.discovery.section_ids == [section]
    assert record.catalog_version == "2026-2027" and record.study_stage == "intermediate"
    assert not record.rule_reviewed and not record.rule_evidence
    assert evaluate_course(record, StudentProfile(standing="Senior", programming_background="experienced")).status == "unknown"
    assert record.field_sources["summary"] == "catalog:" + code
    assert learning_phase(record, StudentProfile(), evaluate_course(record, StudentProfile())) == "build"


@pytest.mark.parametrize("phrase,code", [("device electronics", "ECE352"), ("electromagnetic fields", "ECE381A"),
    ("comparative programming languages", "CSC372")])
def test_track_phrase_routes_the_saved_record(phrase, code):
    assert match_course_requests(StudentProfile(question=phrase), load_discovery_plans()).codes == [code]
    result = run_advisor(load_runtime_catalog(), StudentProfile(question=code, programming_background="experienced"), refresh_sources=False)
    assert "uofa:" + code + ":2026-2027" in result.context.allowed_record_ids


@pytest.mark.parametrize("stage_map,override,expected", [({"R15487/L20": "advanced"}, None, "advanced"),
    ({"R15487/L20": "advanced"}, "intermediate", "intermediate"),
    ({"R15487/L20": "intermediate", "R15487/L30": "advanced"}, None, "advanced")])
def test_unfamiliar_track_links_do_not_inherit_the_foundation_default(tmp_path, stage_map, override, expected):
    data = load_discovery_plans()[1].model_dump(mode="json")
    data.update(section_ids=list(stage_map), section_stages=stage_map, course_codes={}, course_stages={}, course_phrases={})
    identity, code = "7654323", "ECE414"
    if override:
        data["course_codes"] = {identity: code}
        data["course_stages"] = {code: override}
    plan = DiscoveryPlan.model_validate(data)
    catalog = load_catalog()
    record = Record(record_id="fixture:track", kind="course", code=code, title="Controlled upper-level course",
        summary="Controlled source description of a digital hardware design course.", credits=3,
        source_ids=["fixture"], catalog_version="2026-2027")
    pages = {plan.program_code: program_page(plan, ids=[identity])}
    with client_for(catalog, [plan], {identity: record}, programs=pages) as client:
        result = refresh_catalog(catalog, StudentProfile(career_id="embedded"), client=client,
            cache_dir=tmp_path, discovery_plans=[plan], now=NOW)
    found = next(r for r in result.catalog.records if r.code == code)
    assert found.study_stage == expected and evaluate_course(found, StudentProfile()).status == "unknown"
    assert result.discovery_selection["version"] == "p07-course-request-priority-v4"


def test_unconfigured_section_annotations_are_rejected():
    data = load_discovery_plans()[1].model_dump(mode="json")
    data["section_stages"] = {"R999/L99": "foundation"}
    with pytest.raises(ValueError): DiscoveryPlan.model_validate(data)


@pytest.mark.parametrize("career,code", [("ai_ml", "CSC372"), ("embedded", "ECE381A")])
def test_track_request_and_both_mit_resources_reach_fresh_context(tmp_path, career, code):
    catalog = load_runtime_catalog()
    profile = StudentProfile(career_id=career, programming_background="experienced",
        question=code + " with MIT 6.006 and MIT 6.004")
    pages = {RESOURCE_URLS[rid]: mit_page(rid) for rid in MIT}
    seen = []
    with runtime_client(catalog, seen, pages) as client:
        def refresh(catalog, profile, **kwargs):
            return refresh_catalog(catalog, profile, client=client, discovery_plans=load_discovery_plans(),
                resource_checks=True, now=NOW, **kwargs)
        result = run_advisor(catalog, profile, source_refresher=refresh, source_cache_dir=tmp_path)
    assert "uofa:" + code + ":2026-2027" in result.context.allowed_record_ids
    assert result.context.source_freshness["catalog:" + code].verification_status == "verified"
    assert [rid for rid in result.context.allowed_record_ids if rid.startswith("resource:")] == list(MIT)
    assert all(result.context.source_freshness[rid].verification_status == "verified" for rid in MIT)
    assert sum(url.startswith("https://catalog.arizona.edu/courses/") for url in seen) == 8
    assert sum("/programs/" in url for url in seen) <= 2
    assert sum("ocw.mit.edu" in url for url in seen) == 2
    assert sum("resource-check limit" in issue for issue in result.issues) == 1
    assert not any("identity is unsupported" in issue for issue in result.issues)
    assert not result.generation_complete
