"""Canonical explanation controls and adversarial model-output boundaries.

These controlled selections exercise the application contract, not live model
quality or a general factual-entailment classifier.
"""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from src.evaluation import evaluate_suite, load_suite
from src.grounding import (ANSWER_CONTRACT, CLARIFICATIONS, GroundingError,
                           build_statements, materialize_answer)
from src.models import (Completion, ExplanationSelection, GeneratedAnswer, Reason,
                        Recommendation, SelectedRecommendation, StudentProfile)
from src.retrieval import Hit
from src.service import build_context, recommend, validate_answer, validate_references

ECE101 = "uofa:ECE101:2026-2027"
CSC120 = "uofa:CSC120:2026-2027"
CS50 = "resource:cs50"
NOW = datetime(2026, 11, 4, 4, 0, tzinfo=timezone.utc)


def context_for(catalog, *record_ids, profile=None):
    profile = profile or StudentProfile(career_id="exploring", programming_background="experienced")
    return build_context(catalog, profile, "Explore programming", "C programming",
        [Hit(rid + ":overview", rid, 1, "keyword") for rid in (record_ids or (ECE101, CS50))])


def selection_for(context, *, record_id=None, fields=None):
    rid = record_id or context.allowed_record_ids[0]
    statements = [s for s in context.allowed_statements if s.record_id == rid and (fields is None or s.field in fields)]
    return ExplanationSelection(status="answered", recommendations=[
        SelectedRecommendation(record_id=rid, statement_ids=[s.statement_id for s in statements[:4]])])


def rendered(context, catalog, **options):
    return materialize_answer(selection_for(context, **options), context, catalog)


def assert_rejected(code, callback):
    with pytest.raises(GroundingError) as exc:
        callback()
    assert exc.value.code == code


def test_selected_facts_render_exact_words_types_and_evidence(catalog):
    context = context_for(catalog)
    selection = selection_for(context, fields={"description", "credits", "academic_status", "learning_connection"})
    answer = materialize_answer(selection, context, catalog)
    statements = {s.statement_id: s for s in context.allowed_statements}
    reasons = answer.recommendations[0].reasons
    assert len(reasons) == 4
    for reason, sid in zip(reasons, selection.recommendations[0].statement_ids):
        statement = statements[sid]
        assert (reason.text, reason.claim_type, reason.evidence_ids) == (statement.text, statement.claim_type, statement.evidence_ids)
    assert validate_answer(answer, context, catalog) == answer


@pytest.mark.parametrize("record_id", [ECE101, CSC120, CS50, "resource:pytorch"])
def test_each_available_statement_is_an_accepted_positive_control(catalog, record_id):
    context = context_for(catalog, record_id)
    assert context.allowed_statements
    for statement in context.allowed_statements:
        selection = ExplanationSelection(status="answered", recommendations=[SelectedRecommendation(
            record_id=record_id, statement_ids=[statement.statement_id])])
        assert validate_answer(materialize_answer(selection, context, catalog), context, catalog).status == "answered"


def test_course_credits_and_resource_scope_are_separate(catalog):
    context = context_for(catalog)
    credits = next(s for s in context.allowed_statements if s.record_id == ECE101 and s.field == "credits")
    assert "4 credits" in credits.text and "2026-2027" in credits.text
    resource = [s for s in context.allowed_statements if s.record_id == CS50]
    assert not any(s.field in {"credits", "academic_status", "reviewed_condition"} for s in resource)
    assert "does not establish university credit or course equivalency" in next(s.text for s in resource if s.field == "resource_scope")


def test_unknown_conditions_and_learning_stage_cannot_approve_enrollment(catalog):
    context = context_for(catalog, ECE101)
    condition = next(s for s in context.allowed_statements if s.field == "academic_status")
    assert "remain unverified" in condition.text
    stage = next(s for s in context.allowed_statements if s.field == "learning_stage")
    assert stage.claim_type == "recommendation"
    assert not any(s.field == "reviewed_condition" for s in context.allowed_statements)


@pytest.mark.parametrize("completed,expected", [
    ([Completion(course_code="ECE101", grade="B")], "satisfied"),
    ([Completion(course_code="ECE101", grade="D")], "unsatisfied"),
    ([], "unsatisfied"),
])
def test_reviewed_or_condition_is_literal_and_binds_its_separate_proof(catalog, completed, expected):
    profile = StudentProfile(completed=completed, history_complete=True)
    context = context_for(catalog, CSC120, profile=profile)
    assert context.rule_results[CSC120].status == expected
    proof = next(r for r in catalog.records if r.record_id == CSC120).rule_evidence[0]
    statement = next(s for s in context.allowed_statements if s.field == "reviewed_condition")
    assert proof.reviewed_text in statement.text and statement.evidence_ids == [proof.evidence_id]
    assert "does not establish complete enrollment eligibility" in statement.text
    answer = rendered(context, catalog, fields={"reviewed_condition", "academic_status"})
    assert validate_answer(answer, context, catalog) == answer
    if expected == "satisfied":
        assert "dated 2026-2027" in next(s.text for s in context.allowed_statements if s.field == "academic_status")


@pytest.mark.parametrize("state", ["stale", "changed", "unavailable", "unsupported", "binding_changed", "edition_changed"])
def test_unverified_old_conditions_cannot_be_selected_as_reviewed_facts(catalog, state):
    course = next(r for r in catalog.records if r.record_id == CSC120)
    profile = StudentProfile(completed=[Completion(course_code="ECE101", grade="B")])
    if state == "binding_changed":
        course.rule.children[0].minimum_grade = "B"
    elif state == "edition_changed":
        profile.catalog_version = "2025-2026"
    else:
        course.rule_verification = state
    context = context_for(catalog, CSC120, profile=profile)
    assert context.rule_results[CSC120].status == "unknown"
    assert not any(s.field == "reviewed_condition" for s in context.allowed_statements)
    assert "remain unverified" in next(s.text for s in context.allowed_statements if s.field == "academic_status")


@pytest.mark.parametrize("state,checked", [("snapshot", NOW), ("stale", NOW), ("verified", None),
                                           ("verified", NOW.replace(tzinfo=None)), ("verified", NOW)])
def test_source_check_wording_requires_verified_aware_timestamp(catalog, state, checked):
    course = next(r for r in catalog.records if r.record_id == ECE101)
    source = next(s for s in catalog.sources if s.source_id == course.source_ids[0])
    source.verification_status, source.last_checked_at = state, checked
    context = context_for(catalog, ECE101)
    check_statements = [s for s in context.allowed_statements if s.field == "source_freshness"]
    if state == "verified" and checked is not None and checked.tzinfo is not None:
        assert len(check_statements) == 1 and "2026-11-04 04:00 UTC" in check_statements[0].text
        assert "does not verify every academic condition" in check_statements[0].text
    else:
        assert not check_statements
    if state != "verified":
        assert next(s.text for s in context.allowed_statements if s.field == "description").startswith("Saved source")


def test_resource_edition_is_not_an_academic_catalog_year(catalog):
    next(r for r in catalog.records if r.record_id == CS50).resource_version = "2026"
    context = context_for(catalog, CS50)
    version = next(s for s in context.allowed_statements if s.field == "resource_version")
    assert "edition/version 2026" in version.text and "2026-2027" not in version.text
    assert validate_answer(rendered(context, catalog, fields={"resource_version"}), context, catalog)


@pytest.mark.parametrize("kind", ["invented", "foreign", "previous_request"])
def test_statement_ids_must_belong_to_this_record_and_request(catalog, kind):
    context = context_for(catalog)
    selection = selection_for(context)
    item = selection.recommendations[0]
    if kind == "foreign":
        item.statement_ids = [next(s.statement_id for s in context.allowed_statements if s.record_id == CS50)]
    elif kind == "previous_request":
        other = context_for(catalog, profile=StudentProfile(interests="robotics"))
        item.statement_ids = [next(s.statement_id for s in other.allowed_statements if s.record_id == ECE101)]
    else:
        item.statement_ids = ["stmt:invented"]
    assert_rejected("wrong_record" if kind == "foreign" else "unknown_statement",
                    lambda: materialize_answer(selection, context, catalog))


@pytest.mark.parametrize("kind,code", [("duplicate_record", "invalid_record"), ("unallowed_record", "invalid_record"),
                                      ("duplicate_statement", "duplicate_statement"), ("empty_statements", "invalid_selection"),
                                      ("empty_answer", "invalid_selection"), ("answered_clarification", "invalid_selection")])
def test_mutated_or_repeated_selections_are_rejected(catalog, kind, code):
    context = context_for(catalog)
    selection = selection_for(context)
    item = selection.recommendations[0]
    if kind == "duplicate_record": selection.recommendations.append(item.model_copy(deep=True))
    elif kind == "unallowed_record": item.record_id = "career:ai_ml"
    elif kind == "duplicate_statement": item.statement_ids = [item.statement_ids[0]] * 2
    elif kind == "empty_statements": item.statement_ids = []
    elif kind == "empty_answer": selection.recommendations = []
    else: selection.clarification_code = "more_details"
    assert_rejected(code, lambda: materialize_answer(selection, context, catalog))


@pytest.mark.parametrize("payload", [
    {"status": "answered", "recommendations": []},
    {"status": "insufficient_evidence", "clarification_code": "Invented factual advice"},
    {"status": "insufficient_evidence", "clarification_code": "more_details", "text": "Guaranteed admission"},
    {"status": "answered", "recommendations": [{"record_id": ECE101, "statement_ids": ["id"], "reasons": []}]},
])
def test_selection_schema_has_no_free_prose_channel(payload):
    with pytest.raises(ValidationError):
        ExplanationSelection.model_validate(payload)


@pytest.mark.parametrize("change", ["text", "claim_type", "extra_citation", "extra_fact", "relabeled_fact"])
def test_valid_references_do_not_admit_unlisted_wording_or_types(catalog, change):
    context = context_for(catalog)
    answer = rendered(context, catalog, fields={"credits"})
    reason = answer.recommendations[0].reasons[0]
    if change == "text": reason.text = reason.text.replace("4 credits", "12 credits")
    elif change == "claim_type": reason.claim_type = "recommendation"
    elif change == "extra_citation": reason.evidence_ids.append(CS50 + ":overview")
    elif change == "extra_fact": reason.text += " It guarantees a paid internship."
    else:
        reason.text = "Suggested advice: this course clears every enrollment condition and is offered next semester."
        reason.claim_type = "recommendation"
    validate_references(answer, context)  # The previous checker admits these.
    assert_rejected("unlisted_wording", lambda: validate_answer(answer, context, catalog))


@pytest.mark.parametrize("change,code", [("registry_text", "modified_registry"), ("registry_removed", "modified_registry"),
    ("profile", "modified_registry"), ("evidence", "modified_evidence"), ("missing_proof", "incomplete_evidence"),
    ("freshness", "modified_freshness"), ("rule", "modified_academic_result"), ("stage", "modified_stage"),
    ("provenance", "modified_provenance"), ("catalog_text", "modified_evidence"),
    ("catalog_date", "modified_freshness"), ("duplicate_record", "invalid_context"), ("duplicate_evidence", "invalid_context")])
def test_registry_and_its_authoritative_inputs_are_rechecked(catalog, change, code):
    context = context_for(catalog, CSC120)
    selection = selection_for(context)
    if change == "registry_text": context.allowed_statements[0].text += " A fabricated addition."
    elif change == "registry_removed": context.allowed_statements.pop()
    elif change == "profile": context.profile.interests = "A different request"
    elif change == "evidence": context.evidence[0].text += " Fabricated source content."
    elif change == "missing_proof":
        context.evidence = [e for e in context.evidence if ":rule:" not in e.chunk_id]
        remaining_sources = {sid for e in context.evidence for sid in e.source_ids}
        context.source_freshness = {sid: state for sid, state in context.source_freshness.items() if sid in remaining_sources}
    elif change == "freshness": next(iter(context.source_freshness.values())).last_checked_at = NOW
    elif change == "rule": context.rule_results[CSC120].status = "satisfied"
    elif change == "stage": context.suggested_phases[CSC120] = "next" if context.suggested_phases[CSC120] != "next" else "later"
    elif change == "provenance": context.field_sources[CSC120] = {"credits": "invented"}
    elif change == "catalog_text": next(r for r in catalog.records if r.record_id == CSC120).summary += " Changed."
    elif change == "catalog_date":
        sid = next(iter(context.source_freshness))
        next(s for s in catalog.sources if s.source_id == sid).last_checked_at = NOW + timedelta(days=1)
    elif change == "duplicate_record": context.allowed_record_ids.append(CSC120)
    else: context.evidence.append(context.evidence[0])
    assert_rejected(code, lambda: materialize_answer(selection, context, catalog))


@pytest.mark.parametrize("code", list(CLARIFICATIONS))
def test_abstention_uses_fixed_application_wording(catalog, code):
    context = context_for(catalog)
    answer = materialize_answer(ExplanationSelection(status="insufficient_evidence", clarification_code=code), context, catalog)
    assert answer.clarification == CLARIFICATIONS[code] and not answer.recommendations
    assert validate_answer(answer, context, catalog) == answer
    answer.clarification += " Guaranteed enrollment."
    assert_rejected("unlisted_clarification", lambda: validate_answer(answer, context, catalog))


@pytest.mark.parametrize("change,code", [("extra_clarification", "unlisted_clarification"), ("empty_reasons", "invalid_answer"),
                                       ("duplicate_reason", "duplicate_statement")])
def test_rendered_answer_shape_and_extra_channels_are_checked(catalog, change, code):
    context = context_for(catalog)
    answer = rendered(context, catalog, fields={"description"})
    if change == "extra_clarification": answer.clarification = "Fabricated advice."
    elif change == "empty_reasons": answer.recommendations[0].reasons = []
    else: answer.recommendations[0].reasons *= 2
    assert_rejected(code, lambda: validate_answer(answer, context, catalog))


@pytest.mark.parametrize("field,value", [("summary", "Source text with https://invalid.example/a"),
    ("summary", "x" * 1500), ("learning_note", "Try https://invalid.example/b"),
    ("first_activity", "Open HTTPS://invalid.example/c")])
def test_url_bearing_or_oversized_statements_are_omitted(catalog, field, value):
    course = next(r for r in catalog.records if r.record_id == ECE101)
    setattr(course, field, value)
    context = context_for(catalog, ECE101)
    statement_field = {"summary": "description", "learning_note": "learning_connection", "first_activity": "first_activity"}[field]
    assert not any(s.field == statement_field for s in context.allowed_statements)
    assert validate_answer(rendered(context, catalog, fields={"academic_status"}), context, catalog)


def test_registry_limit_fails_closed_with_excessive_source_metadata(catalog):
    course = next(r for r in catalog.records if r.record_id == ECE101)
    source = next(s for s in catalog.sources if s.source_id == course.source_ids[0])
    for i in range(81):
        additional = source.model_copy(update={"source_id": f"fixture:source:{i}", "verification_status": "verified", "last_checked_at": NOW})
        catalog.sources.append(additional)
        course.source_ids.append(additional.source_id)
    assert_rejected("registry_limit", lambda: context_for(catalog, ECE101))


def test_legacy_free_prose_provider_fails_without_losing_source_cards(catalog, fake_provider, tmp_path):
    def legacy(context):
        return GeneratedAnswer(status="answered", recommendations=[Recommendation(record_id=context.allowed_record_ids[0],
            reasons=[Reason(text="Guaranteed enrollment.", claim_type="recommendation",
                evidence_ids=[context.allowed_record_ids[0] + ":overview"])])])
    fake_provider.generate = legacy
    result = recommend(catalog, StudentProfile(), provider=fake_provider, method="keyword", cache_dir=tmp_path)
    assert result.answer is None and result.context.allowed_record_ids and result.hits
    assert result.generation_status == "failed" and result.statement_validation_passed is False
    assert result.trace["validation_error"] == "unsupported_output"
    assert result.trace["answer_contract"] == ANSWER_CONTRACT
    assert "Guaranteed enrollment" not in str(result.trace) and result.selected_statement_ids == []


def test_success_trace_records_the_exact_selected_statement_ids(catalog, fake_provider, tmp_path):
    result = recommend(catalog, StudentProfile(), provider=fake_provider, method="keyword", cache_dir=tmp_path)
    assert result.statement_validation_passed is True
    assert result.trace["validation_error"] is None
    assert result.selected_statement_ids == result.trace["selected_statement_ids"]
    assert result.selected_statement_ids and set(result.selected_statement_ids) <= {s.statement_id for s in result.context.allowed_statements}


def test_no_generation_keeps_validation_unclaimed(catalog):
    result = recommend(catalog, StudentProfile())
    assert result.statement_validation_passed is None and result.trace["statement_validation_passed"] is None


def test_frozen_counterexamples_and_positive_controls_have_separate_results(catalog):
    report = evaluate_suite(catalog, load_suite(catalog))
    assert report["claim_summary"]["unsupported_claims_admitted_by_reference_checks"] == 9
    summary = report["render_contract_summary"]
    assert summary["unsupported_reviewed_claims_admitted"] == 0
    assert summary["legacy_authored_answers_accepted"] == 0  # True paraphrases are outside this contract too.
    assert summary["canonical_controls"]["attempted"] > 0
    assert summary["canonical_controls"]["accepted"] == summary["canonical_controls"]["attempted"]
    assert report["generation_calls"] == 0 and report["regression_checks_passed"]
