"""Shared source links and explicit successful-check/snapshot dates."""

from datetime import timedelta,timezone

import streamlit as st


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
        local=timezone(timedelta(hours=-7))
        downloaded=source.retrieved_at.astimezone(local).strftime("%Y-%m-%d %H:%M MST")
        checked=source.last_checked_at.astimezone(local).strftime("%Y-%m-%d %H:%M MST") if source.last_checked_at else None
        st.link_button(source.title,source.url,key=prefix+"_"+sid)
        if source.verification_status=="verified":
            status="Checked "+(checked or downloaded)+" · downloaded "+downloaded
        elif source.verification_status=="stale":
            status="Source check failed · "+("last successful check "+checked if checked else "saved snapshot "+downloaded)
        else:
            status="Saved source snapshot · retrieved "+downloaded
        st.caption(status+" · "+source.review_note)
