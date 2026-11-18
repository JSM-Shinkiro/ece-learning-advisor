"""Shared source links and explicit successful-check/snapshot dates."""

from datetime import timedelta, timezone

import streamlit as st

from .catalog import code_lookup
from .enrollment_references import ADVISED_PLAN, DEPARTMENT_COURSES, PUBLIC_CLASS_SEARCH

ARIZONA = timezone(timedelta(hours=-7))


def enrollment_details(code, course_url, requirement_reference, catalog_version, references, *, key,
                       show_class_search=True):
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
    if reference and reference.adviser_question:
        st.write("**Ask ECE advising**")
        st.write(reference.adviser_question)
    else:
        st.caption(f"Ask advising which prerequisites and restrictions apply to your {code} section.")
    st.caption(f"Choose the term and search for {code} to confirm the section’s enrollment requirements.")
    if show_class_search:
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


def source_status(source):
    downloaded = source.retrieved_at.astimezone(ARIZONA).strftime("%Y-%m-%d %H:%M MST")
    checked = (source.last_checked_at.astimezone(ARIZONA).strftime("%Y-%m-%d %H:%M MST")
               if source.last_checked_at else None)
    if source.verification_status == "verified":
        return "Checked " + (checked or downloaded) + " · downloaded " + downloaded
    if source.verification_status == "stale":
        return "Source check failed · " + ("last successful check " + checked if checked else "saved snapshot " + downloaded)
    return "Saved source snapshot · retrieved " + downloaded


def source_details(record, prefix, sources):
    for sid in record.source_ids:
        source = sources[sid]
        st.link_button(source.title, source.url, key=prefix + "_" + sid)
        st.caption(source_status(source) + " · " + source.review_note)


def published_courses(codes, catalog, directory):
    """Show named course descriptions independently of career fit or prerequisites."""
    sources = {s.source_id: s for s in catalog.sources}
    reviewed = code_lookup(catalog)
    directory_courses = {c.code: c for c in directory.courses} if directory is not None else {}
    available = [code for code in codes if code in reviewed or code in directory_courses]
    if not available:
        return
    st.subheader("Published course information")
    for code in available:
        record = reviewed.get(code)
        with st.container(border=True):
            if record:
                source = sources[record.source_ids[0]]
                title, summary, url, version = record.title, record.summary, source.url, record.catalog_version
                freshness = source_status(source)
            else:
                course = directory_courses[code]
                title, summary, url, version = course.title, course.summary, course.url, directory.catalog_version
                freshness = "Saved directory snapshot · retrieved " + directory.retrieved_at.astimezone(ARIZONA).strftime("%Y-%m-%d")
            st.markdown(f"**{code} · {title}**")
            st.caption(f"Catalog {version} · {freshness}")
            st.write(summary)
            st.link_button("Official course page", url, key="requested_course_source_" + code)
