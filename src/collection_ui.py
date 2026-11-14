"""Local, independently rerun collection search with on-demand source details."""

import streamlit as st

from .career_paths import CAREER_PATHS
from .career_ui import elective_details
from .collection_filters import filter_collection
from .directory_ui import render_directory
from .source_ui import enrollment_details, source_details


def reset_collection_filters():
    st.session_state.update(collection_query="",collection_kind="all",collection_direction="all")


@st.fragment
def render_collection(catalog, directory=None, references=None):
    st.subheader("Courses & resources")
    if directory is not None:
        scope = st.radio("Browse collection", ["advisor", "ece"],
            format_func=lambda key:"Advisor courses & resources" if key=="advisor" else "All undergraduate ECE courses",
            key="collection_scope", horizontal=True)
        if scope == "ece":
            render_directory(directory, references)
            return
    st.caption("Search the available collection. Learning connections are suggestions; unresolved enrollment rules need review.")
    st.text_input("Search courses and resources",key="collection_query",max_chars=200,
                  placeholder="Course code, title or topic",help="Examples: ECE 372A, machine learning, Python.")
    left,right=st.columns(2)
    kinds={"all":"Courses and resources","course":"Courses only","resource":"Resources only"}
    directions = {"all": "All directions", **{key: path.name for key, path in CAREER_PATHS.items()}}
    kind=left.selectbox("Type",list(kinds),format_func=kinds.get,key="collection_kind")
    direction=right.selectbox("Direction",list(directions),format_func=directions.get,key="collection_direction")
    records=filter_collection(catalog,st.session_state.get("collection_query",""),kind,direction)
    total=sum(r.kind in {"course","resource"} for r in catalog.records)
    st.caption(f"Showing {len(records)} of {total} courses and resources · local collection search")
    st.button("Reset filters",key="collection_reset",on_click=reset_collection_filters)
    if not records:
        st.info("No courses or resources match these filters. Try a broader search or reset the filters.")
    sources={s.source_id:s for s in catalog.sources}
    elective_codes = {path.elective for path in CAREER_PATHS.values() if path.elective}
    for record in records:
        panel=st.expander((record.code+" · " if record.code else "")+record.title,
            key="collection_record_"+record.record_id,on_change="rerun")
        if panel.open:
            with panel:
                credits = f"{record.credits:g} credits" if record.credits is not None else "Variable credits · see source"
                st.caption(f"University course · {credits} · Catalog {record.catalog_version}" if record.kind=="course" else
                           "Independent learning resource"+(" · "+record.resource_version if record.resource_version else ""))
                st.write(record.summary)
                if record.code in elective_codes:
                    st.markdown("**Outside-ECE elective candidate**")
                    st.write(record.learning_note)
                    elective_details("collection_elective_" + record.code)
                source_details(record,"collection_"+record.record_id,sources)
                if record.kind == "course" and not record.rule_reviewed:
                    enrollment_details(record.code, sources[record.source_ids[0]].url, record.requirement_reference,
                                       record.catalog_version, references, key="collection_enrollment_"+record.record_id)
