"""Controlled program/course responses for bounded discovery; no public requests."""

import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from pydantic import ValidationError

from src.catalog import build_evidence, corpus_hash
from src.controller import run_advisor
from src.discovery import DiscoveryPlan, load_discovery_plans
from src.ingest import extract_program_courses
from src.models import Catalog, Completion, Record, StudentProfile
from src.providers import EmbeddingCache
from src.rules import evaluate_course
from src.sources import refresh_catalog
from test_sources import course_page

NOW = datetime(2026, 11, 4, 5, tzinfo=timezone.utc)
CS_ID = "7654324"
ECE_IDS = ["7654321", "7654322", "7654323"]


def encoded_page(primary, extras=(), edition="2026-2027"):
    table = []
    def ref(value):
        index = len(table)
        table.append(None)
        table[index] = ({k: ref(v) for k, v in value.items()} if isinstance(value, dict) else
                        [ref(v) for v in value] if isinstance(value, list) else value)
        return index
    ref(primary)
    for extra in extras:
        ref(extra)
    if edition:
        ref({"activeCatalog": "fixture", "catalogDisplayName": edition + " University of Arizona Catalog"})
    return '<script id="__NUXT_DATA__">' + json.dumps(table).replace("<", r"\u003c") + '</script>'


def program_page(plan, *, proofs=(), ids=None, edition="2026-2027", hidden=False, modify=None, extras=()):
    ids = ids if ids is not None else ([CS_ID] if plan.program_code == "COSCBS" else ["0432351", *ECE_IDS])
    rules = [{"id": "fixture-" + section, "name": "Fixture courses (" + section + ")",
        "value": {"condition": "courses", "values": [{"value": ids, "logic": "and"}], "subSelections": []}}
        for section in plan.section_ids]
    rules.extend({"id": "fixture-proof", "name": "Fixture proof (" + proof.section_id + ")",
        "description": proof.reviewed_text} for proof in proofs)
    primary = {"code": plan.program_code, "programGroupId": plan.program_code,
        "degreeDesignation": "Fixture BS", "longName": "Fixture program",
        "requisites": {"requisitesSimple": [{"showInCatalog": not hidden,
            "requirementLevel": "programRequirements", "rules": rules}]}}
    if modify:
        modify(primary, rules)
    return encoded_page(primary, extras, edition)


@pytest.fixture
def plans():
    return load_discovery_plans()


@pytest.fixture
def new_courses():
    return {identity: Record(record_id="fixture:" + code, kind="course", code=code,
        title="Fixture " + code, summary="Fixture programming and hardware course.", credits=3,
        source_ids=["fixture"], catalog_version="2026-2027", review_status="synthetic_fixture")
        for identity, code in zip([*ECE_IDS, CS_ID], ["ECE175", "ECE275", "ECE274A", "CSC110"])}


def client_for(catalog, plans, new_courses, *, programs=None, courses=None, seen=None, headers=None):
    known = {next(s.url.rsplit('/', 1)[-1] for s in catalog.sources if s.source_id == r.source_ids[0]): r
             for r in catalog.records if r.kind == "course"}
    known.update(new_courses)
    proofs = next(r for r in catalog.records if r.code == "CSC120").rule_evidence
    urls = {p.source.url: p for p in plans}

    def respond(request):
        url = str(request.url)
        if seen is not None:
            seen.append(url)
        if url in urls:
            plan = urls[url]
            body = (programs or {}).get(plan.program_code, program_page(plan,
                proofs=proofs if plan.program_code == "COSCBS" else ()))
        else:
            identity = url.rsplit('/', 1)[-1]
            body = (courses or {}).get(identity, course_page(known[identity], course_id=identity))
        if isinstance(body, int):
            return httpx.Response(body)
        return httpx.Response(200, text=body, headers={"Content-Type": "text/html", **(headers or {})})

    return httpx.Client(transport=httpx.MockTransport(respond))


def refresh(catalog, plans, client, tmp_path, profile=None, now=NOW):
    return refresh_catalog(catalog, profile or StudentProfile(), discovery_plans=plans,
                           client=client, cache_dir=tmp_path, now=now)


def discovered(result):
    return [r for r in result.catalog.records if r.discovery]


def test_extracts_only_explicit_ids_in_primary_visible_sections(plans):
    plan = plans[0]
    decoy = {"name": "Decoy (R1299/L30)", "value": {"condition": "courses", "values": ["0000000"]}}
    data = extract_program_courses(program_page(plan, extras=[decoy]), plan.program_code, plan.section_ids)
    assert data["course_ids"] == {"R1299/L30": [CS_ID]}
    assert data["catalog_version"] == "2026-2027"


@pytest.mark.parametrize("ids", [["https://unapproved.example/course"], [1234567], ["123"], [],
    [str(1000000 + i) for i in range(41)]])
def test_invalid_or_unbounded_id_lists_are_rejected(plans, ids):
    plan = plans[0]
    with pytest.raises(ValueError):
        extract_program_courses(program_page(plan, ids=ids), plan.program_code, plan.section_ids)


@pytest.mark.parametrize("case", ["wrong_program", "hidden", "duplicate", "free_text", "subselection", "wrong_level"])
def test_untrusted_or_unsupported_sections_are_not_used(plans, case):
    plan = plans[0]
    def modify(primary, rules):
        if case == "wrong_program": primary["code"] = "OTHERBS"
        elif case == "hidden": primary["requisites"]["requisitesSimple"][0]["showInCatalog"] = False
        elif case == "duplicate": rules.append(rules[0].copy())
        elif case == "free_text": rules[0]["value"]["condition"] = "freeText"
        elif case == "subselection": rules[0]["value"]["subSelections"] = [{"unsupported": True}]
        else: primary["requisites"]["requisitesSimple"][0]["requirementLevel"] = "other"
    with pytest.raises(ValueError):
        extract_program_courses(program_page(plan, modify=modify), plan.program_code, plan.section_ids)


def test_new_courses_keep_field_provenance_and_unknown_academic_rules(catalog, plans, new_courses, tmp_path):
    original = catalog.model_dump_json()
    seen = []
    with client_for(catalog, plans, new_courses, seen=seen) as client:
        result = refresh(catalog, plans, client, tmp_path)
    added = discovered(result)
    assert {r.code for r in added} == {"CSC110", "ECE175", "ECE275"}
    assert seen.count(plans[0].source.url) == 1  # Same page supplies rule and course-link evidence.
    assert len([url for url in seen if '/courses/' in url]) == 6
    assert seen.count('https://catalog.arizona.edu/courses/0432351') == 1
    for course in added:
        assert not course.rule_reviewed and evaluate_course(course, StudentProfile()).status == "unknown"
        assert course.field_sources == {field: course.source_ids[0]
            for field in ("title", "summary", "credits", "requirement_reference")}
        chunk = next(e for e in build_evidence(result.catalog) if e.record_id == course.record_id)
        assert chunk.source_ids == [course.source_ids[0]]
        assert course.discovery.source_id not in chunk.source_ids
    Catalog.model_validate(result.catalog.model_dump())
    assert catalog.model_dump_json() == original


def test_course_and_program_request_budgets_are_shared(catalog, plans, new_courses, tmp_path, monkeypatch):
    monkeypatch.setattr('src.sources.MAX_SOURCES', 4)
    seen = []
    with client_for(catalog, plans, new_courses, seen=seen) as client:
        result = refresh(catalog, plans, client, tmp_path)
    assert len([url for url in seen if '/courses/' in url]) == 4
    assert len([url for url in seen if '/programs/' in url]) == 2
    assert len(discovered(result)) == 1
    assert any('download budget' in issue for issue in result.issues)


def test_embedded_direction_uses_only_its_configured_program(catalog, plans, new_courses, tmp_path):
    seen = []
    with client_for(catalog, plans, new_courses, seen=seen) as client:
        result = refresh(catalog, plans, client, tmp_path, StudentProfile(career_id='embedded'))
    assert {r.code for r in discovered(result)} == {'ECE175', 'ECE275', 'ECE274A'}
    assert plans[0].source.url not in seen
    assert plans[1].source.url in seen


@pytest.mark.parametrize('bad', ['graduate', 'subject', 'edition', 'variable_units', 'broken_page', 'identity', 'missing_identity'])
def test_invalid_course_pages_never_create_placeholder_recommendations(catalog, plans, new_courses, tmp_path, bad):
    course = new_courses[CS_ID]
    options = ({'code': 'ECE525'} if bad == 'graduate' else {'code': 'MATH125'} if bad == 'subject'
               else {'edition': '2025-2026'} if bad == 'edition' else {'course_id': '1234567'} if bad == 'identity'
               else {'course_id': None} if bad == 'missing_identity' else {'variable_credits': True})
    options.setdefault('course_id', CS_ID)
    body = '<html>Unavailable fixture</html>' if bad == 'broken_page' else course_page(course, **options)
    with client_for(catalog, plans, new_courses, courses={CS_ID: body}) as client:
        result = refresh(catalog, plans[:1], client, tmp_path)
    assert not discovered(result)
    check = next(c for c in result.checks if c.url.endswith('/' + CS_ID))
    assert check.failure_kind == 'validation' and check.retrieved_at is None
    assert 'no placeholder' in check.message


def test_program_outage_does_not_promote_old_link_lists(catalog, plans, new_courses, tmp_path):
    with client_for(catalog, plans, new_courses) as client:
        refresh(catalog, plans, client, tmp_path)
    with client_for(catalog, plans, new_courses, programs={'COSCBS': 503, 'ECEBSECE': 503}) as client:
        result = refresh(catalog, plans, client, tmp_path, now=NOW + timedelta(days=1))
    assert not discovered(result)
    assert all(c.discovery_status == 'stale' for c in result.checks if c.kind in {'rule', 'discovery'})


def test_missing_discovery_section_cannot_revoke_valid_prerequisite_evidence(catalog, plans, new_courses, tmp_path):
    proofs = next(r for r in catalog.records if r.code == 'CSC120').rule_evidence
    page = program_page(plans[0], proofs=proofs, modify=lambda primary, rules: rules.pop(0))
    with client_for(catalog, plans, new_courses, programs={'COSCBS': page}) as client:
        result = refresh(catalog, plans[:1], client, tmp_path)
    course = next(r for r in result.catalog.records if r.code == 'CSC120')
    profile = StudentProfile(completed=[Completion(course_code='ECE101', grade='B')])
    assert evaluate_course(course, profile).status == 'satisfied'
    check = next(c for c in result.checks if c.kind == 'rule')
    assert check.rule_status == 'verified' and check.discovery_status == 'unavailable'
    assert not discovered(result)


def test_failed_course_fetch_uses_only_a_valid_dated_cache(catalog, plans, new_courses, tmp_path):
    with client_for(catalog, plans, new_courses) as client:
        first = refresh(catalog, plans[:1], client, tmp_path)
    with client_for(catalog, plans, new_courses, courses={CS_ID: 503}) as client:
        second = refresh(catalog, plans[:1], client, tmp_path, now=NOW + timedelta(days=1))
    course = discovered(second)[0]
    source = next(s for s in second.catalog.sources if s.source_id == course.source_ids[0])
    assert source.verification_status == 'stale' and source.last_checked_at == NOW
    assert evaluate_course(course, StudentProfile()).status == 'unknown'
    assert corpus_hash(first.catalog) == corpus_hash(second.catalog)


def test_conditional_program_and_course_checks_reuse_vectors(catalog, plans, new_courses, tmp_path, fake_provider):
    with client_for(catalog, plans, new_courses, headers={'ETag': '"fixture"'}) as client:
        first = refresh(catalog, plans, client, tmp_path / 'sources')
    cache = EmbeddingCache(tmp_path / 'vectors')
    cache.get(first.catalog, build_evidence(first.catalog), fake_provider)
    calls = fake_provider.document_calls
    def not_modified(request):
        assert request.headers['if-none-match'] == '"fixture"'
        return httpx.Response(304)
    with httpx.Client(transport=httpx.MockTransport(not_modified)) as client:
        second = refresh(catalog, plans, client, tmp_path / 'sources', now=NOW + timedelta(hours=1))
    cache.get(second.catalog, build_evidence(second.catalog), fake_provider)
    assert fake_provider.document_calls == calls
    assert all(c.status == 'not_modified' for c in second.checks)
    assert {r.code for r in discovered(second)} == {'CSC110', 'ECE175', 'ECE275'}


def test_duplicate_course_identity_does_not_overwrite_configured_record(catalog, plans, new_courses, tmp_path):
    original = next(r for r in catalog.records if r.code == 'ECE101')
    with client_for(catalog, plans, new_courses, courses={CS_ID: course_page(original, course_id=CS_ID)}) as client:
        result = refresh(catalog, plans[:1], client, tmp_path)
    assert len([r for r in result.catalog.records if r.code == 'ECE101']) == 1
    assert not discovered(result)
    assert any(c.status == 'skipped' and 'duplicates' in c.message for c in result.checks)


def test_controller_generates_from_discovered_course_and_field_sources(catalog, plans, new_courses, tmp_path, fake_provider):
    fake_provider.close = lambda: None
    seen = []
    with client_for(catalog, plans, new_courses, seen=seen) as client:
        def refresher(catalog, profile, **kwargs):
            return refresh_catalog(catalog, profile, discovery_plans=plans, client=client, now=NOW, **kwargs)
        result = run_advisor(catalog, StudentProfile(career_id='embedded', question='ECE274A'),
            use_ai=True, api_key='fixture', provider_factory=lambda *a, **k: fake_provider,
            source_refresher=refresher, source_cache_dir=tmp_path / 'sources', cache_dir=tmp_path / 'vectors')
    assert seen and not result.coverage_notice
    assert result.generation_complete
    rid = 'uofa:ECE274A:2026-2027'
    assert rid in result.context.allowed_record_ids
    assert fake_provider.context.field_sources[rid]['summary'] == 'catalog:ECE274A'
    assert result.context.rule_results[rid].status == 'unknown'
    assert rid in result.trace['source_refresh']['discovered_courses']


def test_unresolved_requested_course_still_gets_a_coverage_notice(catalog, plans, new_courses, tmp_path):
    with client_for(catalog, plans, new_courses) as client:
        def refresher(catalog, profile, **kwargs):
            return refresh_catalog(catalog, profile, discovery_plans=plans, client=client, now=NOW, **kwargs)
        result = run_advisor(catalog, StudentProfile(question='ECE499'), source_refresher=refresher,
            source_cache_dir=tmp_path)
    assert result.coverage_notice and not result.context.allowed_record_ids


def test_unsupported_catalog_makes_no_discovery_requests(catalog, plans, new_courses, tmp_path):
    seen = []
    with client_for(catalog, plans, new_courses, seen=seen) as client:
        result = refresh(catalog, plans, client, tmp_path, StudentProfile(catalog_version='2025-2026'))
    assert not seen and not discovered(result)


@pytest.mark.parametrize('field,value', [('url', 'https://unapproved.example/program'), ('catalog_version', None)])
def test_discovery_configuration_rejects_unbound_sources(plans, field, value):
    data = plans[0].model_dump()
    data['source'][field] = value
    with pytest.raises(ValidationError):
        DiscoveryPlan.model_validate(data)


def test_catalog_rejects_dangling_field_provenance(catalog):
    data = catalog.model_dump()
    data['records'][0]['field_sources'] = {'summary': 'unknown:source'}
    with pytest.raises(ValidationError, match='provenance'):
        Catalog.model_validate(data)


def test_program_budget_preserves_rule_job_and_skips_extra_discovery(catalog, plans, new_courses, tmp_path, monkeypatch):
    monkeypatch.setattr('src.discovery.MAX_RULE_SOURCES', 1)
    seen = []
    with client_for(catalog, plans, new_courses, seen=seen) as client:
        result = refresh(catalog, plans, client, tmp_path)
    assert plans[1].source.url not in seen
    assert {r.code for r in discovered(result)} == {'CSC110'}
    assert any(c.kind == 'discovery' and c.status == 'skipped' for c in result.checks)


def test_duplicate_ids_across_sections_share_one_download_and_keep_both_locators(catalog, plans, new_courses, tmp_path):
    plan = plans[0].model_copy(update={'section_ids': ['R1299/L30', 'R1299/L31']})
    proofs = next(r for r in catalog.records if r.code == 'CSC120').rule_evidence
    page = program_page(plan, proofs=proofs, ids=[CS_ID, CS_ID])
    seen = []
    with client_for(catalog, [plan], new_courses, programs={'COSCBS': page}, seen=seen) as client:
        result = refresh(catalog, [plan], client, tmp_path)
    assert seen.count('https://catalog.arizona.edu/courses/' + CS_ID) == 1
    assert discovered(result)[0].discovery.section_ids == ['R1299/L30', 'R1299/L31']


def test_unwritable_course_cache_keeps_fresh_discovered_records(catalog, plans, new_courses, tmp_path, monkeypatch):
    def fail(*args):
        raise OSError('Controlled read-only fixture')
    monkeypatch.setattr('src.sources._save_cache', fail)
    with client_for(catalog, plans, new_courses) as client:
        result = refresh(catalog, plans, client, tmp_path)
    assert len(discovered(result)) == 3
    assert all(s.verification_status == 'verified' for s in result.catalog.sources
               if s.source_id in {r.source_ids[0] for r in discovered(result)})
    assert all(not c.cache_saved for c in result.checks if c.kind == 'course')


@pytest.mark.parametrize('corruption', ['program_schema', 'course_subject'])
def test_incompatible_caches_cannot_create_courses_during_outage(catalog, plans, new_courses, tmp_path, corruption):
    from src.sources import CourseSnapshot, snapshot_hash
    with client_for(catalog, plans, new_courses) as client:
        refresh(catalog, plans[:1], client, tmp_path)
    if corruption == 'program_schema':
        path = next((tmp_path / 'rules').glob('*.json'))
        data = json.loads(path.read_text())
        data['schema_version'] = 1
        path.write_text(json.dumps(data))
        programs, courses = {'COSCBS': 503}, {}
    else:
        path = next(p for p in tmp_path.glob('*.json') if json.loads(p.read_text())['url'].endswith('/' + CS_ID))
        data = json.loads(path.read_text())
        data['data']['code'] = 'ECE525'
        data['content_hash'] = snapshot_hash(CourseSnapshot.model_validate(data['data']))
        path.write_text(json.dumps(data))
        programs, courses = {}, {CS_ID: 503}
    with client_for(catalog, plans, new_courses, programs=programs, courses=courses) as client:
        result = refresh(catalog, plans[:1], client, tmp_path)
    assert not discovered(result)


def test_known_course_also_rejects_a_conflicting_internal_identity(catalog, plans, new_courses, tmp_path):
    course = next(r for r in catalog.records if r.code == 'ECE101')
    bad = course_page(course, course_id='1234567')
    with client_for(catalog, plans, new_courses, courses={'0432351': bad}) as client:
        result = refresh(catalog, plans, client, tmp_path)
    check = next(c for c in result.checks if c.code == 'ECE101')
    assert check.status == 'bundled_fallback' and check.failure_kind == 'validation'
    assert next(r for r in result.catalog.records if r.code == 'ECE101').title == course.title
