"""Controlled prerequisite-source pages; never used by the running app."""

import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from pydantic import ValidationError

from src.catalog import build_evidence, corpus_hash
from src.controller import run_advisor
from src.ingest import extract_program_statements
from src.models import Catalog, Completion, StudentProfile, statement_hash
from src.providers import EmbeddingCache
from src.rule_sources import ProgramSnapshot, program_hash
from src.rules import evaluate_course
from src.service import build_context
from src.sources import refresh_catalog
from test_sources import course_page

NOW = datetime(2026, 11, 4, 4, tzinfo=timezone.utc)


@pytest.fixture
def rule_catalog(catalog):
    course = next(r for r in catalog.records if r.code == "CSC120")
    return Catalog(version=catalog.version, catalog_version=catalog.catalog_version,
                   records=[course.model_copy(deep=True)],
                   sources=[s.model_copy(deep=True) for s in catalog.sources if s.source_id in course.source_ids])


def program_page(course, *, program_code="COSCBS", edition="2026-2027", text=None,
                 missing=False, conflicting=False, extra_texts=None):
    from test_discovery import encoded_page
    nodes = []
    if not missing:
        for proof in course.rule_evidence:
            if proof.program_code != program_code:
                continue
            words = (extra_texts or {}).get(proof.section_id, text or proof.reviewed_text)
            nodes.append({"id": "fixture-" + proof.section_id,
                          "name": "Fixture condition (" + proof.section_id + ")",
                          "description": words})
            if conflicting:
                nodes.append({"id": "conflict", "name": "Conflict (" + proof.section_id + ")",
                              "description": "Different fixture prerequisite statement."})
    primary = {"code": program_code, "programGroupId": program_code,
               "degreeDesignation": "Fixture BS", "longName": "Fixture program",
               "requisites": {"requisitesSimple": [{"showInCatalog": True,
                   "requirementLevel": "programRequirements", "rules": nodes}]}}
    return encoded_page(primary, edition=edition)


def http_fixture(catalog, *, program=None, program_status=200, course_status=200, headers=None, seen=None):
    course = catalog.records[0]
    sources = {s.source_id: s for s in catalog.sources}
    primary_url = next(s.url for s in catalog.sources if "/courses/" in s.url)

    def handle(request):
        if seen is not None:
            seen.append(str(request.url))
        if str(request.url) == primary_url:
            if course_status != 200:
                return httpx.Response(course_status)
            return httpx.Response(200, text=course_page(course), headers={"Content-Type": "text/html", **(headers or {})})
        source = next(s for s in sources.values() if s.url == str(request.url))
        proof = next(p for p in course.rule_evidence if p.source_id == source.source_id)
        status = program_status.get(proof.program_code, 200) if isinstance(program_status, dict) else program_status
        if status != 200:
            return httpx.Response(status)
        page = program if program is not None else program_page(course, program_code=proof.program_code)
        return httpx.Response(200, text=page, headers={"Content-Type": "text/html", **(headers or {})})

    return httpx.Client(transport=httpx.MockTransport(handle))


def check(catalog, client, directory, now=NOW, profile=None):
    return refresh_catalog(catalog, profile or StudentProfile(), client=client, cache_dir=directory, now=now)


def grade_profile(code="ECE101", grade="B"):
    return StudentProfile(completed=[Completion(course_code=code, grade=grade)])


def test_program_identity_edition_and_exact_section_are_extracted(rule_catalog):
    course = rule_catalog.records[0]
    result = extract_program_statements(program_page(course), "COSCBS", ["R1299/L40"])
    assert result["program_code"] == "COSCBS" and result["catalog_version"] == "2026-2027"
    assert result["statements"]["R1299/L40"] == course.rule_evidence[0].reviewed_text


@pytest.mark.parametrize("options", [{"program_code": "OTHERBS"}, {"missing": True}, {"conflicting": True}])
def test_wrong_program_or_ambiguous_section_is_not_accepted(rule_catalog, options):
    with pytest.raises(ValueError):
        extract_program_statements(program_page(rule_catalog.records[0], **options), "COSCBS", ["R1299/L40"])


@pytest.mark.parametrize("edition", [None, "2025-2026"])
def test_missing_or_wrong_edition_keeps_rule_unknown(rule_catalog, tmp_path, edition):
    with http_fixture(rule_catalog, program=program_page(rule_catalog.records[0], edition=edition)) as client:
        result = check(rule_catalog, client, tmp_path)
    assert result.catalog.records[0].rule_verification == "unavailable"
    assert evaluate_course(result.catalog.records[0], grade_profile()).status == "unknown"


@pytest.mark.parametrize("code,grade,status", [("ECE101", "B", "satisfied"), ("CSC110", "C", "satisfied"),
    ("ECE175", "C", "satisfied"), ("ISTA130", "C", "satisfied"),
    ("ECE101", "D", "unknown"), ("ECE101", None, "unknown")])
def test_verified_condition_uses_reviewed_alternatives_and_grades(rule_catalog, tmp_path, code, grade, status):
    with http_fixture(rule_catalog) as client:
        result = check(rule_catalog, client, tmp_path)
    course = result.catalog.records[0]
    evaluated = evaluate_course(course, grade_profile(code, grade))
    assert evaluated.status == status
    assert evaluated.verification_status == "verified"
    assert evaluated.evidence_ids == [course.rule_evidence[0].evidence_id]
    assert evaluated.source_ids == ["catalog:CS_foundations"]


def test_known_failed_alternative_with_complete_history_is_unsatisfied(rule_catalog, tmp_path):
    profile = grade_profile(grade="D").model_copy(update={"history_complete": True})
    with http_fixture(rule_catalog) as client:
        result = check(rule_catalog, client, tmp_path, profile=profile)
    assert evaluate_course(result.catalog.records[0], profile).status == "unsatisfied"


def test_changed_statement_never_rewrites_the_reviewed_interpretation(rule_catalog, tmp_path):
    original = rule_catalog.model_dump_json()
    original_rule = rule_catalog.records[0].rule.model_dump_json()
    page = program_page(rule_catalog.records[0], text="A changed fixture condition requires additional approval.")
    with http_fixture(rule_catalog, program=page) as client:
        result = check(rule_catalog, client, tmp_path)
    course = result.catalog.records[0]
    assert course.rule_verification == "changed"
    assert course.rule.model_dump_json() == original_rule
    assert evaluate_course(course, grade_profile()).status == "unknown"
    assert course.rule_evidence[0].observed_text.startswith("A changed fixture")
    assert result.catalog.sources[-1].verification_status == "verified"
    assert next(c for c in result.checks if c.kind == "rule").rule_status == "changed"
    assert rule_catalog.model_dump_json() == original


@pytest.mark.parametrize("status", [404, 429, 503, 302])
def test_missing_rule_source_does_not_approve_from_the_bundled_snapshot(rule_catalog, tmp_path, status):
    with http_fixture(rule_catalog, program_status=status) as client:
        result = check(rule_catalog, client, tmp_path)
    assert result.catalog.records[0].rule_verification == "unavailable"
    assert evaluate_course(result.catalog.records[0], grade_profile()).status == "unknown"
    assert result.issues


def test_stale_rule_cache_remains_reference_only_during_outage(rule_catalog, tmp_path):
    with http_fixture(rule_catalog) as client:
        first = check(rule_catalog, client, tmp_path)
    with http_fixture(rule_catalog, program_status=503) as client:
        result = check(rule_catalog, client, tmp_path, now=NOW + timedelta(days=1))
    check_result = next(c for c in result.checks if c.kind == "rule")
    assert check_result.status == "stale_cache" and check_result.last_checked_at == NOW
    assert check_result.attempted_at > check_result.last_checked_at
    assert result.catalog.records[0].rule_verification == "stale"
    assert evaluate_course(result.catalog.records[0], grade_profile()).status == "unknown"
    assert corpus_hash(first.catalog) == corpus_hash(result.catalog)


def test_current_program_cannot_hide_a_failed_course_identity_check(rule_catalog, tmp_path):
    with http_fixture(rule_catalog, course_status=503) as client:
        result = check(rule_catalog, client, tmp_path)
    assert result.catalog.sources[-1].verification_status == "verified"
    assert result.catalog.records[0].rule_verification == "stale"
    assert next(c for c in result.checks if c.kind == "rule").rule_status == "stale"
    assert evaluate_course(result.catalog.records[0], grade_profile()).status == "unknown"


def test_corrupt_program_cache_is_not_used_on_failure(rule_catalog, tmp_path):
    with http_fixture(rule_catalog) as client:
        check(rule_catalog, client, tmp_path)
    next((tmp_path / "rules").glob("*.json")).write_text("invalid JSON")
    with http_fixture(rule_catalog, program_status=503) as client:
        result = check(rule_catalog, client, tmp_path)
    assert next(c for c in result.checks if c.kind == "rule").status == "bundled_fallback"
    assert result.catalog.records[0].rule_verification == "unavailable"


def test_conditional_recheck_reuses_the_prerequisite_vector(rule_catalog, fake_provider, tmp_path):
    with http_fixture(rule_catalog, headers={"ETag": '"fixture-etag"'}) as client:
        first = check(rule_catalog, client, tmp_path / "sources")
    cache = EmbeddingCache(tmp_path / "vectors")
    cache.get(first.catalog, build_evidence(first.catalog), fake_provider)
    calls = fake_provider.document_calls
    def unchanged(request):
        assert request.headers["if-none-match"] == '"fixture-etag"'
        return httpx.Response(304)
    with httpx.Client(transport=httpx.MockTransport(unchanged)) as client:
        second = check(rule_catalog, client, tmp_path / "sources", now=NOW + timedelta(hours=1))
    assert second.catalog.records[0].rule_verification == "verified"
    assert next(c for c in second.checks if c.kind == "rule").status == "not_modified"
    assert next(s for s in second.catalog.sources if s.source_id == "catalog:CS_foundations").retrieved_at == NOW
    assert cache.get(second.catalog, build_evidence(second.catalog), fake_provider)[1] == "hit"
    assert fake_provider.document_calls == calls


def test_rule_cache_write_failure_does_not_discard_current_proof(rule_catalog, tmp_path, monkeypatch):
    def fail(*args):
        raise OSError("private filesystem detail")
    monkeypatch.setattr("src.rule_sources._write", fail)
    with http_fixture(rule_catalog) as client:
        result = check(rule_catalog, client, tmp_path)
    assert result.catalog.records[0].rule_verification == "verified"
    assert not next(c for c in result.checks if c.kind == "rule").cache_saved
    assert "private filesystem detail" not in str(result.issues)


def test_unapproved_program_host_is_not_contacted_or_cached(rule_catalog, tmp_path, monkeypatch):
    source = next(s for s in rule_catalog.sources if s.source_id == "catalog:CS_foundations")
    source.url = "https://catalog.arizona.edu.unapproved.example/programs/COSCBS/program-requirements-demo"
    monkeypatch.setattr("src.rule_sources._read", lambda *a: pytest.fail("Unapproved cache was read"))
    seen = []
    with http_fixture(rule_catalog, seen=seen) as client:
        result = check(rule_catalog, client, tmp_path)
    assert source.url not in seen
    assert result.catalog.records[0].rule_verification == "unavailable"


def test_changed_interpretation_cannot_reuse_an_old_review_fingerprint(rule_catalog, tmp_path):
    course = rule_catalog.records[0]
    course.rule.children[0].minimum_grade = "D"
    assert evaluate_course(course, grade_profile()).status == "unknown"
    with pytest.raises(ValidationError, match="interpretation"):
        Catalog.model_validate(rule_catalog.model_dump())
    with http_fixture(rule_catalog) as client:
        result = check(rule_catalog, client, tmp_path)
    assert result.catalog.records[0].rule_verification == "changed"
    assert not any(c.kind == "rule" and c.http_status is not None for c in result.checks)


@pytest.mark.parametrize("field,value", [("course_code", "ECE101"), ("source_id", "catalog:CSC120"),
    ("catalog_version", "2025-2026"), ("evidence_id", "unrelated:rule:identifier")])
def test_provenance_cannot_be_moved_to_another_record_or_source(rule_catalog, field, value):
    data = rule_catalog.model_dump()
    data["records"][0]["rule_evidence"][0][field] = value
    with pytest.raises(ValidationError):
        Catalog.model_validate(data)


def test_snapshot_assessment_is_explicitly_dated(rule_catalog):
    evaluated = evaluate_course(rule_catalog.records[0], grade_profile())
    assert evaluated.status == "satisfied" and evaluated.verification_status == "snapshot"
    assert any("dated" in reason for reason in evaluated.reasons)


def test_rule_evidence_is_atomic_under_a_tight_context_budget(rule_catalog):
    from src.retrieval import Retriever
    chunks = build_evidence(rule_catalog)
    hits = Retriever(chunks).search("programming")
    profile = StudentProfile(programming_background="experienced")
    tight = build_context(rule_catalog, profile, "", "programming", hits, max_chunks=1)
    assert not tight.allowed_record_ids
    complete = build_context(rule_catalog, profile, "", "programming", hits, max_chunks=2)
    assert complete.allowed_record_ids == [rule_catalog.records[0].record_id]
    assert {c.chunk_id for c in complete.evidence} == {c.chunk_id for c in chunks}
    assert set(complete.rule_results[complete.allowed_record_ids[0]].evidence_ids) <= {c.chunk_id for c in complete.evidence}


def test_course_descriptions_and_prerequisite_citations_have_distinct_sources(rule_catalog):
    overview, prerequisite = build_evidence(rule_catalog)
    assert overview.source_ids == ["catalog:CSC120"]
    assert prerequisite.source_ids == ["catalog:CS_foundations"]
    assert "R1299/L40" in prerequisite.text


def test_controller_passes_the_verified_rule_chunk_to_generation(rule_catalog, fake_provider, tmp_path):
    fake_provider.close = lambda: None
    with http_fixture(rule_catalog) as client:
        def refresh(catalog, profile, **kwargs):
            return refresh_catalog(catalog, profile, client=client, now=NOW, **kwargs)
        result = run_advisor(rule_catalog, grade_profile(), use_ai=True, api_key="fixture",
            provider_factory=lambda *a, **k: fake_provider, source_refresher=refresh,
            source_cache_dir=tmp_path / "sources", cache_dir=tmp_path / "vectors")
    rule = result.context.rule_results[rule_catalog.records[0].record_id]
    assert rule.status == "satisfied" and rule.verification_status == "verified"
    assert any(":rule:" in c.chunk_id for c in fake_provider.context.evidence)
    assert result.generation_complete


def test_refresher_failure_cannot_keep_a_current_prerequisite_approval(rule_catalog):
    def fail(*args, **kwargs):
        raise ValueError("bad configuration")
    profile = grade_profile().model_copy(update={"question": "Programming next steps"})
    result = run_advisor(rule_catalog, profile, source_refresher=fail)
    assert result.context.rule_results[rule_catalog.records[0].record_id].status == "unknown"
    assert result.catalog.records[0].rule_verification == "unavailable"


def add_supporting_proof(catalog, *, new_source=False):
    course = catalog.records[0]
    original = course.rule_evidence[0]
    text = "Fixture supporting statement for the same reviewed condition."
    proof = original.model_copy(update={"evidence_id": course.record_id + ":rule:fixture-support",
        "section_id": "R1299/L90", "reviewed_text": text, "statement_hash": statement_hash(text)}, deep=True)
    if new_source:
        source = next(s for s in catalog.sources if s.source_id == original.source_id).model_copy(deep=True)
        source.source_id = "catalog:fixture_program"
        source.url = "https://catalog.arizona.edu/programs/DEMOBA/program-requirements-fixture"
        proof.source_id, proof.program_code = source.source_id, "DEMOBA"
        catalog.sources.append(source)
        course.source_ids.append(source.source_id)
    course.rule_evidence.append(proof)
    return proof


def test_two_sections_share_one_download_and_both_must_match(rule_catalog, tmp_path):
    add_supporting_proof(rule_catalog)
    seen = []
    with http_fixture(rule_catalog, seen=seen) as client:
        result = check(rule_catalog, client, tmp_path)
    program_url = rule_catalog.sources[-1].url
    assert seen.count(program_url) == 1
    assert result.catalog.records[0].rule_verification == "verified"
    page = program_page(rule_catalog.records[0], extra_texts={"R1299/L90": "Changed fixture interpretation."})
    with http_fixture(rule_catalog, program=page) as client:
        changed = check(rule_catalog, client, tmp_path)
    assert changed.catalog.records[0].rule_verification == "changed"
    assert evaluate_course(changed.catalog.records[0], grade_profile()).status == "unknown"


@pytest.mark.parametrize("reverse", [False, True])
def test_one_current_source_cannot_override_another_unavailable_source(rule_catalog, tmp_path, reverse):
    add_supporting_proof(rule_catalog, new_source=True)
    if reverse:
        rule_catalog.records[0].rule_evidence.reverse()
    with http_fixture(rule_catalog, program_status={"DEMOBA": 503}) as client:
        result = check(rule_catalog, client, tmp_path)
    assert result.catalog.records[0].rule_verification == "unavailable"
    assert evaluate_course(result.catalog.records[0], grade_profile()).status == "unknown"
    assert {p.verification_status for p in result.catalog.records[0].rule_evidence} == {"verified", "unavailable"}


@pytest.mark.parametrize("corruption", ["program", "edition", "sections", "hash", "url", "time"])
def test_forged_or_incompatible_program_cache_cannot_approve_during_outage(rule_catalog, tmp_path, corruption):
    with http_fixture(rule_catalog) as client:
        check(rule_catalog, client, tmp_path)
    path = next((tmp_path / "rules").glob("*.json"))
    data = json.loads(path.read_text())
    if corruption == "program":
        data["data"]["program_code"] = "OTHERBS"
    elif corruption == "edition":
        data["data"]["catalog_version"] = "2025-2026"
    elif corruption == "sections":
        data["data"]["statements"] = {"R1/L1": "A different fixture section."}
    elif corruption == "url":
        data["url"] = "https://unapproved.example/program"
    elif corruption == "time":
        data["last_checked_at"] = "2026-01-01T00:00:00Z"
    else:
        data["data"]["statements"]["R1299/L40"] = "Modified cached fixture."
    if corruption != "hash":
        data["content_hash"] = program_hash(ProgramSnapshot.model_validate(data["data"]))
    path.write_text(json.dumps(data))
    with http_fixture(rule_catalog, program_status=503) as client:
        result = check(rule_catalog, client, tmp_path)
    assert next(c for c in result.checks if c.kind == "rule").status == "bundled_fallback"
    assert evaluate_course(result.catalog.records[0], grade_profile()).status == "unknown"


def test_rule_source_budget_keeps_omitted_proof_unknown(rule_catalog, tmp_path, monkeypatch):
    add_supporting_proof(rule_catalog, new_source=True)
    monkeypatch.setattr("src.rule_sources.MAX_RULE_SOURCES", 1)
    with http_fixture(rule_catalog) as client:
        result = check(rule_catalog, client, tmp_path)
    assert result.catalog.records[0].rule_verification == "unavailable"
    assert any(c.kind == "rule" and c.status == "skipped" for c in result.checks)


def test_prerequisite_bundle_cannot_be_split_by_character_limit(rule_catalog):
    from src.retrieval import Retriever
    chunks = build_evidence(rule_catalog)
    hits = Retriever(chunks).search("programming")
    limit = sum(len(c.text) for c in chunks) - 1
    context = build_context(rule_catalog, StudentProfile(), "", "programming", hits, max_characters=limit)
    assert not context.allowed_record_ids


def test_rule_citations_must_resolve_to_the_bound_prerequisite_chunks(rule_catalog):
    data = rule_catalog.model_dump()
    data["records"][0]["rule_evidence"][0]["evidence_id"] += "-renamed"
    with pytest.raises(ValidationError, match="citations"):
        Catalog.model_validate(data)


def test_reviewed_text_cannot_change_without_a_new_fingerprint(rule_catalog):
    data = rule_catalog.model_dump()
    data["records"][0]["rule_evidence"][0]["reviewed_text"] = "Altered fixture source statement."
    with pytest.raises(ValidationError, match="fingerprint"):
        Catalog.model_validate(data)


@pytest.mark.parametrize('prior,expected,verification', [('verified', 'satisfied', 'snapshot'),
                                                       ('changed', 'unknown', 'changed')])
def test_offline_use_preserves_rule_limitations_without_claiming_a_live_check(rule_catalog, tmp_path, prior, expected, verification):
    with http_fixture(rule_catalog) as client:
        active = check(rule_catalog, client, tmp_path).catalog
    active.records[0].rule_verification = prior
    profile = grade_profile().model_copy(update={'question': 'Programming next steps'})
    result = run_advisor(active, profile, refresh_sources=False)
    evaluated = result.context.rule_results[active.records[0].record_id]
    assert evaluated.status == expected and evaluated.verification_status == verification
    assert all(s.verification_status == 'snapshot' for s in result.catalog.sources)
    assert active.records[0].rule_verification == prior
    if prior == 'verified':
        assert any('dated reviewed snapshot' in reason for reason in evaluated.reasons)
