"""Controlled evidence for a reviewed rule attached during course discovery."""

import json
from datetime import timedelta

import httpx
import pytest
from pydantic import ValidationError

from src.catalog import build_evidence, corpus_hash
from src.controller import run_advisor
from src.discovery import DiscoveryPlan, load_discovery_plans
from src.models import Catalog, Completion, Record, StudentProfile, rule_hash
from src.retrieval import Hit
from src.rule_sources import ProgramSnapshot, program_hash
from src.rules import evaluate_course
from src.service import build_context, recommend
from src.sources import refresh_catalog
from test_discovery import NOW, client_for, program_page
from test_sources import course_page

RID = "uofa:CSC110:2026-2027"
IDENTITY = "0393681"
MISSING = object()


def rule_client(catalog, *, text=MISSING, identity=IDENTITY, reference="017080", program=None,
                course=None, headers=None, seen=None, extras=()):
    plan = load_discovery_plans()[0]
    record = Record(record_id="fixture:CSC110", kind="course", code="CSC110", title="Fixture programming I",
        summary="Fixture introductory programming.", credits=4, source_ids=["fixture"],
        catalog_version="2026-2027", requirement_reference=reference)
    def modify(primary, rules):
        if text is not None:
            rules[0]["description"] = plan.reviewed_rules[0].proof.reviewed_text if text is MISSING else text
    proofs = next(r for r in catalog.records if r.code == "CSC120").rule_evidence
    page = program_page(plan, ids=[identity], proofs=proofs, modify=modify, extras=extras)
    return client_for(catalog, [plan], {identity: record},
        programs={"COSCBS": page if program is None else program},
        courses={identity: course} if course is not None else None, headers=headers, seen=seen)


def refresh(catalog, client, path, profile=None, now=NOW):
    return refresh_catalog(catalog, profile or StudentProfile(), client=client, cache_dir=path,
                           discovery_plans=load_discovery_plans()[:1], now=now)


def discovered(result):
    return next(r for r in result.catalog.records if r.record_id == RID)


def math_profile(grade="B", **options):
    return StudentProfile(completed=[Completion(course_code="MATH112", grade=grade)], **options)


@pytest.mark.parametrize("grade,expected", [("A", "satisfied"), ("B", "satisfied"), ("C", "satisfied"),
    ("C-", "unknown"), ("D", "unknown"), ("P", "unknown"), (None, "unknown")])
def test_reviewed_coursework_branch_and_unknown_placement(catalog, tmp_path, grade, expected):
    profile = math_profile(grade, history_complete=True)
    with rule_client(catalog) as client:
        result = refresh(catalog, client, tmp_path, profile)
    record = discovered(result)
    assert record.rule_reviewed and record.rule_verification == "verified"
    assert evaluate_course(record, profile).status == expected
    assert record.rule.children[1].type == "unknown"
    assert "placement" in record.rule.children[1].note
    assert next(c for c in result.checks if c.code == "CSC110").rule_status == "verified"
    Catalog.model_validate(result.catalog.model_dump())


@pytest.mark.parametrize("profile", [StudentProfile(history_complete=True, standing="Senior"),
    StudentProfile(current_enrollment=["MATH112"], history_complete=True),
    StudentProfile(consents=["appropriate math placement", "MATH120R"], history_complete=True)])
def test_standing_concurrency_and_unverified_placement_cannot_clear_condition(catalog, tmp_path, profile):
    with rule_client(catalog) as client:
        record = discovered(refresh(catalog, client, tmp_path, profile))
    assert evaluate_course(record, profile).status == "unknown"


def test_course_and_rule_have_distinct_source_chunks_and_atomic_context(catalog, tmp_path):
    with rule_client(catalog) as client:
        result = refresh(catalog, client, tmp_path, math_profile())
    record = discovered(result)
    chunks = [e for e in build_evidence(result.catalog) if e.record_id == RID]
    assert len(chunks) == 2
    assert chunks[0].source_ids == ["catalog:CSC110"]
    assert chunks[1].source_ids == ["catalog:CS_foundations"]
    context = build_context(result.catalog, math_profile(), "CSC110", "CSC110", [Hit(chunks[0].chunk_id, RID, 1, "keyword")])
    assert context.rule_results[RID].status == "satisfied"
    assert any(s.field == "reviewed_condition" and s.evidence_ids == [record.rule_evidence[0].evidence_id] for s in context.allowed_statements)
    tiny = build_context(result.catalog, math_profile(), "CSC110", "CSC110", [Hit(chunks[0].chunk_id, RID, 1, "keyword")], max_chunks=1)
    assert RID not in tiny.allowed_record_ids


@pytest.mark.parametrize("text,status", [(None, "unavailable"), ("A changed placement requirement awaits interpretation.", "changed")])
def test_missing_or_changed_statement_retains_description_with_unknown_rule(catalog, tmp_path, text, status):
    with rule_client(catalog, text=text) as client:
        result = refresh(catalog, client, tmp_path, math_profile())
    record = discovered(result)
    assert record.rule_verification == status and evaluate_course(record, math_profile()).status == "unknown"
    assert next(c for c in result.checks if c.code == "CSC110").rule_status == status
    answer = recommend(result.catalog, math_profile(), "CSC110")
    assert not any(s.field == "reviewed_condition" and s.record_id == RID for s in answer.context.allowed_statements)


@pytest.mark.parametrize("visible,expected", [(None, "unavailable"), (MISSING, "verified")])
def test_unrelated_metadata_cannot_supply_or_replace_visible_condition(catalog, tmp_path, visible, expected):
    reviewed = load_discovery_plans()[0].reviewed_rules[0].proof.reviewed_text
    decoy = {"id": "metadata", "name": "Unrelated old section (R1299/L30)",
             "description": reviewed if visible is None else "A conflicting metadata condition."}
    with rule_client(catalog, text=visible, extras=[decoy]) as client:
        record = discovered(refresh(catalog, client, tmp_path, math_profile()))
    assert record.rule_verification == expected


@pytest.mark.parametrize("options", [{"identity": "7654324"}, {"reference": "999999"}])
def test_matching_code_without_exact_course_and_enrollment_binding_stays_unreviewed(catalog, tmp_path, options):
    with rule_client(catalog, **options) as client:
        record = discovered(refresh(catalog, client, tmp_path, math_profile()))
    assert not record.rule_reviewed and not record.rule_evidence
    assert evaluate_course(record, math_profile()).status == "unknown"


def test_one_program_download_serves_old_rule_new_rule_and_discovery(catalog, tmp_path):
    seen = []
    with rule_client(catalog, seen=seen) as client:
        result = refresh(catalog, client, tmp_path, math_profile())
    plan = load_discovery_plans()[0]
    assert seen.count(plan.source.url) == 1
    assert len([url for url in seen if "/courses/" in url]) == 4
    assert discovered(result).rule_verification == "verified"
    assert next(r for r in result.catalog.records if r.code == "CSC120").rule_verification == "verified"
    info = result.trace()["discovered_courses"][RID]
    assert info["rule_evidence_ids"] == [discovered(result).rule_evidence[0].evidence_id]
    assert info["rule_hash"] == rule_hash(discovered(result).rule)
    assert info["reviewed_statement_hashes"] == {p.evidence_id: p.statement_hash for p in discovered(result).rule_evidence}


def test_304_reuses_validated_statement_without_advancing_content_download(catalog, tmp_path):
    with rule_client(catalog, headers={"ETag": '"fixture-rule"'}) as client:
        first = refresh(catalog, client, tmp_path, math_profile())
    later = NOW + timedelta(days=1)
    with rule_client(catalog, program=304) as client:
        second = refresh(catalog, client, tmp_path, math_profile(), now=later)
    assert discovered(second).rule_verification == "verified"
    source = next(s for s in second.catalog.sources if s.source_id == "catalog:CS_foundations")
    assert source.retrieved_at == NOW and source.last_checked_at == later
    assert next(c for c in second.checks if c.kind == "rule").status == "not_modified"
    # Only course timestamps changed; evidence and the interpretation stay the same.
    assert corpus_hash(first.catalog) == corpus_hash(second.catalog)


def test_legacy_program_cache_cannot_supply_new_rule_evidence_on_304(catalog, tmp_path):
    with rule_client(catalog) as client:
        refresh(catalog, client, tmp_path)
    path = next((tmp_path / "rules").glob("*.json"))
    data = json.loads(path.read_text())
    data["schema_version"] = 2
    data["data"].pop("discovery_statements")
    path.write_text(json.dumps(data))
    with rule_client(catalog, program=304) as client:
        result = refresh(catalog, client, tmp_path)
    assert not any(r.record_id == RID for r in result.catalog.records)
    assert next(c for c in result.checks if c.kind == "rule").failure_kind == "validation"


@pytest.mark.parametrize("corruption", ["statement", "foreign_section"])
def test_invalid_or_rehashed_changed_cache_cannot_approve_math_branch(catalog, tmp_path, corruption):
    with rule_client(catalog) as client:
        refresh(catalog, client, tmp_path)
    path = next((tmp_path / "rules").glob("*.json"))
    data = json.loads(path.read_text())
    section = "R1299/L30" if corruption == "statement" else "R999/L10"
    data["data"]["discovery_statements"] = {section: "Different fixture condition."}
    if corruption == "statement":
        data["content_hash"] = program_hash(ProgramSnapshot.model_validate(data["data"]))
    path.write_text(json.dumps(data))
    with rule_client(catalog, program=304) as client:
        result = refresh(catalog, client, tmp_path, math_profile())
    if corruption == "statement":
        record = discovered(result)
        assert record.rule_verification == "changed" and evaluate_course(record, math_profile()).status == "unknown"
    else:
        assert not any(r.record_id == RID for r in result.catalog.records)


def test_course_outage_cannot_approve_a_fresh_program_condition(catalog, tmp_path):
    with rule_client(catalog) as client:
        refresh(catalog, client, tmp_path, math_profile())
    with rule_client(catalog, course=503) as client:
        result = refresh(catalog, client, tmp_path, math_profile(), now=NOW + timedelta(days=1))
    record = discovered(result)
    assert record.rule_evidence[0].verification_status == "verified"
    assert record.rule_verification == "stale" and evaluate_course(record, math_profile()).status == "unknown"


def test_program_outage_with_already_discovered_record_revokes_its_condition(catalog, tmp_path):
    with rule_client(catalog) as client:
        first = refresh(catalog, client, tmp_path, math_profile())
    with rule_client(first.catalog, program=503) as client:
        second = refresh(first.catalog, client, tmp_path, math_profile(), now=NOW + timedelta(days=1))
    assert evaluate_course(discovered(second), math_profile()).status == "unknown"


def test_offline_snapshot_preserves_qualified_condition_but_not_live_verification(catalog, tmp_path):
    with rule_client(catalog) as client:
        active = refresh(catalog, client, tmp_path, math_profile()).catalog
    result = run_advisor(active, math_profile(), refresh_sources=False)
    record = next(r for r in result.catalog.records if r.record_id == RID)
    assert record.rule_verification == "snapshot" and evaluate_course(record, math_profile()).status == "satisfied"
    assert any("dated reviewed snapshot" in reason for reason in evaluate_course(record, math_profile()).reasons)


def test_other_editions_do_not_make_requests_or_add_rules(catalog, tmp_path):
    with rule_client(catalog, seen=(seen := [])) as client:
        result = refresh(catalog, client, tmp_path, StudentProfile(catalog_version="2025-2026"))
    assert not seen and not any(r.record_id == RID for r in result.catalog.records)


def test_controlled_generation_receives_the_new_proof_and_conservative_result(catalog, fake_provider, tmp_path):
    def refresher(active, profile, **kwargs):
        with rule_client(active) as client:
            return refresh(active, client, tmp_path / "sources", profile)
    fake_provider.close = lambda: None
    profile = math_profile(question="CSC110")
    result = run_advisor(catalog, profile, source_refresher=refresher, use_ai=True, api_key="fixture",
        method="keyword", provider_factory=lambda *args, **kwargs: fake_provider, cache_dir=tmp_path / "vectors")
    assert result.generation_complete and result.statement_validation_passed
    assert result.context.rule_results[RID].status == "satisfied"
    assert any(e.chunk_id == "uofa:CSC110:2026-2027:rule:R1299-L30" for e in fake_provider.context.evidence)


@pytest.mark.parametrize("field,value", [("source_id", "other"), ("program_code", "OTHERBS"),
    ("catalog_version", "2025-2026"), ("section_id", "R1299/L40"), ("course_code", "CSC111"),
    ("statement_hash", "0" * 64), ("rule_hash", "0" * 64), ("evidence_id", "uofa:OTHER:2026-2027:rule:R1")])
def test_manifest_cannot_silently_rebind_proof_identity_or_interpretation(field, value):
    data = load_discovery_plans()[0].model_dump(mode="json")
    data["reviewed_rules"][0]["proof"][field] = value
    with pytest.raises(ValidationError):
        DiscoveryPlan.model_validate(data)


@pytest.mark.parametrize("field", ["course_id", "course_code"])
def test_duplicate_manifest_identity_is_rejected(field):
    data = load_discovery_plans()[0].model_dump(mode="json")
    duplicate = json.loads(json.dumps(data["reviewed_rules"][0]))
    if field == "course_id":
        duplicate["course_code"] = "CSC111"  # A mismatched proof is also invalid.
    data["reviewed_rules"].append(duplicate)
    with pytest.raises(ValidationError):
        DiscoveryPlan.model_validate(data)
