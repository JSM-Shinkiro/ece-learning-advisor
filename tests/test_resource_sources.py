"""Controlled resource pages and HTTP responses; no public network requests."""

import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from src.catalog import build_evidence, corpus_hash
from src.controller import run_advisor
from src.models import Catalog, Completion, StudentProfile
from src.providers import EmbeddingCache
from src.resource_sources import RESOURCE_URLS, extract_resource
from src.rules import evaluate_course
from src.sources import refresh_catalog

NOW = datetime(2026, 11, 4, 5, 30, tzinfo=timezone.utc)
INTRO = "Fixture introduction describes programming practice and a short machine learning workflow."
BASELINE_RESOURCES = ["resource:pytorch", "resource:cs50"]


def resource_page(resource_id, *, intro=INTRO, version=None, document_title=None, heading=None,
                  root=True, canonical=None, navigation="Fixture navigation", suffix="", hidden=""):
    pytorch = resource_id == 'resource:pytorch'
    version = version or ('2.99.0+fixture' if pytorch else '2026')
    title = document_title or ('Quickstart — PyTorch Tutorials ' + version + ' documentation' if pytorch else 'CS50x ' + version)
    identity = '' if pytorch else '<aside><header><h2>CS50’s Introduction to Computer Science</h2></header></aside>'
    start, end = ('<main><article class="bd-article">', '</article></main>') if pytorch else ('<main>', '</main>')
    if not root:
        start, end = '<div>', '</div>'
    canonical = RESOURCE_URLS[resource_id] if canonical is None else canonical
    return (f'<html><head><title>{title}</title><link rel="canonical" href="{canonical}"></head>'
        f'<body><nav><p>{navigation}</p></nav>{identity}{start}<p>Unselected preface outside the introduction.</p>'
        f'<h1>{heading or ("Quickstart" if pytorch else "Welcome")}</h1>'
        '<p>Created On: fixture metadata that is not part of the excerpt.</p>'
        '<script>untrusted script instructions</script><pre>unselected code sample</pre>'
        f'{hidden}<p>{intro}</p><h2>Another section</h2><p>Unselected later material.</p>{end}'
        f'<footer>{suffix}</footer></body></html>')


@pytest.fixture
def resource_catalog(catalog):
    records = [r.model_copy(deep=True) for r in catalog.records if r.kind == 'resource']
    ids = {sid for r in records for sid in r.source_ids}
    return Catalog(version=catalog.version, catalog_version=catalog.catalog_version, records=records,
                   sources=[s.model_copy(deep=True) for s in catalog.sources if s.source_id in ids])


def client_for(*, responses=None, seen=None, headers=None):
    urls = {url: rid for rid, url in RESOURCE_URLS.items()}
    def respond(request):
        url = str(request.url)
        if seen is not None:
            seen.append(url)
        rid = urls[url]
        response = (responses or {}).get(rid, resource_page(rid))
        if isinstance(response, int):
            return httpx.Response(response)
        return httpx.Response(200, text=response, headers={'Content-Type': 'text/html', **(headers or {})})
    return httpx.Client(transport=httpx.MockTransport(respond))


def refresh(catalog, client, tmp_path, profile=None, now=NOW):
    return refresh_catalog(catalog, profile or StudentProfile(), client=client, cache_dir=tmp_path,
                           resource_checks=True, now=now)


@pytest.mark.parametrize('rid', BASELINE_RESOURCES)
def test_resource_intro_has_independent_identity_and_version(rid):
    data = extract_resource(resource_page(rid), rid, RESOURCE_URLS[rid])
    assert data.summary == INTRO
    assert data.resource_version == ('2026' if rid == 'resource:cs50' else '2.99.0+fixture')
    assert 'unselected' not in data.summary.lower() and 'script' not in data.summary


@pytest.mark.parametrize('bad', ['document_title', 'heading', 'root', 'canonical', 'empty_intro', 'duplicate_root'])
@pytest.mark.parametrize('rid', BASELINE_RESOURCES)
def test_wrong_identity_or_unsupported_layout_is_rejected(rid, bad):
    options = {'document_title': 'A different resource'} if bad == 'document_title' else (
        {'heading': 'Different resource'} if bad == 'heading' else {'root': False} if bad == 'root'
        else {'canonical': 'https://unapproved.example/page'} if bad == 'canonical'
        else {'intro': ''} if bad == 'empty_intro' else {})
    page = resource_page(rid, **options)
    if bad == 'duplicate_root':
        page += '<article class="bd-article"></article>' if rid == 'resource:pytorch' else '<main></main>'
    with pytest.raises(ValueError):
        extract_resource(page, rid, RESOURCE_URLS[rid])


def test_hidden_blocks_cannot_supply_the_excerpt():
    rid = 'resource:pytorch'
    hidden = ('<div hidden><p>Hidden fixture paragraph should not be included in evidence.</p></div>'
        '<div aria-hidden="true"><p>Another hidden fixture paragraph with enough words.</p></div>'
        '<div class="admonition"><p>A fixture notice should not become introductory evidence.</p></div>')
    data = extract_resource(resource_page(rid, hidden=hidden), rid, RESOURCE_URLS[rid])
    assert data.summary == INTRO


def test_inline_markup_and_line_breaks_preserve_excerpt_words():
    rid = 'resource:pytorch'
    intro = 'Fixture introduction preserves <strong>formatted words</strong><br>and inline <code>API names</code> in readable source evidence.'
    data = extract_resource(resource_page(rid, intro=intro), rid, RESOURCE_URLS[rid])
    assert data.summary == 'Fixture introduction preserves formatted words and inline API names in readable source evidence.'


def test_fetched_resource_fields_have_provenance_without_mutating_bundle(resource_catalog, tmp_path):
    original = resource_catalog.model_dump_json()
    with client_for() as client:
        result = refresh(resource_catalog, client, tmp_path)
    assert len(result.checks) == 2 and all(c.kind == 'resource' for c in result.checks)
    for record in result.catalog.records:
        assert record.summary == INTRO and record.review_status == 'source_fetched'
        assert record.resource_version and record.catalog_version is None and record.credits is None
        assert record.field_sources == {key: record.record_id for key in ('title', 'summary', 'resource_version')}
        source = next(s for s in result.catalog.sources if s.source_id == record.record_id)
        assert source.verification_status == 'verified' and source.last_checked_at == NOW
        chunk = next(e for e in build_evidence(result.catalog) if e.record_id == record.record_id)
        assert record.resource_version in chunk.text and 'university credit' in chunk.text
    Catalog.model_validate(result.catalog.model_dump())
    assert resource_catalog.model_dump_json() == original


def test_resource_checks_are_direction_scoped(resource_catalog, tmp_path):
    seen = []
    with client_for(seen=seen) as client:
        result = refresh(resource_catalog, client, tmp_path, StudentProfile(career_id='embedded'))
    assert seen == [RESOURCE_URLS['resource:cs50']]
    assert next(s for s in result.catalog.sources if s.source_id == 'resource:pytorch').verification_status == 'snapshot'


def test_resources_can_refresh_for_an_unsupported_academic_edition(resource_catalog, tmp_path):
    with client_for() as client:
        result = refresh(resource_catalog, client, tmp_path, StudentProfile(catalog_version='2025-2026'))
    assert all(c.kind == 'resource' and c.status == 'updated' for c in result.checks)
    assert all(r.resource_version for r in result.catalog.records)


@pytest.mark.parametrize('status', [404, 429, 503, 302])
def test_failed_resources_retain_dated_bundle_without_approval(resource_catalog, tmp_path, status):
    with client_for(responses={rid: status for rid in RESOURCE_URLS}) as client:
        result = refresh(resource_catalog, client, tmp_path)
    assert all(c.status == 'bundled_fallback' for c in result.checks)
    assert all(s.verification_status == 'stale' and s.last_checked_at is None for s in result.catalog.sources)
    assert all(r.resource_version is None and r.summary != INTRO for r in result.catalog.records)
    assert result.issues


def test_outage_uses_valid_cache_without_advancing_successful_check(resource_catalog, tmp_path):
    with client_for() as client:
        first = refresh(resource_catalog, client, tmp_path)
    with client_for(responses={rid: 503 for rid in RESOURCE_URLS}) as client:
        second = refresh(resource_catalog, client, tmp_path, now=NOW + timedelta(days=1))
    assert all(c.status == 'stale_cache' and c.last_checked_at == NOW for c in second.checks)
    assert all(s.verification_status == 'stale' and s.last_checked_at == NOW for s in second.catalog.sources)
    assert all(r.summary == INTRO for r in second.catalog.records)
    assert corpus_hash(first.catalog) == corpus_hash(second.catalog)


@pytest.mark.parametrize('corruption', ['json', 'hash', 'url', 'time', 'schema', 'oversized', 'version'])
def test_invalid_caches_cannot_replace_bundled_resources_during_outage(resource_catalog, tmp_path, corruption):
    with client_for() as client:
        refresh(resource_catalog, client, tmp_path)
    paths = list((tmp_path / 'resources').glob('*.json'))
    for path in paths:
        data = json.loads(path.read_text())
        if corruption == 'json':
            path.write_text('invalid JSON')
            continue
        if corruption == 'hash': data['data']['summary'] = 'Forged fixture content that does not match the saved fingerprint.'
        elif corruption == 'url': data['requested_url'] = 'https://unapproved.example/page'
        elif corruption == 'time': data['last_checked_at'] = '2026-01-01T00:00:00Z'
        elif corruption == 'schema': data['schema_version'] = 99
        elif corruption == 'version': data['data']['resource_version'] = 'unsupported'
        path.write_text((' ' * 31000 if corruption == 'oversized' else '') + json.dumps(data))
    with client_for(responses={rid: 503 for rid in RESOURCE_URLS}) as client:
        result = refresh(resource_catalog, client, tmp_path)
    assert all(c.status == 'bundled_fallback' for c in result.checks)
    assert all(r.resource_version is None for r in result.catalog.records)


def test_conditional_recheck_reuses_resource_vectors(resource_catalog, tmp_path, fake_provider):
    with client_for(headers={'ETag': '"fixture"', 'Last-Modified': 'Tue, 03 Nov 2026 20:00:00 GMT'}) as client:
        first = refresh(resource_catalog, client, tmp_path / 'sources')
    cache = EmbeddingCache(tmp_path / 'vectors')
    cache.get(first.catalog, build_evidence(first.catalog), fake_provider)
    calls = fake_provider.document_calls
    def not_modified(request):
        assert request.headers['if-none-match'] == '"fixture"'
        assert 'if-modified-since' in request.headers
        return httpx.Response(304)
    with httpx.Client(transport=httpx.MockTransport(not_modified)) as client:
        second = refresh(resource_catalog, client, tmp_path / 'sources', now=NOW + timedelta(hours=1))
    cache.get(second.catalog, build_evidence(second.catalog), fake_provider)
    assert fake_provider.document_calls == calls
    assert all(c.status == 'not_modified' and c.retrieved_at == NOW for c in second.checks)
    assert all(c.last_checked_at > c.retrieved_at for c in second.checks)


def test_not_modified_without_cache_cannot_verify_a_resource(resource_catalog, tmp_path):
    with client_for(responses={rid: 304 for rid in RESOURCE_URLS}) as client:
        result = refresh(resource_catalog, client, tmp_path)
    assert all(c.status == 'bundled_fallback' for c in result.checks)
    assert all(s.verification_status == 'stale' for s in result.catalog.sources)


def test_changed_excerpt_reembeds_only_its_resource(resource_catalog, tmp_path, fake_provider):
    with client_for() as client:
        first = refresh(resource_catalog, client, tmp_path / 'sources')
    cache = EmbeddingCache(tmp_path / 'vectors')
    cache.get(first.catalog, build_evidence(first.catalog), fake_provider)
    calls = fake_provider.document_calls
    changed = resource_page('resource:pytorch', intro='Changed fixture introduction explains a different programming and model evaluation workflow.')
    with client_for(responses={'resource:pytorch': changed}) as client:
        second = refresh(resource_catalog, client, tmp_path / 'sources')
    cache.get(second.catalog, build_evidence(second.catalog), fake_provider)
    assert fake_provider.document_calls == calls + 1
    assert corpus_hash(first.catalog) != corpus_hash(second.catalog)


def test_navigation_and_footer_changes_do_not_change_embedding_identity(resource_catalog, tmp_path):
    with client_for() as client:
        first = refresh(resource_catalog, client, tmp_path)
    with client_for(responses={rid: resource_page(rid, navigation='Changed fixture navigation', suffix='New footer')
                               for rid in RESOURCE_URLS}) as client:
        second = refresh(resource_catalog, client, tmp_path, now=NOW + timedelta(hours=1))
    assert corpus_hash(first.catalog) == corpus_hash(second.catalog)
    assert all(c.status == 'unchanged' for c in second.checks)


@pytest.mark.parametrize('location', ['https://unapproved.example/page', 'https://cs50.harvard.edu/python/2026/',
    'https://user@cs50.harvard.edu/x/2026/', 'http://cs50.harvard.edu/x/2026/',
    '/x/2026/?token=fixture', '/x/2026/#section'])
def test_unsafe_or_unrelated_redirects_are_not_followed(resource_catalog, tmp_path, location):
    seen = []
    def respond(request):
        url = str(request.url); seen.append(url)
        if url == RESOURCE_URLS['resource:cs50']:
            return httpx.Response(302, headers={'Location': location})
        assert url == RESOURCE_URLS['resource:pytorch']
        return httpx.Response(200, text=resource_page('resource:pytorch'), headers={'Content-Type': 'text/html'})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = refresh(resource_catalog, client, tmp_path)
    assert len(seen) == 2
    assert next(c for c in result.checks if c.code == 'resource:cs50').status == 'bundled_fallback'


def test_one_valid_cs50_redirect_is_pinned_to_its_edition(resource_catalog, tmp_path):
    target = 'https://cs50.harvard.edu/x/2026/'
    seen = []
    def respond(request):
        url = str(request.url); seen.append(url)
        if url == RESOURCE_URLS['resource:cs50']:
            return httpx.Response(301, headers={'Location': '/x/2026/'})
        rid = 'resource:cs50' if url == target else 'resource:pytorch'
        return httpx.Response(200, text=resource_page(rid, canonical=target if rid.endswith('cs50') else None),
                              headers={'Content-Type': 'text/html'})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = refresh(resource_catalog, client, tmp_path)
    source = next(s for s in result.catalog.sources if s.source_id == 'resource:cs50')
    assert len(seen) == 3 and source.url == target
    assert next(c for c in result.checks if c.code == 'resource:cs50').resolved_url == target


def test_new_cs50_redirect_edition_does_not_reuse_old_validators(resource_catalog, tmp_path):
    year = '2026'
    def respond(request):
        url = str(request.url)
        if url == RESOURCE_URLS['resource:cs50']:
            return httpx.Response(302, headers={'Location': '/x/' + year + '/'})
        rid = 'resource:pytorch' if url == RESOURCE_URLS['resource:pytorch'] else 'resource:cs50'
        if rid.endswith('cs50') and year == '2027':
            assert 'if-none-match' not in request.headers
        return httpx.Response(200, text=resource_page(rid, version=year if rid.endswith('cs50') else None,
            canonical=url), headers={'Content-Type': 'text/html', 'ETag': '"fixture"'})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        first = refresh(resource_catalog, client, tmp_path)
        year = '2027'
        second = refresh(resource_catalog, client, tmp_path, now=NOW + timedelta(days=1))
    assert next(r for r in second.catalog.records if r.record_id == 'resource:cs50').resource_version == '2027'
    assert corpus_hash(first.catalog) != corpus_hash(second.catalog)


def test_redirect_chain_stops_after_one_hop(resource_catalog, tmp_path):
    seen = []
    def respond(request):
        url = str(request.url); seen.append(url)
        if 'cs50.harvard.edu' in url:
            return httpx.Response(302, headers={'Location': '/x/2026/'})
        return httpx.Response(200, text=resource_page('resource:pytorch'), headers={'Content-Type': 'text/html'})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = refresh(resource_catalog, client, tmp_path)
    assert len(seen) == 3
    assert next(c for c in result.checks if c.code == 'resource:cs50').status == 'bundled_fallback'


def test_unwritable_cache_keeps_fresh_resource_fields(resource_catalog, tmp_path, monkeypatch):
    def fail(*args): raise OSError('Controlled fixture cache-write failure')
    monkeypatch.setattr('src.resource_sources._write', fail)
    with client_for() as client:
        result = refresh(resource_catalog, client, tmp_path)
    assert all(c.status == 'updated' and not c.cache_saved for c in result.checks)
    assert all(s.verification_status == 'verified' for s in result.catalog.sources)
    assert all(r.summary == INTRO for r in result.catalog.records)


def test_resource_budget_is_independent_and_bounded(resource_catalog, tmp_path, monkeypatch):
    monkeypatch.setattr('src.resource_sources.MAX_RESOURCE_SOURCES', 1)
    seen = []
    with client_for(seen=seen) as client:
        result = refresh(resource_catalog, client, tmp_path)
    assert len(seen) == 1
    assert any(c.kind == 'resource' and c.status == 'skipped' for c in result.checks)


def test_unconfigured_resource_url_is_not_fetched(resource_catalog, tmp_path):
    source = next(s for s in resource_catalog.sources if s.source_id == 'resource:cs50')
    source.url = 'https://unapproved.example/page'
    seen = []
    with client_for(seen=seen) as client:
        result = refresh(resource_catalog, client, tmp_path)
    assert seen == [RESOURCE_URLS['resource:pytorch']]
    assert any(c.code == 'resource:cs50' and c.status == 'skipped' for c in result.checks)


def test_resource_updates_reach_controlled_generator(resource_catalog, tmp_path, fake_provider):
    fake_provider.close = lambda: None
    with client_for() as client:
        def refresher(catalog, profile, **kwargs):
            return refresh_catalog(catalog, profile, resource_checks=True, client=client, now=NOW, **kwargs)
        result = run_advisor(resource_catalog, StudentProfile(question='PyTorch programming'), source_refresher=refresher,
            use_ai=True, api_key='fixture', provider_factory=lambda *a, **k: fake_provider,
            source_cache_dir=tmp_path / 'sources', cache_dir=tmp_path / 'vectors')
    assert result.generation_complete
    assert fake_provider.context.field_sources['resource:pytorch']['summary'] == 'resource:pytorch'
    assert any(INTRO in e.text and '2.99.0+fixture' in e.text for e in fake_provider.context.evidence)
    assert fake_provider.context.source_freshness['resource:pytorch'].verification_status == 'verified'
    assert result.trace['resource_versions']['resource:cs50'] == '2026'


def test_whole_refresher_failure_marks_previously_verified_resources_stale(resource_catalog, tmp_path):
    with client_for() as client:
        active = refresh(resource_catalog, client, tmp_path).catalog
    def fail(*args, **kwargs): raise OSError('Controlled fixture failure')
    result = run_advisor(active, StudentProfile(question='PyTorch programming'), source_refresher=fail)
    assert all(s.verification_status == 'stale' for s in result.catalog.sources)
    assert result.issues and not result.generation_complete


def test_offline_use_labels_previously_fetched_resources_as_saved(resource_catalog, tmp_path):
    with client_for() as client:
        active = refresh(resource_catalog, client, tmp_path).catalog
    def forbidden(*args, **kwargs): raise AssertionError('No offline source requests are allowed')
    result = run_advisor(active, StudentProfile(question='PyTorch programming'), source_refresher=forbidden,
                         refresh_sources=False)
    assert all(s.verification_status == 'snapshot' for s in result.catalog.sources)
    assert all(s.verification_status == 'verified' for s in active.sources)
    assert not result.trace['source_refresh']['enabled']
    assert all(r.resource_version for r in result.catalog.records)


def test_resource_outage_cannot_override_verified_academic_condition(catalog, tmp_path):
    from test_rule_sources import program_page
    from test_sources import course_page
    course = next(r for r in catalog.records if r.code == 'CSC120')
    pages = {next(s.url for s in catalog.sources if s.source_id == r.source_ids[0]):
             course_page(r, course_id=next(s.url for s in catalog.sources if s.source_id == r.source_ids[0]).rsplit('/', 1)[-1])
             for r in catalog.records if r.kind == 'course'}
    def respond(request):
        url = str(request.url)
        if url in RESOURCE_URLS.values(): return httpx.Response(503)
        return httpx.Response(200, text=pages.get(url, program_page(course)), headers={'Content-Type': 'text/html'})
    profile = StudentProfile(completed=[Completion(course_code='ECE101', grade='B')])
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = refresh(catalog, client, tmp_path, profile)
    checked = next(r for r in result.catalog.records if r.code == 'CSC120')
    assert evaluate_course(checked, profile).status == 'satisfied'
    assert all(c.status == 'bundled_fallback' for c in result.checks if c.kind == 'resource')
