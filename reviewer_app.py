"""Local human relevance review. This app never runs retrieval or AI grading."""

import os
from pathlib import Path

import streamlit as st

from src.catalog import ROOT
from src.review_workspace import (GRADE_LABELS, ROLE_LABELS, begin_workspace, complete_review, export_draft,
                                  load_workspace, move_evidence, restore_draft, review_progress, save_current)

st.set_page_config(page_title="ECE Learning Advisor · Evidence review", page_icon="📋", layout="wide")
st.title("Evidence review")
st.caption("Grade the saved excerpts for each question. No relevance grade is selected for you.")

if "review_packet" not in st.session_state:
    try:
        packet = load_workspace(Path(os.environ.get("ECE_REVIEW_PACKET_DIR", ROOT / "data/reviews/runtime_v1")))
        begin_workspace(st.session_state, packet)
    except (OSError, ValueError, TypeError, RecursionError):
        st.error("The review packet could not be loaded. Check the prepared packet and its catalog snapshot.")
        st.stop()


def clear_completed():
    st.session_state.pop("review_completed_json", None)


def restore_uploaded():
    upload = st.session_state.get("review_upload")
    if upload is None:
        return
    try:
        restored = restore_draft(upload.getvalue(), st.session_state.review_packet)
        begin_workspace(st.session_state, st.session_state.review_packet, restored)
        st.session_state.pop("review_error", None)
    except (ValueError, TypeError, RecursionError):
        st.session_state.review_error = "The draft could not be restored. Check its format and packet identity. Your saved ratings are unchanged."


packet, form = st.session_state.review_packet, st.session_state.review_form
revision = st.session_state.review_revision
alias_key, role_key = f"review_alias_{revision}", f"review_role_{revision}"
if alias_key not in st.session_state:
    st.session_state[alias_key] = form.reviewer_id or ""
    st.session_state[role_key] = form.reviewer_role

with st.sidebar:
    st.subheader("Your review")
    alias = st.text_input("Reviewer alias", key=alias_key, max_chars=80, on_change=clear_completed,
                          help="Use letters, numbers, hyphens or underscores. A real name is not needed.")
    role = st.radio("Reviewer role", list(ROLE_LABELS), index=None, format_func=ROLE_LABELS.get,
                    key=role_key, on_change=clear_completed)
    st.caption("Choose Project contributor if you worked on this app. Roles are self-reported and do not verify independence.")
    st.file_uploader("Restore a review draft", type=["json"], max_upload_size=2,
                     key="review_upload", on_change=restore_uploaded)
    st.caption("Save the current grade before downloading. Drafts stay in this session until you download them.")
    try:
        draft = export_draft(form, packet, alias, role)
        st.download_button("Download review draft", draft.model_dump_json(indent=2),
                           file_name="review_draft.json", mime="application/json", on_click="ignore")
    except (ValueError, TypeError):
        st.warning("Use a reviewer alias containing letters, numbers, hyphens or underscores.")
    if st.button("Prepare completed review"):
        clear_completed()
        try:
            completed = complete_review(form, packet, alias, role)
            st.session_state.review_completed_json = completed.model_dump_json(indent=2)
        except (ValueError, TypeError):
            st.warning("Complete all ratings and choose a valid reviewer alias and role before finalizing.")
    if "review_completed_json" in st.session_state:
        st.download_button("Download completed review", st.session_state.review_completed_json,
                           file_name="completed_review.json", mime="application/json", on_click="ignore")

if st.session_state.get("review_error"):
    st.warning(st.session_state.review_error)
saved, total = review_progress(form)
st.progress(saved / total)
st.caption(f"Saved ratings: {saved} of {total}")
st.caption("Review grades measure saved-evidence relevance. Question provenance and reviewer independence are not authenticated; grades do not establish enrollment eligibility.")
st.caption("Declared question origin: " + packet.question_origin.replace("_", " "))
st.selectbox("Question", [q.case_id for q in packet.questions], key="review_question")
question = next(q for q in packet.questions if q.case_id == st.session_state.review_question)
case = next(c for c in form.cases if c.case_id == question.case_id)
position = st.session_state.review_positions[question.case_id]
chunk = next(e for e in packet.evidence if e.chunk_id == question.candidate_ids[position])
st.subheader("Question to judge")
st.text(question.query)
st.caption(f"Evidence {position + 1} of {len(question.candidate_ids)} · saved packet order")
st.text(chunk.chunk_id)
st.text(chunk.text)
with st.expander("Source references"):
    st.caption("Judge the saved excerpt above. Linked pages may have changed since this packet was prepared.")
    for index, source_id in enumerate(chunk.source_ids, 1):
        source = next(s for s in packet.sources if s.source_id == source_id)
        st.text(source.title)
        st.caption("Saved evidence retrieved: " + source.retrieved_at.isoformat())
        st.link_button("Open source " + str(index), source.url)

grade_key = f"review_grade_{revision}_{question.case_id}_{position}"
note_key = f"review_note_{revision}_{question.case_id}"
if grade_key not in st.session_state:
    st.session_state[grade_key] = case.relevance[chunk.chunk_id]
if note_key not in st.session_state:
    st.session_state[note_key] = case.note
with st.form("judgment_form"):
    st.radio("Relevance grade", list(GRADE_LABELS), index=None, format_func=GRADE_LABELS.get, key=grade_key)
    st.text_area("Question note (optional)", key=note_key, max_chars=2000)
    st.form_submit_button("Save grade and next", type="primary", on_click=save_current,
                          args=(st.session_state, grade_key, note_key, question.case_id, chunk.chunk_id))
previous, following, clear = st.columns(3)
previous.button("Previous evidence", disabled=position == 0, on_click=move_evidence, args=(st.session_state, -1))
following.button("Next evidence", disabled=position + 1 == len(question.candidate_ids),
                 on_click=move_evidence, args=(st.session_state, 1))
clear.button("Clear this grade", on_click=save_current,
             args=(st.session_state, grade_key, note_key, question.case_id, chunk.chunk_id), kwargs={"clear": True})
