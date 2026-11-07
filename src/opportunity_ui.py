"""Opportunity controls rerun independently; detail work runs beside its listing."""

import streamlit as st

from . import jobs as jobs_api, opportunities, opportunity_details as details, opportunity_pages as pages
from .planning import CAREER_NAMES
from .posting_actions import queue_posting_detail,take_posting_detail


def check_selected_posting(posting_id,displayed_result):
    queue_posting_detail(st.session_state,posting_id,displayed_result)


def change_opportunity_page(page):
    try:
        pages.request_opportunity_page(st.session_state,page)
    except (ValueError,OSError):
        st.session_state["job_page_error"]="This saved search page could not be opened. Run a new search."


@st.fragment
def render_opportunities(settings):
    profile=st.session_state.profile
    st.subheader("Explore opportunities")
    st.caption("Direction: "+CAREER_NAMES[profile.career_id]+" · uses your saved profile")
    configured = settings.adzuna_configured
    provider_names = {"greenhouse": "Employer boards", "adzuna": "Adzuna location search"}
    provider = st.selectbox("Opportunity source", ["greenhouse", "adzuna"] if configured else ["greenhouse"],
                            format_func=provider_names.get, key="opportunity_provider")
    board_available = True
    if provider == "greenhouse":
        try:
            employer_names = ", ".join(b.employer for b in opportunities.load_employer_boards())
            st.caption("Searches the configured employer boards: " + employer_names + ".")
        except (OSError, ValueError):
            board_available = False
            st.warning("The employer-board connection is unavailable.")
        st.caption("Matches title keywords for your direction. Location filters match the employer's wording; leave blank to include all listed locations.")
    if profile.career_id=="exploring":
        st.info("Choose AI/ML or Embedded Systems in your roadmap before searching for relevant opportunities.")
    with st.form("jobs_form"):
        location = st.text_input("Location contains (optional)" if provider == "greenhouse" else "Location",
                                 value="" if provider == "greenhouse" else "Tucson, AZ", max_chars=120, key="opportunity_location_" + provider)
        if provider == "greenhouse":
            role_labels = {"all": "All levels", "internship": "Internship / co-op", "early_career": "New grad / entry-level"}
            role_filter = st.selectbox("Role titles", list(role_labels), format_func=role_labels.get,
                help="Filters explicit title words. New-grad/entry-level excludes internship and senior/leadership titles; requirements still need review.", key="opportunity_role_titles")
            internship, early_career = role_filter == "internship", role_filter == "early_career"
        else:
            internship = st.checkbox("Prefer internship search terms", help="Changes the search phrase; provider listings may include other roles.",
                key="opportunity_internship_adzuna")
            early_career = False
        updated_within = st.selectbox("Listing updated within", [None, 7, 30, 90],
            format_func=lambda days: "Any date" if days is None else str(days) + " days",
            key="opportunity_age", disabled=provider != "greenhouse")
        reuse = st.checkbox("Reuse matching results from the last 20 minutes", value=False, key="reuse_opportunities")
        requested = st.form_submit_button("Available Opportunities",disabled=profile.career_id=="exploring" or not board_available)
    if requested and profile.career_id!="exploring":
        try:
            with st.spinner("Searching opportunities..."):
                opportunities.request_opportunities(st.session_state, profile.career_id, location, internship, provider=provider,
                    updated_within=updated_within if provider == "greenhouse" else None, reuse=reuse,
                    early_career=early_career,
                    public_search=opportunities.search_employer_jobs, adzuna_search=jobs_api.search_jobs,
                    app_id=settings.adzuna_app_id.get_secret_value(), app_key=settings.adzuna_app_key.get_secret_value())
        except (ValueError,RuntimeError):
            st.warning("The provider could not complete this search. Try again later.")
    jobs = st.session_state.get("job_result")
    job_error = st.session_state.get("job_error")
    pending = take_posting_detail(st.session_state)
    if jobs is None or jobs.provider != provider:
        pending = None
    if not jobs and job_error and job_error["provider"] == provider:
        with st.expander("Last search source checks"):
            st.dataframe(job_error["checks"], hide_index=True)
    if jobs and jobs.provider == provider:
        st.caption(f"Source: {provider_names[jobs.provider]} · Query: {jobs.query} · Location: {jobs.location} · Retrieved: {jobs.retrieved_at}")
        if provider == "greenhouse":
            st.caption("Results title filter: " + role_labels.get(jobs.role_filter, "All levels") + ".")
        st.caption("Reused recent results; sources were not checked again." if jobs.cache_state == "reused" else "Sources requested for this search.")
        if st.session_state.get("job_page_error"):
            st.warning(st.session_state["job_page_error"])
        for issue in jobs.issues:
            st.warning(issue)
        if not jobs.listings:
            st.info("No listings were returned for these filters.")
        elif jobs.total_matches is not None:
            pagination = pages.page_info(jobs)
            if pagination:
                st.caption(f"Showing {pagination.first}–{pagination.last} of {pagination.total_matches} matching listings, sorted by last update.")
                if pagination.truncated:
                    st.info(f"This search retains the first {pagination.retained} matches. Narrow the filters to find more specific results.")
                if pagination.pages > 1:
                    st.caption(f"Page {pagination.number} of {pagination.pages} · Saved search results; paging does not check sources again.")
                    previous, following = st.columns(2)
                    previous.button("Previous listings", key="opportunity_previous", disabled=jobs.page == 0,
                        on_click=change_opportunity_page, args=(jobs.page - 1,))
                    following.button("Next listings", key="opportunity_next", disabled=pagination.number == pagination.pages,
                        on_click=change_opportunity_page, args=(jobs.page + 1,))
            else:
                st.caption(f"Showing {len(jobs.listings)} of {jobs.total_matches} matching listings, sorted by last update.")
        for job in jobs.listings:
            with st.container(border=True):
                st.text(job["title"])
                st.text(job["employer"]+" · "+job["location"])
                if job["posted_at"]:
                    st.caption("Provider posting date: "+str(job["posted_at"]))
                if job.get("updated_at"):
                    st.caption("Provider last update: "+job["updated_at"])
                if job["description_snippet"]:
                    st.text(job["description_snippet"][:700])
                if job.get("matched_terms"):
                    st.caption("Title matches: " + ", ".join(job["matched_terms"]))
                st.link_button("View original opportunity",job["url"])
                if provider == "greenhouse":
                    st.button("Check posting details", key="job_detail_" + job["id"],
                        on_click=check_selected_posting, args=(job["id"],jobs))
                    if pending is not None and pending.posting_id == job["id"]:
                        with st.spinner("Checking posting details..."):
                            try:
                                details.request_posting_detail(st.session_state,job["id"],fetcher=details.fetch_posting_detail)
                            except (ValueError,RuntimeError,OSError):
                                if st.session_state.get("job_result") is jobs:
                                    st.session_state["job_detail_error"] = job["id"]
                    if st.session_state.get("job_detail_error") == job["id"]:
                        st.warning("This posting could not be checked. Run a new search and try again.")
                    detail = st.session_state.get("job_detail")
                    if detail and detail.posting_id == job["id"]:
                        st.caption(f"Posting check: {len(detail.attempts)} HTTP attempt(s) · {detail.retry_count} retry · {detail.transport_seconds:.2f}s transport")
                        if detail.attempts:
                            with st.expander("Posting request attempts"):
                                st.dataframe([a.model_dump() for a in detail.attempts], hide_index=True)
                        if detail.status == "verified" and detail.posting:
                            st.caption("Posting details checked: " + detail.checked_at.isoformat())
                            if detail.changed_fields:
                                st.info("Posting information changed since this search: " + ", ".join(detail.changed_fields)
                                    + ". Search filters have not been rerun; review the checked posting below.")
                            with st.expander("Checked posting description", expanded=True):
                                st.text(detail.posting.title)
                                st.text(detail.posting.employer + " · " + detail.posting.location)
                                if detail.posting.posted_at:
                                    st.caption("Checked posting's publication date: " + detail.posting.posted_at)
                                if detail.posting.updated_at:
                                    st.caption("Checked posting's provider update: " + detail.posting.updated_at)
                                st.text(detail.posting.description)
                                if detail.posting.truncated:
                                    st.warning("This description is shortened. Open the original for the complete posting.")
                                st.link_button("Open checked posting", detail.posting.url)
                        else:
                            messages = {"not_listed": "This posting was not found at the source. Run a new search or check the employer's careers page.",
                                "unavailable": "This posting could not be reached. Its requirements have not been checked.",
                                "invalid_response": "The returned posting could not be validated. Its requirements have not been checked."}
                            st.warning(messages[detail.status])
                            st.caption("Posting check attempted: " + detail.requested_at.isoformat()
                                + (" · HTTP " + str(detail.http_status) if detail.http_status else ""))
        if jobs.checks:
            with st.expander("Opportunity source checks"):
                st.dataframe([{k: v for k, v in check.items() if k != "attempts"} for check in jobs.checks], hide_index=True)
                for check in jobs.checks:
                    if check.get("attempts"):
                        st.caption(check.get("employer", check.get("board", "Source")) + " · HTTP attempts")
                        st.dataframe(check["attempts"], hide_index=True)
        st.caption("These are source listings, not eligibility decisions. Check the original opportunity for current availability and requirements.")
