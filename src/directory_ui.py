"""Paged, local browsing of the full published undergraduate ECE inventory."""

import math

import streamlit as st

from .course_directory import filter_directory
from .profiles import edit_profile
from .session import apply_profile
from .source_ui import ARIZONA, enrollment_details

PAGE_SIZE = 15


def reset_directory_page():
    st.session_state.directory_page = 0


def change_directory_page(offset):
    st.session_state.directory_page += offset


def render_directory(directory, references):
    st.caption(f"{len(directory.courses)} published undergraduate ECE courses · Catalog {directory.catalog_version}")
    start_date, end_date = directory.effective_dates.split(",")
    filter_date = start_date if start_date == end_date else f"{start_date} to {end_date}"
    retrieved = directory.retrieved_at.astimezone(ARIZONA).strftime("%Y-%m-%d %H:%M MST")
    st.caption(f"Effective-date filter {filter_date} · snapshot retrieved {retrieved}")
    st.text_input("Search the ECE catalog", key="directory_query", max_chars=200,
                  placeholder="ECE 413, circuits, optics...", on_change=reset_directory_page)
    labels = {"all":"All levels", "1":"100 level", "2":"200 level", "3":"300 level", "4":"400 level"}
    level = st.selectbox("Course level", list(labels), format_func=labels.get,
                         key="directory_level", on_change=reset_directory_page)
    courses = filter_directory(directory, st.session_state.get("directory_query", ""), level)
    pages = max(1, math.ceil(len(courses) / PAGE_SIZE))
    page = min(st.session_state.get("directory_page", 0), pages-1)
    st.session_state.directory_page = page
    start = page * PAGE_SIZE
    st.caption(f"{len(courses)} matching courses · Page {page+1} of {pages} · local catalog search")
    previous, following = st.columns(2)
    previous.button("Previous courses", key="directory_previous", disabled=page==0,
                    on_click=change_directory_page, args=(-1,))
    following.button("Next courses", key="directory_next", disabled=page+1>=pages,
                     on_click=change_directory_page, args=(1,))
    if not courses:
        st.info("No ECE courses match. Try another course code or a broader topic.")
    profile = st.session_state.profile
    recorded = {c.course_code for c in profile.completed} | set(profile.current_enrollment)
    for course in courses[start:start+PAGE_SIZE]:
        panel = st.expander(course.code+" · "+course.title, key="directory_record_"+course.code, on_change="rerun")
        if panel.open:
            with panel:
                st.caption(course.credits_label+" · Catalog "+directory.catalog_version)
                st.write(course.summary)
                st.caption(f"Catalog record effective from {course.effective_start} · enrollment requirements unverified")
                st.link_button("Official course page", course.url, key="directory_source_"+course.code)
                enrollment_details(course.code, course.url, course.requirement_reference,
                                   directory.catalog_version, references, key="directory_enrollment_"+course.code)
                disabled = course.code in recorded or profile.catalog_version != directory.catalog_version
                if st.button("Explore "+course.code+" in my roadmap", key="directory_ask_"+course.code,
                    disabled=disabled, help="Uses your saved profile and AI settings. Enrollment and preparation remain unverified."):
                    apply_profile(st.session_state, edit_profile(profile, question="What can I learn in "+course.code+"?"))
                    st.rerun()
