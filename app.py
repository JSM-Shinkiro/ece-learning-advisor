"""Run with: python -m streamlit run app.py."""

from datetime import timedelta, timezone

import streamlit as st
from dotenv import load_dotenv
from pydantic import ValidationError

from src.catalog import ROOT, load_runtime_catalog
from src.controller import run_advisor
from src.inspector import render_inspector
from src.jobs import search_jobs
from src.opportunities import load_employer_boards, request_opportunities, search_employer_jobs
from src.opportunity_details import fetch_posting_detail, request_posting_detail
from src.opportunity_pages import page_info, request_opportunity_page
from src.models import StudentProfile
from src.planning import CAREER_NAMES, PHASE_NAMES
from src.profiles import edit_profile, export_profile, merge_completions, parse_completions, parse_current_courses
from src.session import apply_profile, choose_direction, complete_course, restore_profile, sync_profile_widgets
from src.settings import ConfigurationError, load_settings

load_dotenv(ROOT / ".env")
st.set_page_config(page_title="ECE Learning Advisor · P07", page_icon="🧭", layout="wide")
try:
    settings = load_settings()
except ConfigurationError as exc:
    st.error(str(exc))
    st.stop()
st.markdown("""
<style>
.block-container { max-width: 1180px; padding-top: 3rem; padding-bottom: 2rem; }
[data-testid="stSidebar"] { border-right: 1px solid #25334a; }
h1 { letter-spacing: -.035em; }
.stButton button, .stDownloadButton button { border-radius: 9px; }
@media (max-width: 700px) { .block-container { padding-left: 1rem; padding-right: 1rem; } }
</style>
""", unsafe_allow_html=True)

base_catalog = load_runtime_catalog()
catalog = getattr(st.session_state.get("result"), "catalog", None) or base_catalog
records = {r.record_id:r for r in catalog.records}
sources = {s.source_id:s for s in catalog.sources}
course_lookup = {r.code:r for r in catalog.records if r.kind == "course"}
standings = ["Incoming", "Freshman", "Sophomore", "Junior", "Senior", "Other"]
background_names = {"new":"Getting started", "some":"Some programming experience", "experienced":"Comfortable with programming"}
if "profile" not in st.session_state:
    st.session_state.profile = StudentProfile()
    st.session_state.reset_profile_widgets = True
profile = st.session_state.profile
if st.session_state.pop("reset_profile_widgets", False):
    sync_profile_widgets(st.session_state, profile, course_lookup)


def show_profile_error(exc):
    if isinstance(exc, ValidationError):
        return exc.errors()[0]["msg"].removeprefix("Value error, ")
    return str(exc)


def check_selected_posting(posting_id):
    try:
        request_posting_detail(st.session_state, posting_id, fetcher=fetch_posting_detail)
    except (ValueError, RuntimeError, OSError):
        st.session_state["job_detail_error"] = posting_id


def change_opportunity_page(page):
    try:
        request_opportunity_page(st.session_state, page)
    except (ValueError, OSError):
        st.session_state["job_page_error"] = "This saved search page could not be opened. Run a new search."


def restore_uploaded_profile():
    uploaded = st.session_state.get("profile_upload")
    if uploaded is not None:
        try:
            restore_profile(st.session_state, uploaded.getvalue())
            st.session_state.reset_profile_widgets = True
            st.session_state.profile_message = "Saved profile restored."
            st.session_state.pop("profile_error", None)
        except (ValueError, TypeError) as exc:
            st.session_state.profile_error = "Profile was not restored. " + show_profile_error(exc)


def source_details(record, prefix):
    for sid in record.source_ids:
        source = sources[sid]
        local = timezone(timedelta(hours=-7))
        downloaded = source.retrieved_at.astimezone(local).strftime("%Y-%m-%d %H:%M MST")
        checked = source.last_checked_at.astimezone(local).strftime("%Y-%m-%d %H:%M MST") if source.last_checked_at else None
        st.link_button(source.title,source.url,key=prefix+"_"+sid)
        if source.verification_status == "verified":
            status = "Checked "+(checked or downloaded)+" · downloaded "+downloaded
        elif source.verification_status == "stale":
            status = "Source check failed · "+("last successful check "+checked if checked else "saved snapshot "+downloaded)
        else:
            status = "Saved source snapshot · retrieved "+downloaded
        st.caption(status+" · "+source.review_note)


def grade_requirements(rule):
    found = {rule.course_code} if rule.minimum_grade and rule.course_code else set()
    for child in rule.children:
        found |= grade_requirements(child)
    return found


with st.sidebar:
    st.caption("TEAM P07 · ECE 425/525")
    st.subheader("Your starting point")
    if "profile_error" in st.session_state:
        st.error(st.session_state.profile_error)
    if "profile_message" in st.session_state:
        st.success(st.session_state.pop("profile_message"))
    with st.form("profile_form"):
        standing = st.selectbox("Academic standing",standings,key="standing")
        career_id = st.selectbox("Career direction",list(CAREER_NAMES),
                                 format_func=lambda k:CAREER_NAMES[k],key="career_id")
        background = st.selectbox("Programming background",list(background_names),
            format_func=lambda k:background_names[k],key="programming_background")
        interests = st.text_area("What interests you?",max_chars=1500,
                                 placeholder="AI and hardware integration, robotics, computer vision...",height=85,key="interests")
        selected = st.multiselect("Completed courses (optional)",list(course_lookup),
            format_func=lambda code:code+" · "+course_lookup[code].title,key="completed_courses")
        current_selected = st.multiselect("Currently taking (optional)",list(course_lookup),
            format_func=lambda code:code+" · "+course_lookup[code].title,key="current_courses",
            help="Keep these courses out of your next-step suggestions. Taking a course does not count as passing it.")
        submitted = st.form_submit_button("Update my roadmap",type="primary",width="stretch")
        with st.expander("Optional details"):
            catalog_version = st.text_input("Catalog year",key="catalog_version",
                                           help="Use your admitted catalog year. Enter Not sure if you do not know it.")
            manual_text = st.text_area("Other course codes or optional grades",
                placeholder="MATH129, CSC110:B",key="course_text",
                help="Separate codes with commas. A grade can be supplied as CODE:B. List successful completions only.")
            current_text = st.text_area("Other current course codes",
                placeholder="MATH129, PHYS241",key="current_course_text",
                help="Separate courses you are taking with commas. Add grades after successful completion.")
            needed_grades = set().union(*(grade_requirements(r.rule) for r in catalog.records if r.rule_reviewed))
            grade_values = {}
            grade_options = [None,"A+","A","A-","B+","B","B-","C+","C","C-","D+","D","D-","P","S","CR"]
            for code in selected:
                if code in needed_grades:
                    grade_values[code] = st.selectbox("Grade for "+code,grade_options,
                        format_func=lambda g:g or "Not recorded",
                        key="grade_"+code,help="A reviewed prerequisite uses the grade for this course.")
            history_complete = st.checkbox("I listed all my completed courses",key="history_complete")
            experience = st.text_area("Projects or experience",key="experience",max_chars=2000)
            question = st.text_input("A question about your next step",key="question",max_chars=1200)

    # Credentials from the server never become widget defaults or session values.
    server_key = settings.gemini_key.get_secret_value()
    if server_key:
        st.session_state.pop("gemini_key", None)
    development = settings.development_mode
    with st.expander("AI and ranking options"):
        session_key = ""
        if development and not server_key:
            session_key = st.text_input("Session-only Gemini key",type="password",value="",key="gemini_key")
        api_key = server_key or session_key
        if not api_key:
            st.caption("Preview mode is available. The team can configure AI explanations for this app.")
        else:
            st.caption("AI is configured. A submitted profile and selected evidence are sent to Gemini when enabled.")
        use_ai = st.checkbox("Generate AI explanations",value=False,disabled=not bool(api_key),key="use_ai")
        method = st.selectbox("Ranking method",["hybrid","semantic","keyword"],disabled=not (use_ai and api_key),key="ranking_method")
        generation_model = settings.generation_model
        embedding_model = settings.embedding_model
        if development:
            generation_model = st.text_input("Generation model",value=generation_model)
            embedding_model = st.text_input("Embedding model",value=embedding_model)

    with st.expander("Saved profile"):
        st.caption("Carry your progress between sessions with a JSON file, up to 1 MB.")
        st.file_uploader("Restore a saved profile",type=["json"],max_upload_size=1,
                         key="profile_upload",on_change=restore_uploaded_profile)
        st.download_button("Download my profile",export_profile(profile),file_name="ece_profile.json",mime="application/json",width="stretch",on_click="ignore")
    collection_summary = st.empty()

if submitted:
    try:
        completed = merge_completions(selected,manual_text,profile.completed)
        manual_codes = {c.course_code for c in parse_completions(manual_text)}
        completed = [c.model_copy(update={"grade":grade_values[c.course_code]})
                     if c.course_code in grade_values and c.course_code not in manual_codes else c for c in completed]
        updated = edit_profile(profile,standing=standing,career_id=career_id,programming_background=background,
            catalog_version=catalog_version.strip() or "Not sure",interests=interests,completed=completed,
            current_enrollment=[*current_selected, *parse_current_courses(current_text)],
            history_complete=history_complete,experience=experience,question=question)
        apply_profile(st.session_state,updated,reset_widgets=False)
        st.session_state.reset_profile_widgets = True
        st.session_state.pop("profile_error",None)
        st.rerun()
    except (ValueError,TypeError) as exc:
        st.error("Please check your profile. "+show_profile_error(exc))

if st.session_state.pop("refresh_pending",False):
    with st.spinner("Updating your learning plan..."):
        try:
            st.session_state.result = run_advisor(base_catalog,profile,api_key=api_key,use_ai=use_ai,
                method=method,embedding_model=embedding_model,generation_model=generation_model,
                dimensions=settings.embedding_dimensions,cache_dir=settings.cache_root/"embeddings",
                ai_time_budget_seconds=settings.ai_time_budget_seconds,
                refresh_sources=settings.refresh_sources,
                source_cache_dir=settings.cache_root/"sources")
        except (ValueError,OSError):
            st.error("The plan could not be updated. Check the configuration and submit your profile again.")

active_result = st.session_state.get("result")
if active_result is not None:
    catalog = getattr(active_result, "catalog", None) or base_catalog
    records = {r.record_id:r for r in catalog.records}
    sources = {s.source_id:s for s in catalog.sources}

st.caption("ECE LEARNING ADVISOR")
st.title("Your next step, with a path forward.")
st.caption("Learning suggestions for UofA ECE students. Stages describe preparation, not guaranteed enrollment or semester placement.")
collection_summary.caption(f"Available collection · {sum(r.kind == 'course' for r in catalog.records)} courses · {sum(r.kind == 'resource' for r in catalog.records)} resources")
roadmap, collection, opportunities = st.tabs(["My Roadmap","Courses & Resources","Opportunities"])


def direction_cards():
    st.subheader("Choose a direction to explore")
    st.write("AI and hardware can overlap. Pick a starting direction and switch as your interests develop.")
    for column, career in zip(st.columns(2),["ai_ml","embedded"]):
        with column, st.container(border=True):
            st.markdown("**"+CAREER_NAMES[career]+"**")
            st.write("Neural networks, programming, and practical model building." if career=="ai_ml"
                     else "C programming, processor architecture, and connected devices.")
            example_codes = ["ECE101", "CSC120", "ECE425"] if career == "ai_ml" else ["ECE101", "ECE369A", "ECE372A"]
            st.caption("Example learning connection: "+" → ".join(code for code in example_codes if code in course_lookup))
            st.button("Explore "+CAREER_NAMES[career],key="choose_"+career,width="stretch",
                      on_click=choose_direction,args=(st.session_state,career))


def render_card(record, result):
    rid = record.record_id
    is_course = record.kind == "course"
    with st.container(border=True):
        st.markdown("**"+(record.code+" · " if record.code else "")+record.title+"**")
        if is_course:
            status = result.context.rule_results[rid].status
            badge = {"satisfied":"Recorded prerequisites satisfied","unsatisfied":"Prerequisites missing","unknown":"Enrollment requirements unverified"}[status]
            st.caption(badge+f" · {record.credits:g} credits")
        else:
            st.caption("Online resource · independent study")
        st.write("**Why this fits:** "+(record.learning_note or record.summary))
        if record.first_activity:
            st.write("**First activity:** "+record.first_activity)
        explanation = next((r for r in result.answer.recommendations if r.record_id==rid),None) if result.answer else None
        if explanation:
            st.caption("AI explanation")
            evidence = {e.chunk_id:e for e in result.context.evidence}
            for i,reason in enumerate(explanation.reasons):
                st.write(reason.text)
                cited = list(dict.fromkeys(s for eid in reason.evidence_ids for s in evidence[eid].source_ids))
                for sid in cited:
                    st.link_button("Evidence: "+sources[sid].title,sources[sid].url,key=f"reason_{rid}_{i}_{sid}")
        actions = st.columns(2) if is_course else [st.container()]
        actions[0].link_button("Official course source" if is_course else "Open learning resource",
                               sources[record.source_ids[0]].url,key="open_"+rid)
        if is_course:
            actions[1].button("Mark completed",key="complete_"+record.code,
                on_click=complete_course,args=(st.session_state,record.code),help="Record successful completion and refresh the plan.")
        with st.expander("Course details & sources" if is_course else "Resource details & sources"):
            st.write(record.summary)
            if is_course:
                st.caption("Catalog "+record.catalog_version)
                st.write(" ".join(result.context.rule_results[rid].reasons))
                st.caption("If a grade is needed, add it under Optional details in your profile.")
            source_details(record,"details_"+rid)


with roadmap:
    st.caption(f"Saved profile: {profile.standing} · {CAREER_NAMES[profile.career_id]} · {len(profile.completed)} completed courses · {len(profile.current_enrollment)} currently taking")
    for notice in st.session_state.get("profile_notices",[]):
        st.caption(notice)
    if profile.completed:
        with st.expander("Completed coursework ("+str(len(profile.completed))+")"):
            st.write(", ".join(c.course_code+(" ("+c.grade+")" if c.grade else "") for c in profile.completed))
    if profile.current_enrollment:
        with st.expander("Currently taking ("+str(len(profile.current_enrollment))+")",expanded=True):
            st.caption("Mark a course completed after passing it. Add any required grade under Optional details.")
            for code in profile.current_enrollment:
                label = code + (" · " + course_lookup[code].title if code in course_lookup else "")
                name, action = st.columns([3,1])
                name.write(label)
                action.button("Mark completed",key="finish_"+code,
                    on_click=complete_course,args=(st.session_state,code),help="Move this course to completed coursework and refresh the plan.")
    result = st.session_state.get("result")
    if profile.career_id=="exploring" or result is None:
        direction_cards()
    if result is None:
        st.info("Complete your starting point and select Update my roadmap, or choose a direction above.")
    else:
        if result.coverage_notice:
            st.info(result.coverage_notice)
        elif result.generation_status=="insufficient_evidence":
            st.info(result.answer.clarification if result.answer else "More source information is needed for this request.")
        elif result.generation_complete:
            st.caption("AI explanation available · based on selected sources")
        else:
            st.caption("Preview mode · learning suggestions from available sources")
        for issue in result.issues:
            st.warning(issue)
        if not result.coverage_notice and result.generation_status!="insufficient_evidence":
            st.caption("Start with the first suitable activity. Confirm course enrollment requirements before registering.")
            for phase,title in PHASE_NAMES.items():
                ids = [rid for rid in result.context.allowed_record_ids if result.context.suggested_phases.get(rid)==phase]
                if ids:
                    st.subheader(title)
                    for rid in ids:
                        render_card(records[rid],result)
            if not result.context.allowed_record_ids:
                st.info("No additional matches remain in this small collection. Explore Courses & Resources or try another direction.")
        render_inspector(result,catalog)

with collection:
    st.subheader("Courses & resources")
    st.caption("A starting collection with dated sources. Learning connections are suggestions; unresolved enrollment rules need review.")
    for record in catalog.records:
        if record.kind=="career":
            continue
        with st.expander((record.code+" · " if record.code else "")+record.title):
            st.write(record.summary)
            source_details(record,"collection_"+record.record_id)

with opportunities:
    st.subheader("Explore opportunities")
    st.caption("Direction: "+CAREER_NAMES[profile.career_id]+" · uses your saved profile")
    configured = settings.adzuna_configured
    provider_names = {"greenhouse": "Employer boards", "adzuna": "Adzuna location search"}
    provider = st.selectbox("Opportunity source", ["greenhouse", "adzuna"] if configured else ["greenhouse"],
                            format_func=provider_names.get, key="opportunity_provider")
    board_available = True
    if provider == "greenhouse":
        try:
            employer_names = ", ".join(b.employer for b in load_employer_boards())
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
                request_opportunities(st.session_state, profile.career_id, location, internship, provider=provider,
                    updated_within=updated_within if provider == "greenhouse" else None, reuse=reuse,
                    early_career=early_career,
                    public_search=search_employer_jobs, adzuna_search=search_jobs,
                    app_id=settings.adzuna_app_id.get_secret_value(), app_key=settings.adzuna_app_key.get_secret_value())
        except (ValueError,RuntimeError):
            st.warning("The provider could not complete this search. Try again later.")
    jobs = st.session_state.get("job_result")
    job_error = st.session_state.get("job_error")
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
            pagination = page_info(jobs)
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
                        on_click=check_selected_posting, args=(job["id"],))
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
