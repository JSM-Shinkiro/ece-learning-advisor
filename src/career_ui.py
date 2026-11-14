"""Career cards and citations for college and department elective guidance."""

import streamlit as st

from .career_paths import CAREER_PATHS, ELECTIVE_GUIDANCE, ELECTIVE_RULE
from .enrollment_references import ADVISED_PLAN
from .session import choose_direction
from .source_ui import roadmap_expander, source_details


def direction_cards(course_lookup):
    st.subheader("Choose a direction to explore")
    for row in (("ai_ml", "embedded"), ("signals", "controls")):
        for column, key in zip(st.columns(2), row):
            path = CAREER_PATHS[key]
            with column, st.container(border=True):
                st.markdown("**" + path.name + "**")
                st.write(path.roles)
                progression = " → ".join(code for code in path.progression if code in course_lookup)
                if progression:
                    st.caption("Example course progression · " + progression)
                st.button("Explore " + path.name, key="choose_" + key, width="stretch",
                          on_click=choose_direction, args=(st.session_state, key))


def elective_details(key):
    st.write(ELECTIVE_GUIDANCE)
    st.link_button("Official ECE technical elective requirements", ELECTIVE_RULE, key=key + "_rules")
    st.link_button("2026–27 advised degree plan", ADVISED_PLAN, key=key + "_plan")


def render_career_path(result, catalog):
    direction = result.context.profile.career_id
    path = CAREER_PATHS.get(direction)
    if path is None or not path.elective:
        return
    elective = next((r for r in catalog.records if r.code == path.elective), None)
    career = next((r for r in catalog.records if r.record_id == "career:" + direction), None)
    if elective is None or career is None:
        return
    if result.trace.get("career_direction"):
        st.caption("Direction matched from your question · " + path.name)
        st.button("Use this direction", key="save_matched_direction", on_click=choose_direction,
                  args=(st.session_state, direction, result.context.question))
    sources = {source.source_id: source for source in catalog.sources}
    st.caption(path.roles)
    panel = roadmap_expander("Career path and elective", key="career_details_" + direction)
    if panel.open:
        with panel:
            st.caption("Example course progression · Catalog " + catalog.catalog_version
                       + " · " + " → ".join(path.progression))
            st.write(path.application)
            st.write("**Practice project** · " + path.project)
            source_details(career, direction, sources)
            st.markdown("**Outside-ECE elective candidate**")
            st.link_button(elective.code + " · " + elective.title, sources[elective.source_ids[0]].url,
                           key="career_elective_" + direction)
            st.write(elective.learning_note)
            elective_details("career_elective_" + direction)
