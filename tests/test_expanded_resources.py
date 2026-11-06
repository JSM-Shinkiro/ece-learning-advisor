"""New official resource layouts, bounded selection, and independent freshness."""

from datetime import timedelta

import httpx
import pytest

from src.catalog import build_evidence, load_runtime_catalog
from src.controller import run_advisor
from src.models import Catalog, StudentProfile
from src.resource_sources import (MAX_RESOURCE_SOURCES, RESOURCE_URLS, ResourceSnapshot,
                                  extract_resource, prepare_resource_jobs)
from src.sources import refresh_catalog
from test_sources import NOW
from test_runtime_catalog import runtime_client


NEW_RESOURCES = ["resource:python", "resource:numpy", "resource:sklearn", "resource:pico"]
INTRO = "Controlled introduction describes the supported programming workflow and its initial practice exercises."
FIXTURES = {
    "resource:python": ("The Python Tutorial — Python 3.15.2 documentation", "The Python Tutorial",
        '<div class="body" role="main">', '</div>', None, "3.15.2"),
    "resource:numpy": ("NumPy quickstart — NumPy v2.5 Manual", "NumPy quickstart",
        '<main><article class="bd-article">', '</article></main>', "Prerequisites", "2.5"),
    "resource:sklearn": ("Getting Started — scikit-learn 1.9.1 documentation", "Getting Started",
        '<main><article class="bd-article">', '</article></main>', None, "1.9.1"),
    "resource:pico": ("The C/C++ SDK - Raspberry Pi Documentation", "The C/C++ SDK",
        '<section id="content" role="main">', '</section>', "Raspberry Pi Pico C/C++ SDK", "unversioned documentation"),
}


def resource_page(rid, *, intro=INTRO):
    title, heading, start, end, section, _ = FIXTURES[rid]
    intro_heading = '<h2>' + section + '</h2>' if section else ''
    return (f'<html><head><title>{title}</title><link rel="canonical" href="{RESOURCE_URLS[rid]}"></head>'
        '<body><nav><p>Unselected navigation.</p></nav><svg><title>Decorative logo</title></svg>'
        f'{start}<h1>{heading}</h1>{intro_heading}'
        '<div class="edit-link"><p>Unselected edit link with enough words to resemble an introductory paragraph.</p></div>'
        '<div hidden><p>A hidden paragraph must never be treated as retrieved evidence.</p></div>'
        '<script>Executable text must never become source evidence.</script><pre>Unselected code</pre>'
        f'<p>{intro}</p><h2>Later section</h2><p>Unselected later material.</p>{end}</body></html>')


def only_resource(rid):
    runtime = load_runtime_catalog()
    record = next(r for r in runtime.records if r.record_id == rid)
    return Catalog(version=runtime.version, catalog_version=runtime.catalog_version, records=[record],
        sources=[s for s in runtime.sources if s.source_id in record.source_ids])


@pytest.mark.parametrize("rid", NEW_RESOURCES)
def test_intro_identity_version_and_visible_section_boundaries(rid):
    snapshot = extract_resource(resource_page(rid), rid, RESOURCE_URLS[rid])
    assert snapshot.summary == INTRO
    assert snapshot.resource_version == FIXTURES[rid][-1]
    assert snapshot.title == next(r.title for r in load_runtime_catalog().records if r.record_id == rid)
    assert ResourceSnapshot.model_validate(snapshot.model_dump()) == snapshot


@pytest.mark.parametrize("rid", NEW_RESOURCES)
@pytest.mark.parametrize("bad", ["title", "heading", "root", "canonical", "empty", "script_only", "duplicate_root", "missing_section"])
def test_resource_identity_or_layout_changes_cannot_become_fresh_evidence(rid, bad):
    title, heading, start, end, section, _ = FIXTURES[rid]
    page = resource_page(rid)
    if bad == "title": page = page.replace('<title>' + title, '<title>Wrong identity')
    elif bad == "heading": page = page.replace('<h1>' + heading, '<h1>Wrong identity')
    elif bad == "root": page = page.replace(start, '<div>').replace(end, '</div>')
    elif bad == "canonical": page = page.replace(RESOURCE_URLS[rid], 'https://unreviewed.example/resource')
    elif bad == "empty": page = page.replace(INTRO, '')
    elif bad == "script_only": page = page.replace(INTRO, '<script>' + INTRO + '</script>')
    elif bad == "duplicate_root": page += start + end
    elif section: page = page.replace('<h2>' + section, '<h2>Unreviewed section')
    else: page = page.replace('<h1>' + heading, '<h1>Missing introduction')
    with pytest.raises(ValueError): extract_resource(page, rid, RESOURCE_URLS[rid])


@pytest.mark.parametrize("rid", NEW_RESOURCES)
def test_snapshot_cannot_claim_another_resource_or_an_invented_version(rid):
    snapshot = extract_resource(resource_page(rid), rid, RESOURCE_URLS[rid]).model_dump()
    with pytest.raises(ValueError): ResourceSnapshot.model_validate({**snapshot, "resolved_url": "https://unreviewed.example/"})
    with pytest.raises(ValueError): ResourceSnapshot.model_validate({**snapshot, "resource_version": "invented release"})
    with pytest.raises(ValueError): ResourceSnapshot.model_validate({**snapshot, "title": "Another resource"})


@pytest.mark.parametrize("rid", NEW_RESOURCES)
def test_new_resource_cache_rechecks_on_use_and_failure_retains_original_date(rid, tmp_path):
    catalog = only_resource(rid)
    original = catalog.model_dump_json()
    seen = []
    status = [200]
    def respond(request):
        assert str(request.url) == RESOURCE_URLS[rid]
        seen.append(dict(request.headers))
        if status[0] == 200:
            return httpx.Response(200, text=resource_page(rid), headers={"Content-Type": "text/html", "ETag": '"intro-v1"'})
        return httpx.Response(status[0])
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        kwargs = dict(client=client, cache_dir=tmp_path, resource_checks=True)
        first = refresh_catalog(catalog, StudentProfile(career_id="exploring"), now=NOW, **kwargs)
        status[0] = 304
        second = refresh_catalog(catalog, StudentProfile(career_id="exploring"), now=NOW + timedelta(hours=1), **kwargs)
        status[0] = 404
        failed = refresh_catalog(catalog, StudentProfile(career_id="exploring"), now=NOW + timedelta(hours=2), **kwargs)
    assert [r.checks[0].status for r in [first, second, failed]] == ["updated", "not_modified", "stale_cache"]
    assert len(seen) == 3 and seen[1]["if-none-match"] == '"intro-v1"'
    assert second.catalog.sources[0].retrieved_at == NOW
    assert second.catalog.sources[0].last_checked_at == NOW + timedelta(hours=1)
    assert failed.catalog.sources[0].last_checked_at == second.catalog.sources[0].last_checked_at
    assert failed.catalog.sources[0].verification_status == "stale"
    assert failed.catalog.records[0].summary == INTRO
    assert catalog.model_dump_json() == original
    evidence = build_evidence(first.catalog)[0]
    assert "university credit or course equivalency" in evidence.text
    assert first.catalog.records[0].catalog_version is None


@pytest.mark.parametrize("question,career,expected", [
    ("NumPy with the Python tutorial", "ai_ml", ["resource:numpy", "resource:python"]),
    ("scikit-learn model evaluation", "ai_ml", ["resource:sklearn", "resource:pytorch"]),
    ("Pico C/C++ SDK", "embedded", ["resource:pico", "resource:cs50"]),
    ("NumPy", "embedded", ["resource:cs50", "resource:python"]),
    ("Python tutorial with scikit-learn", "exploring", ["resource:python", "resource:sklearn"]),
])
def test_request_relevant_resources_take_the_two_check_slots(question, career, expected):
    jobs, skipped = prepare_resource_jobs(load_runtime_catalog(), StudentProfile(career_id=career, question=question), NOW)
    assert [job.record_id for job in jobs] == expected
    assert len(jobs) == MAX_RESOURCE_SOURCES
    assert all(check.status == "skipped" for check in skipped)
    assert not set(expected) & {check.code for check in skipped}


def test_resource_checks_are_independent_of_unsupported_academic_editions(tmp_path):
    catalog = only_resource("resource:numpy")
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200,
        text=resource_page("resource:numpy"), headers={"Content-Type": "text/html"}))) as client:
        result = refresh_catalog(catalog, StudentProfile(catalog_version="2025-2026"),
            client=client, cache_dir=tmp_path, resource_checks=True, now=NOW)
    assert result.checks[0].status == "updated"
    assert result.catalog.records[0].resource_version == "2.5"


@pytest.mark.parametrize("question,rid", [("NumPy numerical arrays", "resource:numpy"),
    ("scikit-learn model evaluation", "resource:sklearn"), ("Raspberry Pi Pico SDK", "resource:pico")])
def test_requested_resources_reach_the_grounded_context(question, rid):
    result = run_advisor(load_runtime_catalog(), StudentProfile(question=question,
        career_id="embedded" if rid == "resource:pico" else "ai_ml", programming_background="experienced"), refresh_sources=False)
    assert rid in result.context.allowed_record_ids
    assert any(e.record_id == rid and rid in e.source_ids for e in result.context.evidence)
    assert result.context.source_freshness[rid].verification_status == "snapshot"


@pytest.mark.parametrize("background", ["new", "experienced"])
def test_checked_explicit_resources_are_the_resources_presented_in_context(tmp_path, background):
    catalog = load_runtime_catalog()
    profile = StudentProfile(question="CSC210 and ECE310; practice with NumPy and scikit-learn.",
        programming_background=background)
    seen = []
    resources = ["resource:numpy", "resource:sklearn"]
    pages = {RESOURCE_URLS[rid]: resource_page(rid) for rid in resources}
    with runtime_client(catalog, seen, pages) as client:
        def refresh(catalog, profile, **kwargs):
            return refresh_catalog(catalog, profile, client=client, resource_checks=True, now=NOW, **kwargs)
        result = run_advisor(catalog, profile, source_refresher=refresh, source_cache_dir=tmp_path)
    shown = [rid for rid in result.context.allowed_record_ids if rid.startswith("resource:")]
    assert shown == resources
    assert result.trace["requested_resource_ids"] == resources
    for rid in resources:
        assert result.context.source_freshness[rid].verification_status == "verified"
        assert seen.count(RESOURCE_URLS[rid]) == 1
