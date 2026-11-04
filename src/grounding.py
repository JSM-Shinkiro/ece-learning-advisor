"""Application-owned explanation statements and untrusted model selections.

This validates a bounded output contract, not unrestricted prose entailment.
Source quality and recommendation suitability still need separate evaluation.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import timezone

from .catalog import build_evidence
from .models import (ExplanationSelection, ExplanationStatement, GeneratedAnswer, Reason, Recommendation,
                     SourceFreshness, rule_binding_matches)
from .planning import learning_phase
from .rules import evaluate_course

ANSWER_CONTRACT = "statement-selection-v1"
MAX_STATEMENTS = 80
CLARIFICATIONS = {
    "insufficient_evidence": "I could not form a supported explanation from the selected evidence. Try a more specific learning question.",
    "more_details": "Please add a learning goal or clarify what you want to explore.",
}


class GroundingError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def _checked_inputs(catalog, context):
    chunks = {e.chunk_id: e for e in build_evidence(catalog)}
    records = {r.record_id: r for r in catalog.records}
    ids = [e.chunk_id for e in context.evidence]
    allowed = context.allowed_record_ids
    if len(ids) != len(set(ids)) or len(allowed) != len(set(allowed)) or len(allowed) > 5:
        raise GroundingError("invalid_context", "Explanation context identities are inconsistent")
    for chunk in context.evidence:
        if chunks.get(chunk.chunk_id) != chunk:
            raise GroundingError("modified_evidence", "Explanation evidence does not match the active catalog")
    source_ids = {sid for e in context.evidence for sid in e.source_ids}
    sources = {s.source_id: s for s in catalog.sources}
    for sid, freshness in context.source_freshness.items():
        source = sources.get(sid)
        if sid not in source_ids or source is None or freshness != SourceFreshness(
                verification_status=source.verification_status, retrieved_at=source.retrieved_at,
                last_checked_at=source.last_checked_at):
            raise GroundingError("modified_freshness", "Explanation source dates do not match the active catalog")
    for rid in allowed:
        record = records.get(rid)
        required = {e.chunk_id for e in chunks.values() if e.record_id == rid}
        if record is None or record.kind == "career" or not required or not required <= set(ids):
            raise GroundingError("incomplete_evidence", "An explanation record needs its complete evidence bundle")
        evaluation = evaluate_course(record, context.profile) if record.kind == "course" else None
        if evaluation is not None:
            supplied = context.rule_results.get(rid)
            if supplied is None or supplied.model_dump(exclude={"reasons"}) != evaluation.model_dump(exclude={"reasons"}):
                raise GroundingError("modified_academic_result", "Explanation academic results do not match application evaluation")
        if context.suggested_phases.get(rid) != learning_phase(record, context.profile, evaluation):
            raise GroundingError("modified_stage", "Explanation learning stages do not match application policy")
        if context.field_sources.get(rid, {}) != record.field_sources:
            raise GroundingError("modified_provenance", "Explanation field sources do not match the active catalog")
    return chunks, records


def build_statements(catalog, context):
    chunks, records = _checked_inputs(catalog, context)
    seed = hashlib.sha256(json.dumps(context.model_dump(mode="json", exclude={"allowed_statements"}),
                                     sort_keys=True).encode()).hexdigest()
    statements = []

    def add(rid, field, claim_type, text, evidence_ids):
        evidence_ids = list(dict.fromkeys(evidence_ids))
        if not text or len(text) > 1400 or re.search(r"https?://", text, re.I):
            return
        if not evidence_ids or len(evidence_ids) > 8 or not set(evidence_ids) <= {e.chunk_id for e in context.evidence}:
            raise GroundingError("unprovided_evidence", "An explanation statement needs supplied evidence")
        if not any(chunks[key].record_id == rid for key in evidence_ids):
            raise GroundingError("wrong_record", "An explanation statement needs evidence about its record")
        if len(statements) >= MAX_STATEMENTS:
            raise GroundingError("registry_limit", "The explanation statement list exceeds its request limit")
        identity = json.dumps([ANSWER_CONTRACT, seed, rid, field, claim_type, text, evidence_ids])
        statements.append(ExplanationStatement(statement_id="stmt:" + hashlib.sha256(identity.encode()).hexdigest(),
            record_id=rid, field=field, claim_type=claim_type, text=text, evidence_ids=evidence_ids))

    for rid in context.allowed_record_ids:
        record = records[rid]
        overview = rid + ":overview"
        label = record.code or record.title
        own_sources = [context.source_freshness.get(sid) for sid in chunks[overview].source_ids]
        saved = not own_sources or any(s is None or s.verification_status != "verified" for s in own_sources)
        prefix = "Saved source description" if saved else "Source description"
        add(rid, "description", "source_fact", f"{prefix} for {label}: {record.summary}", [overview])
        if record.kind == "course":
            if record.credits is not None:
                saved_word = "saved " if saved else ""
                add(rid, "credits", "source_fact",
                    f"The {saved_word}{record.catalog_version} source entry lists {label} as {record.credits:g} credits.", [overview])
            evaluation = context.rule_results[rid]
            rule_ids = evaluation.evidence_ids or [overview]
            if evaluation.status == "satisfied":
                text = f"The recorded coursework satisfies the stored reviewed condition for {label}. This does not establish complete enrollment eligibility."
                if evaluation.verification_status == "snapshot":
                    text = f"The recorded coursework satisfies the dated {record.catalog_version} reviewed condition for {label}. This does not establish complete enrollment eligibility."
            elif evaluation.status == "unsatisfied":
                text = f"The supplied history does not satisfy the stored reviewed condition for {label}. This is not a complete enrollment decision."
            else:
                text = f"Enrollment requirements for {label} remain unverified in this request. Confirm them with the official source or an advisor."
            add(rid, "academic_status", "source_fact", text, rule_ids)
            if (record.rule_reviewed and record.rule_evidence and rule_binding_matches(record)
                    and context.profile.catalog_version == record.catalog_version
                    and evaluation.verification_status in {"snapshot", "verified"}):
                for proof in record.rule_evidence:
                    add(rid, "reviewed_condition", "source_fact",
                        f"Stored reviewed {record.catalog_version} source condition for {label}: {proof.reviewed_text} "
                        "This condition alone does not establish complete enrollment eligibility.", [proof.evidence_id])
        else:
            add(rid, "resource_scope", "source_fact",
                f"{label} is complementary independent study. This app does not establish university credit or course equivalency for it.", [overview])
            if record.resource_version:
                add(rid, "resource_version", "source_fact",
                    f"The saved resource record for {label} is labeled edition/version {record.resource_version}.", [overview])
        for sid in chunks[overview].source_ids:
            freshness = context.source_freshness.get(sid)
            if (freshness is not None and freshness.verification_status == "verified" and freshness.last_checked_at is not None
                    and freshness.last_checked_at.tzinfo is not None):
                checked = freshness.last_checked_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                add(rid, "source_freshness", "source_fact",
                    f"The descriptive source for {label} was successfully checked at {checked}. This does not verify every academic condition.", [overview])
        if record.learning_note:
            add(rid, "learning_connection", "recommendation", "Suggested learning connection: " + record.learning_note, [overview])
        if record.first_activity:
            add(rid, "first_activity", "recommendation", "Suggested first activity: " + record.first_activity, [overview])
        phase = context.suggested_phases[rid]
        guidance = {
            "next": f"Consider {label} as a starting learning activity. Confirm any university enrollment requirements before registering.",
            "build": f"Build toward {label} as your preparation develops. This learning stage is not a semester assignment.",
            "later": f"Keep {label} as a later learning goal while developing preparation and checking requirements. This learning stage is not a semester assignment.",
        }
        add(rid, "learning_stage", "recommendation", guidance[phase], [overview])
    return statements


def _statement_map(catalog, context):
    expected = build_statements(catalog, context)
    if expected != context.allowed_statements:
        raise GroundingError("modified_registry", "The explanation statement list changed after context assembly")
    return {s.statement_id: s for s in expected}


def materialize_answer(selection, context, catalog):
    if not isinstance(selection, ExplanationSelection):
        raise GroundingError("unsupported_output", "The provider must return statement selections, not free-form explanations")
    try:
        selection = ExplanationSelection.model_validate(selection.model_dump())
    except ValueError as exc:
        raise GroundingError("invalid_selection", "The provider returned an invalid explanation selection") from exc
    statements = _statement_map(catalog, context)
    if selection.status == "insufficient_evidence":
        return GeneratedAnswer(status="insufficient_evidence", clarification=CLARIFICATIONS[selection.clarification_code])
    used, recommendations = set(), []
    for item in selection.recommendations:
        if item.record_id not in context.allowed_record_ids or item.record_id in used:
            raise GroundingError("invalid_record", "Selected recommendation identities must be unique and allowed")
        used.add(item.record_id)
        if len(item.statement_ids) != len(set(item.statement_ids)):
            raise GroundingError("duplicate_statement", "A recommendation cannot repeat an explanation statement")
        reasons = []
        for statement_id in item.statement_ids:
            statement = statements.get(statement_id)
            if statement is None:
                raise GroundingError("unknown_statement", "The selected explanation statement is not in this context")
            if statement.record_id != item.record_id:
                raise GroundingError("wrong_record", "The selected explanation belongs to another record")
            reasons.append(Reason(text=statement.text, claim_type=statement.claim_type, evidence_ids=statement.evidence_ids))
        recommendations.append(Recommendation(record_id=item.record_id, reasons=reasons))
    return GeneratedAnswer(status="answered", recommendations=recommendations)


def validate_wording(answer, context, catalog):
    statements = _statement_map(catalog, context)
    if answer.status == "answered" and answer.clarification is not None:
        raise GroundingError("unlisted_clarification", "Answered explanations cannot include arbitrary clarification text")
    if answer.status == "insufficient_evidence":
        if answer.clarification not in CLARIFICATIONS.values():
            raise GroundingError("unlisted_clarification", "Clarification wording must come from the application")
        return answer
    allowed = {(s.record_id, s.claim_type, s.text, tuple(s.evidence_ids)) for s in statements.values()}
    for recommendation in answer.recommendations:
        seen = set()
        for reason in recommendation.reasons:
            key = (recommendation.record_id, reason.claim_type, reason.text, tuple(reason.evidence_ids))
            if key not in allowed:
                raise GroundingError("unlisted_wording", "Explanation wording or citations do not match an application-owned statement")
            if key in seen:
                raise GroundingError("duplicate_statement", "A recommendation cannot repeat an explanation statement")
            seen.add(key)
    return answer
