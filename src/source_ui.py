"""Shared source links and explicit successful-check/snapshot dates."""

from datetime import timedelta, timezone

import streamlit as st

from .enrollment_references import ADVISED_PLAN, DEPARTMENT_COURSES, PUBLIC_CLASS_SEARCH

ARIZONA = timezone(timedelta(hours=-7))


def enrollment_details(code, course_url, requirement_reference, catalog_version, references, *, key):
    reference = (references.for_course(code, course_url, requirement_reference, catalog_version)
                 if references is not None else None)
    if reference is not None:
        st.markdown("**Enrollment references**")
        st.caption(f"Reviewed {references.reviewed_on.isoformat()} alongside the {catalog_version} catalog.")
        st.write(reference.department_summary)
        st.link_button("Department course page", DEPARTMENT_COURSES + code, key=key + "_department")
        if reference.plan_summary:
            st.write(reference.plan_summary)
            st.link_button("2026–27 advised degree plan", ADVISED_PLAN + "#page=1", key=key + "_plan")
    st.caption(f"Choose the term and search for {code} to confirm the section’s enrollment requirements.")
    st.link_button("Open class search", PUBLIC_CLASS_SEARCH, key=key + "_class_search")


def roadmap_expander(label, *, key):
    """Keep the open preference when an intermediate plan omits the panel."""
    st.session_state.setdefault(key, key in st.session_state.get("roadmap_open_panels", ()))
    panel = st.expander(label, key=key, on_change="rerun")
    panels = st.session_state.setdefault("roadmap_open_panels", set())
    if panel.open:
        panels.add(key)
    else:
        panels.discard(key)
    return panel


def source_details(record,prefix,sources):
    for sid in record.source_ids:
        source=sources[sid]
        downloaded=source.retrieved_at.astimezone(ARIZONA).strftime("%Y-%m-%d %H:%M MST")
        checked=source.last_checked_at.astimezone(ARIZONA).strftime("%Y-%m-%d %H:%M MST") if source.last_checked_at else None
        st.link_button(source.title,source.url,key=prefix+"_"+sid)
        if source.verification_status=="verified":
            status="Checked "+(checked or downloaded)+" · downloaded "+downloaded
        elif source.verification_status=="stale":
            status="Source check failed · "+("last successful check "+checked if checked else "saved snapshot "+downloaded)
        else:
            status="Saved source snapshot · retrieved "+downloaded
        st.caption(status+" · "+source.review_note)
