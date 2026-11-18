"""Career cards and citations for college and department elective guidance."""

import streamlit as st

from .career_paths import CAREER_PATHS, ELECTIVE_GUIDANCE, ELECTIVE_RULE
from .enrollment_references import ADVISED_PLAN
from .session import choose_direction
from .source_ui import roadmap_expander, source_details


def direction_cards():
    st.subheader("Choose a direction to explore")
    paths = list(CAREER_PATHS.items())
    for offset in range(0, len(paths), 2):
        row = paths[offset:offset + 2]
        for column, (key, path) in zip(st.columns(len(row)), row):
            with column, st.container(border=True):
                st.markdown("**" + path.name + "**")
                st.write(path.roles)
                st.caption(" · ".join(route.label for route in path.routes))
                st.button("Explore " + path.name, key="choose_" + key, width="stretch",
                          on_click=choose_direction, args=(st.session_state, key))


def elective_details(key):
    st.write(ELECTIVE_GUIDANCE)
    st.link_button("Official ECE technical elective requirements", ELECTIVE_RULE, key=key + "_rules")
    st.link_button("2026–27 advised degree plan", ADVISED_PLAN, key=key + "_plan")


def render_career_path(result, catalog):
    direction = result.context.profile.career_id
    path = CAREER_PATHS.get(direction)
    if path is None:
        return
    electives = {r.code: r for r in catalog.records if r.code in path.electives}
    career = next((r for r in catalog.records if r.record_id == "career:" + direction), None)
    if career is None:
        return
    if result.trace.get("career_direction"):
        st.caption("Direction matched from your question · " + path.name)
        st.button("Use this direction", key="save_matched_direction", on_click=choose_direction,
                  args=(st.session_state, direction, result.context.question))
    sources = {source.source_id: source for source in catalog.sources}
    st.caption(path.roles)
    active_route = result.trace.get("study_route")
    if active_route:
        st.caption("Specialization · " + active_route)
        selected_route = next(route for route in path.routes if route.label == active_route)
        st.write("**First practice** · " + selected_route.practice)
        for alternative in path.routes:
            for index, (selected_code, alternative_code) in enumerate(zip(selected_route.courses, alternative.courses)):
                if selected_code != alternative_code:
                    if index:
                        prior = selected_route.courses[index - 1]
                        st.caption(f"After {prior}, this route explores {selected_code}. "
                                   f"{alternative.label} explores {alternative_code}.")
                    break
    plural = "s" if len(electives) > 1 else ""
    title = "Career path and elective" + plural if electives else "Career path and study routes"
    panel = roadmap_expander(title, key="career_details_" + direction)
    if panel.open:
        with panel:
            st.caption("Example study routes · Catalog " + catalog.catalog_version)
            for index, route in enumerate(path.routes):
                st.write(f"**{route.label}** · " + " → ".join(route.courses))
                st.caption("Practice · " + route.practice)
                st.button("Explore " + route.label, key=f"choose_route_{direction}_{index}",
                          on_click=choose_direction,
                          args=(st.session_state, direction, route.starting_question))
            if path.application:
                st.write(path.application)
            source_details(career, direction, sources)
            if electives:
                st.markdown("**Outside-ECE elective candidate" + plural + "**")
                for code in path.electives:
                    elective = electives.get(code)
                    if elective is not None:
                        st.link_button(code + " · " + elective.title, sources[elective.source_ids[0]].url,
                                       key="career_elective_" + code)
                        st.write(elective.learning_note)
                elective_details("career_elective_" + direction)
