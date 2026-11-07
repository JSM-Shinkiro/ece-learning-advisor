"""Local, independently rerun collection search with on-demand source details."""

import streamlit as st

from .collection_filters import filter_collection
from .source_ui import source_details


def reset_collection_filters():
    st.session_state.update(collection_query="",collection_kind="all",collection_direction="all")


@st.fragment
def render_collection(base_catalog):
    catalog=getattr(st.session_state.get("result"),"catalog",None) or base_catalog
    st.subheader("Courses & resources")
    st.caption("Search the available collection. Learning connections are suggestions; unresolved enrollment rules need review.")
    st.text_input("Search courses and resources",key="collection_query",max_chars=200,
                  placeholder="Course code, title or topic",help="Examples: ECE 372A, machine learning, Python.")
    left,right=st.columns(2)
    kinds={"all":"Courses and resources","course":"Courses only","resource":"Resources only"}
    directions={"all":"All directions","ai_ml":"AI / Machine Learning","embedded":"Embedded Systems"}
    kind=left.selectbox("Type",list(kinds),format_func=kinds.get,key="collection_kind")
    direction=right.selectbox("Direction",list(directions),format_func=directions.get,key="collection_direction")
    records=filter_collection(catalog,st.session_state.get("collection_query",""),kind,direction)
    total=sum(r.kind in {"course","resource"} for r in catalog.records)
    st.caption(f"Showing {len(records)} of {total} courses and resources · local collection search")
    st.button("Reset filters",key="collection_reset",on_click=reset_collection_filters)
    if not records:
        st.info("No courses or resources match these filters. Try a broader search or reset the filters.")
    sources={s.source_id:s for s in catalog.sources}
    for record in records:
        panel=st.expander((record.code+" · " if record.code else "")+record.title,
            key="collection_record_"+record.record_id,on_change="rerun")
        if panel.open:
            with panel:
                st.caption(f"University course · {record.credits:g} credits · Catalog {record.catalog_version}" if record.kind=="course" else
                           "Independent learning resource"+(" · "+record.resource_version if record.resource_version else ""))
                st.write(record.summary)
                source_details(record,"collection_"+record.record_id,sources)
