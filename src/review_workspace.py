"""Offline human-review drafts; no rankings, inferred labels, or disk writes."""

from datetime import datetime, timezone
from pathlib import Path

from .review import (ReviewForm, ReviewPacket, blank_form, load_catalog_snapshot, load_review_json,
                     parse_review_json, validate_packet, validate_review)

GRADE_LABELS = {0: "0 · Unrelated", 1: "1 · Background", 2: "2 · Useful support", 3: "3 · Direct evidence"}
ROLE_LABELS = {"independent_reviewer": "Independent reviewer", "project_contributor": "Project contributor",
               "controlled_fixture": "Controlled fixture (testing only)"}


def load_workspace(directory):
    directory = Path(directory)
    catalog = load_catalog_snapshot(directory / "catalog_snapshot.json")
    packet = validate_packet(ReviewPacket.model_validate(load_review_json(directory / "packet.json")), catalog)
    return packet


def validate_draft(form, packet):
    form = ReviewForm.model_validate(form.model_dump(warnings=False))
    if form.packet_hash != packet.packet_hash:
        raise ValueError("Draft belongs to a different packet")
    expected = {question.case_id for question in packet.questions}
    ids = [case.case_id for case in form.cases]
    if len(ids) != len(expected) or set(ids) != expected:
        raise ValueError("Draft must include every question exactly once")
    chunks = {chunk.chunk_id for chunk in packet.evidence}
    if any(set(case.relevance) != chunks for case in form.cases):
        raise ValueError("Draft must include every evidence chunk for every question")
    if form.reviewed_at is not None:
        validate_review(form, packet)
    return form


def restore_draft(raw, packet):
    return validate_draft(ReviewForm.model_validate(parse_review_json(raw)), packet)


def save_judgment(form, packet, case_id, chunk_id, grade, note):
    updated = validate_draft(form, packet).model_copy(deep=True)
    case = next((case for case in updated.cases if case.case_id == case_id), None)
    if case is None or chunk_id not in case.relevance:
        raise ValueError("Choose a question and evidence chunk in this packet")
    case.relevance[chunk_id], case.note = grade, note
    updated.reviewed_at = None
    return validate_draft(updated, packet)


def review_progress(form):
    total = sum(len(case.relevance) for case in form.cases)
    saved = sum(grade is not None for case in form.cases for grade in case.relevance.values())
    return saved, total


def export_draft(form, packet, reviewer_id, reviewer_role):
    data = form.model_dump()
    data.update(reviewer_id=reviewer_id.strip() or None, reviewer_role=reviewer_role, reviewed_at=None)
    return validate_draft(ReviewForm.model_validate(data), packet)


def complete_review(form, packet, reviewer_id, reviewer_role, *, now=None):
    result = export_draft(form, packet, reviewer_id, reviewer_role)
    result.reviewed_at = now or datetime.now(timezone.utc)
    return validate_review(result, packet)


def begin_workspace(state, packet, form=None):
    form = blank_form(packet) if form is None else validate_draft(form, packet)
    state["review_packet"], state["review_form"] = packet, form
    state["review_revision"] = state.get("review_revision", 0) + 1
    state["review_positions"] = {question.case_id: 0 for question in packet.questions}
    state["review_question"] = packet.questions[0].case_id
    state.pop("review_completed_json", None)


def save_current(state, grade_key, note_key, case_id, chunk_id, *, clear=False):
    packet, form = state["review_packet"], state["review_form"]
    question = next(q for q in packet.questions if q.case_id == case_id)
    position = state["review_positions"][case_id]
    if state["review_question"] != case_id or question.candidate_ids[position] != chunk_id:
        state["review_error"] = "The selected evidence changed. Review the displayed excerpt before saving."
        return
    grade = None if clear else state.get(grade_key)
    if grade is None and not clear:
        state["review_error"] = "Choose a relevance grade before saving."
        return
    try:
        updated = save_judgment(form, packet, case_id, chunk_id, grade, state.get(note_key, ""))
    except (ValueError, TypeError):
        state["review_error"] = "The grade or note could not be saved. Check the selected evidence and note length."
        return
    state["review_form"] = updated
    state.pop("review_error", None)
    state.pop("review_completed_json", None)
    if clear:
        state[grade_key] = None
        return
    if position + 1 < len(question.candidate_ids):
        state["review_positions"][case_id] += 1
    else:
        index = next(i for i, q in enumerate(packet.questions) if q.case_id == case_id)
        if index + 1 < len(packet.questions):
            state["review_question"] = packet.questions[index + 1].case_id


def move_evidence(state, offset):
    question = next(q for q in state["review_packet"].questions if q.case_id == state["review_question"])
    positions = state["review_positions"]
    positions[question.case_id] = max(0, min(len(question.candidate_ids) - 1, positions[question.case_id] + offset))
