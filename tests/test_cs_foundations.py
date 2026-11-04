"""Controlled current-scope CS conditions; no external requests or model calls."""

from datetime import timedelta

import pytest

from src.catalog import build_evidence
from src.discovery import load_discovery_plans
from src.models import Catalog, Completion, Record, StudentProfile
from src.planning import learning_phase
from src.retrieval import Hit
from src.rules import evaluate_course
from src.service import build_context
from src.sources import refresh_catalog
from test_discovery import NOW, client_for, program_page


def expanded_refresh(catalog, path, profile, *, mutate=None, program=None, course_payloads=None,
                     identities=None, references=None, headers=None, seen=None, now=NOW):
    plan = load_discovery_plans()[0]
    entries = plan.reviewed_rules
    identities, references = identities or {}, references or {}
    ids = {entry.proof.section_id: [identities.get(entry.course_code, entry.course_id)] for entry in entries}
    new_courses = {identities.get(entry.course_code, entry.course_id): Record(
        record_id="fixture:" + entry.course_code, kind="course", code=entry.course_code,
        title="Fixture " + entry.course_code,
        summary="Fixture discrete mathematics and software programming course.", credits=3,
        source_ids=["fixture"], catalog_version="2026-2027", review_status="synthetic_fixture",
        requirement_reference=references.get(entry.course_code, entry.requirement_reference)) for entry in entries}
    def descriptions(primary, rules):
        for node, entry in zip(rules, entries):
            node["description"] = entry.proof.reviewed_text
        if mutate:
            mutate(primary, rules)
    proofs = next(r for r in catalog.records if r.code == "CSC120").rule_evidence
    page = program_page(plan, ids_by_section=ids, proofs=proofs, modify=descriptions)
    with client_for(catalog, [plan], new_courses, programs={"COSCBS": page if program is None else program},
                    courses=course_payloads, headers=headers, seen=seen) as client:
        return refresh_catalog(catalog, profile, discovery_plans=[plan], client=client, cache_dir=path, now=now)


def course(result, code):
    return next(r for r in result.catalog.records if r.code == code)


def profile_with(*courses, **kwargs):
    return StudentProfile(completed=[Completion(course_code=code, grade=grade) for code, grade in courses],
                          history_complete=True, **kwargs)


@pytest.mark.parametrize("programming", ["CSC110", "ECE101", "ECE175", "ISTA130"])
def test_csc144_accepts_each_explicit_introductory_alternative(catalog, tmp_path, programming):
    profile = profile_with((programming, "C"), ("MATH112", "C"))
    record = course(expanded_refresh(catalog, tmp_path, profile), "CSC144")
    assert record.rule_verification == "verified"
    assert evaluate_course(record, profile).status == "satisfied"


@pytest.mark.parametrize("math", ["MATH112", "MATH113", "MATH116", "MATH120R", "MATH122A", "MATH122B", "MATH125"])
def test_csc144_accepts_only_the_explicit_math_coursework_alternatives(catalog, tmp_path, math):
    profile = profile_with(("ECE101", "B"), (math, "C"))
    record = course(expanded_refresh(catalog, tmp_path, profile), "CSC144")
    assert evaluate_course(record, profile).status == "satisfied"


@pytest.mark.parametrize("completed,expected", [
    ([("ECE101", "C-"), ("MATH125", "B")], "unsatisfied"),
    ([("ECE101", "P"), ("MATH125", "B")], "unknown"),
    ([("ECE101", None), ("MATH125", "B")], "unknown"),
    ([("ECE101", "C"), ("MATH112", "C-")], "unknown"),
    ([("ECE101", "C"), ("MATH112", None)], "unknown"),
    ([("ECE101", "C"), ("MATH112", "P")], "unknown"),
    ([("ECE101", "C")], "unknown"),
    ([("MATH125", "B")], "unsatisfied"),
    ([], "unsatisfied"),
    ([("ECE101", "C"), ("MATH125", "D")], "satisfied"),
])
def test_csc144_preserves_and_or_grades_and_unverified_placement(catalog, tmp_path, completed, expected):
    profile = profile_with(*completed, standing="Senior", consents=["math placement", "instructor"])
    record = course(expanded_refresh(catalog, tmp_path, profile), "CSC144")
    assert evaluate_course(record, profile).status == expected
    # The source gives MATH112 a C threshold, but no such threshold for the other math alternatives.
    assert record.rule.children[1].children[0].type == "unknown"


@pytest.mark.parametrize("concurrent,completed,expected", [
    (["ECE101"], [("MATH125", "B")], "unsatisfied"),
    (["MATH125"], [("ECE101", "B")], "unknown"),
])
def test_csc144_prior_coursework_cannot_be_replaced_by_concurrent_enrollment(catalog, tmp_path, concurrent, completed, expected):
    profile = profile_with(*completed, current_enrollment=concurrent)
    assert evaluate_course(course(expanded_refresh(catalog, tmp_path, profile), "CSC144"), profile).status == expected


@pytest.mark.parametrize("grade,expected", [("A", "satisfied"), ("B", "satisfied"), ("C", "satisfied"),
    ("C-", "unsatisfied"), ("D", "unsatisfied"), ("P", "unknown"), (None, "unknown")])
def test_csc210_requires_csc120_with_a_confirmed_minimum_grade(catalog, tmp_path, grade, expected):
    profile = profile_with(("CSC120", grade))
    record = course(expanded_refresh(catalog, tmp_path, profile), "CSC210")
    assert record.rule_verification == "verified"
    assert evaluate_course(record, profile).status == expected


@pytest.mark.parametrize("profile,expected", [
    (StudentProfile(), "unknown"),
    (StudentProfile(history_complete=True), "unsatisfied"),
    (StudentProfile(history_complete=True, current_enrollment=["CSC120"]), "unsatisfied"),
    (StudentProfile(history_complete=True, standing="Senior", consents=["instructor"]), "unsatisfied"),
    (profile_with(("ECE201", "A")), "unsatisfied"),
])
def test_csc210_does_not_invent_equivalencies_concurrency_or_permission_alternatives(catalog, tmp_path, profile, expected):
    assert evaluate_course(course(expanded_refresh(catalog, tmp_path, profile), "CSC210"), profile).status == expected


@pytest.mark.parametrize("code", ["CSC144", "CSC210"])
@pytest.mark.parametrize("change,verification", [("missing", "unavailable"), ("changed", "changed"), ("hidden", "unavailable")])
def test_new_conditions_need_their_own_unchanged_visible_section(catalog, tmp_path, code, change, verification):
    def mutate(primary, rules):
        index = 1 if code == "CSC144" else 2
        if change == "missing": rules[index].pop("description")
        elif change == "changed": rules[index]["description"] = "Changed fixture condition."
        else: rules[index]["showInCatalog"] = False
    profile = profile_with(("ECE101", "B"), ("MATH112", "B"), ("CSC120", "B"))
    result = expanded_refresh(catalog, tmp_path, profile, mutate=mutate)
    if change == "hidden":
        # Hidden link sections fail the configured discovery plan; they cannot approve new conditions.
        assert not any(r.code == code for r in result.catalog.records)
    else:
        record = course(result, code)
        assert record.rule_verification == verification
        assert evaluate_course(record, profile).status == "unknown"
        assert course(result, "CSC110").rule_verification == "verified"


@pytest.mark.parametrize("code", ["CSC144", "CSC210"])
@pytest.mark.parametrize("mismatch", ["identity", "enrollment_reference"])
def test_same_course_code_is_insufficient_without_the_bound_course_and_reference(catalog, tmp_path, code, mismatch):
    options = {"identities" if mismatch == "identity" else "references": {code: "7654321"}}
    result = expanded_refresh(catalog, tmp_path, profile_with(("ECE101", "B"), ("MATH112", "B"), ("CSC120", "B")), **options)
    record = course(result, code)
    assert not record.rule_reviewed and not record.rule_evidence
    assert evaluate_course(record, StudentProfile()).status == "unknown"
    if code == "CSC210" and mismatch == "enrollment_reference":
        assert record.study_stage == "intermediate"  # A changed condition cannot relabel it as introductory.


def test_expanded_cs_scope_keeps_shared_download_budgets_and_stages(catalog, tmp_path):
    seen = []
    profile = profile_with(("ECE101", "B"), ("MATH112", "B"), ("CSC120", "B"))
    result = expanded_refresh(catalog, tmp_path, profile, seen=seen)
    assert len([url for url in seen if "/programs/" in url]) == 1
    assert len([url for url in seen if "/courses/" in url]) == 6
    assert {r.code for r in result.catalog.records if r.discovery} == {"CSC110", "CSC144", "CSC210"}
    assert course(result, "CSC144").study_stage == "foundation"
    assert course(result, "CSC210").study_stage == "intermediate"
    assert learning_phase(course(result, "CSC210"), profile, evaluate_course(course(result, "CSC210"), profile)) == "next"
    for code in ["ECE101", "ECE369A", "ECE372A", "ECE425"]:
        assert not course(result, code).rule_reviewed
    Catalog.model_validate(result.catalog.model_dump())


@pytest.mark.parametrize("code", ["CSC144", "CSC210"])
def test_each_new_proof_is_separate_from_the_description_and_atomic_in_context(catalog, tmp_path, code):
    profile = profile_with(("ECE101", "B"), ("MATH112", "B"), ("CSC120", "B"))
    result = expanded_refresh(catalog, tmp_path, profile)
    record = course(result, code)
    evidence = [e for e in build_evidence(result.catalog) if e.record_id == record.record_id]
    assert len(evidence) == 2
    assert evidence[0].source_ids == ["catalog:" + code]
    assert evidence[1].source_ids == ["catalog:CS_foundations"]
    hits = [Hit(evidence[0].chunk_id, record.record_id, 1.0, "keyword")]
    context = build_context(result.catalog, profile, code, code, hits)
    assert {e.chunk_id for e in evidence} <= {e.chunk_id for e in context.evidence}
    tiny = build_context(result.catalog, profile, code, code, hits, max_chunks=1)
    assert record.record_id not in tiny.allowed_record_ids
    assert not any(e.record_id == record.record_id for e in tiny.evidence)


def test_304_preserves_all_three_bound_discovery_conditions(catalog, tmp_path):
    profile = profile_with(("ECE101", "B"), ("MATH112", "B"), ("CSC120", "B"))
    first = expanded_refresh(catalog, tmp_path, profile, headers={"ETag": '"fixture-cs"'})
    second = expanded_refresh(catalog, tmp_path, profile, program=304, now=NOW + timedelta(days=1))
    for code in ["CSC110", "CSC144", "CSC210"]:
        assert course(first, code).rule_verification == course(second, code).rule_verification == "verified"
        assert evaluate_course(course(second, code), profile).status == "satisfied"


@pytest.mark.parametrize("code,identity", [("CSC144", "0420001"), ("CSC210", "0393711")])
def test_failed_course_revalidation_cannot_be_overridden_by_fresh_program_text(catalog, tmp_path, code, identity):
    profile = profile_with(("ECE101", "B"), ("MATH112", "B"), ("CSC120", "B"))
    expanded_refresh(catalog, tmp_path, profile)
    result = expanded_refresh(catalog, tmp_path, profile, course_payloads={identity: 503}, now=NOW + timedelta(days=1))
    record = course(result, code)
    assert record.rule_verification == "stale"
    assert evaluate_course(record, profile).status == "unknown"
    assert next(check for check in result.checks if check.code == code).status == "stale_cache"
