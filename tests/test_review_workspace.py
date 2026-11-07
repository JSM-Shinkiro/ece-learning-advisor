"""Partial human-review integrity and completed-form compatibility; fixtures are not judgments."""

from datetime import datetime, timedelta, timezone
import json

import pytest

from src.review import MAX_REVIEW_BYTES, blank_form, make_packet, score_review
from src.review_workspace import (begin_workspace, complete_review, export_draft, load_workspace, restore_draft,
                                  review_progress, save_current, save_judgment)

NOW = datetime(2026, 11, 5, 23, tzinfo=timezone.utc)


@pytest.fixture
def packet(catalog):
    return make_packet(catalog, packet_id="workspace-fixture", now=NOW,
                       questions=[{"case_id": "q1", "query": "How do microcontrollers use interrupts?"}])


def test_saved_workspace_loads_exact_bound_inputs_without_ranking(catalog, packet, tmp_path, monkeypatch):
    monkeypatch.setattr("src.review.Retriever", lambda *a, **k: pytest.fail("The workspace must not rank evidence"))
    (tmp_path / "packet.json").write_text(packet.model_dump_json())
    snapshot = tmp_path / "catalog_snapshot.json"
    snapshot.write_text(catalog.model_dump_json())
    assert load_workspace(tmp_path) == packet
    changed = catalog.model_copy(deep=True)
    changed.records[0].summary += " changed"
    snapshot.write_text(changed.model_dump_json())
    with pytest.raises(ValueError): load_workspace(tmp_path)


def test_explicit_zero_grade_roundtrips_as_one_rating_without_mutating_the_blank(packet):
    blank = blank_form(packet)
    chunk = packet.questions[0].candidate_ids[0]
    updated = save_judgment(blank, packet, "q1", chunk, 0, "Saved evidence note")
    assert review_progress(updated) == (1, 10)
    assert blank.cases[0].relevance[chunk] is None
    restored = restore_draft(updated.model_dump_json().encode(), packet)
    assert restored == updated and restored.reviewed_at is None


@pytest.mark.parametrize("change", ["packet", "missing_case", "duplicate_case", "missing_chunk", "extra_chunk", "bool_grade"])
def test_restored_drafts_require_exact_case_and_chunk_binding(packet, change):
    data = blank_form(packet).model_dump(mode="json")
    if change == "packet": data["packet_hash"] = "0" * 64
    elif change == "missing_case": data["cases"] = []
    elif change == "duplicate_case": data["cases"].append(dict(data["cases"][0]))
    elif change == "missing_chunk": data["cases"][0]["relevance"].pop(packet.questions[0].candidate_ids[0])
    elif change == "extra_chunk": data["cases"][0]["relevance"]["foreign-chunk"] = None
    else: data["cases"][0]["relevance"][packet.questions[0].candidate_ids[0]] = True
    with pytest.raises(ValueError): restore_draft(json.dumps(data).encode(), packet)


@pytest.mark.parametrize("raw", [b'{"packet_hash":"one","packet_hash":"two"}', b'\xff', b' ' * (MAX_REVIEW_BYTES + 1)])
def test_uploaded_review_bytes_are_bounded_and_duplicate_key_checked(packet, raw):
    with pytest.raises(ValueError): restore_draft(raw, packet)


def test_partial_or_unidentified_forms_cannot_be_exported_as_completed(catalog, packet):
    form = blank_form(packet)
    with pytest.raises(ValueError): complete_review(form, packet, "fixture", "controlled_fixture")
    for chunk in packet.questions[0].candidate_ids:
        form = save_judgment(form, packet, "q1", chunk, 0, "Controlled fixture only")
    with pytest.raises(ValueError): complete_review(form, packet, "", None)
    completed = complete_review(form, packet, "fixture", "controlled_fixture", now=NOW + timedelta(hours=1))
    report = score_review(catalog, packet, completed)
    assert report["reviewer"]["self_reported_role"] == "controlled_fixture"
    assert report["embedding_calls"] == report["generation_calls"] == report["source_refresh_calls"] == 0
    edited = save_judgment(completed, packet, "q1", packet.questions[0].candidate_ids[0], None, "Changed")
    assert edited.reviewed_at is None and review_progress(edited) == (9, 10)
    with pytest.raises(ValueError): complete_review(edited, packet, "fixture", "controlled_fixture")


def test_completed_timestamps_and_identity_are_not_inferred_for_drafts(packet):
    draft = export_draft(blank_form(packet), packet, "  fixture  ", "controlled_fixture")
    assert draft.reviewer_id == "fixture" and draft.reviewed_at is None
    data = draft.model_dump(mode="json")
    data["reviewed_at"] = (NOW + timedelta(hours=1)).isoformat()
    with pytest.raises(ValueError): restore_draft(json.dumps(data).encode(), packet)


def test_save_requires_a_choice_and_rejects_a_stale_double_click(packet):
    state = {}
    begin_workspace(state, packet)
    chunk = packet.questions[0].candidate_ids[0]
    save_current(state, "grade", "note", "q1", chunk)
    assert review_progress(state["review_form"]) == (0, 10)
    state["grade"] = 0
    save_current(state, "grade", "note", "q1", chunk)
    assert review_progress(state["review_form"]) == (1, 10)
    save_current(state, "grade", "note", "q1", chunk)
    assert review_progress(state["review_form"]) == (1, 10)
    assert "evidence changed" in state["review_error"]


def test_clear_keeps_live_reviewer_fields_and_explicitly_resets_the_grade(packet):
    state = {}
    begin_workspace(state, packet)
    state.update(grade=3, note="Question note", review_alias_1="fixture", review_role_1="controlled_fixture")
    chunk = packet.questions[0].candidate_ids[0]
    save_current(state, "grade", "note", "q1", chunk)
    state["review_positions"]["q1"] = 0
    save_current(state, "grade", "note", "q1", chunk, clear=True)
    assert state["grade"] is None and review_progress(state["review_form"]) == (0, 10)
    assert state["review_alias_1"] == "fixture" and state["review_role_1"] == "controlled_fixture"
    assert state["review_revision"] == 1


def test_question_advance_never_copies_the_previous_grade(catalog):
    packet = make_packet(catalog, now=NOW, questions=[{"case_id": "q1", "query": "microcontrollers"},
                                                   {"case_id": "q2", "query": "programming foundations"}])
    state = {}
    begin_workspace(state, packet)
    state["review_positions"]["q1"] = 9
    state.update(grade=2, note="First question")
    save_current(state, "grade", "note", "q1", packet.questions[0].candidate_ids[9])
    assert state["review_question"] == "q2" and state["review_positions"]["q2"] == 0
    assert all(value is None for value in state["review_form"].cases[1].relevance.values())
