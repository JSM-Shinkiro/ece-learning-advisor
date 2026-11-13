"""Run with: python -m streamlit run app.py."""

import streamlit as st
from dotenv import load_dotenv
from pydantic import ValidationError

from src.catalog import ROOT, load_runtime_catalog
from src.controller import run_advisor
from src.inspector import render_inspector
from src.models import StudentProfile
from src.planning import CAREER_NAMES, PHASE_NAMES
from src.profiles import edit_profile, export_profile, merge_completions, parse_completions, parse_current_courses
from src.session import apply_profile, choose_direction, complete_course, restore_profile, sync_profile_widgets
from src.settings import ConfigurationError, load_settings
from src.source_reuse import SOURCE_REUSE_SECONDS
from src.advisor_jobs import AdvisorBusy, start_advisor_job, collect_advisor_job, keep_source_plan, source_checks_pending
from src.progress import PHASE_LABELS
from src.collection_ui import render_collection
from src.opportunity_ui import render_opportunities
from src.source_ui import enrollment_details, roadmap_expander, source_details
from src.course_directory import load_course_directory
from src.enrollment_references import load_enrollment_references
from src.learning_ui import LESSONS, render_lesson

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

sections = (*LESSONS, "Advisor")
destination = st.session_state.pop("lesson_destination", None)
if destination is not None:
    st.session_state.view = destination
elif "view" not in st.session_state:
    requested_view = st.query_params.get("view")
    st.session_state.view = requested_view if requested_view in sections else "Beginner"
view = st.segmented_control("Learning stage", sections, key="view", required=True,
                            bind="query-params", width="stretch", label_visibility="collapsed")
if view in LESSONS:
    st.session_state.reset_profile_widgets = True
    render_lesson(view, None if view == "Beginner" else load_runtime_catalog())
    st.stop()

base_catalog = load_runtime_catalog()
try:
    course_directory = load_course_directory()
except (OSError, ValueError):
    course_directory = None
    st.warning("The broader ECE catalog is unavailable. The saved advisor collection remains available.")
try:
    enrollment_references = load_enrollment_references()
except (OSError, ValueError):
    enrollment_references = None
catalog = getattr(st.session_state.get("result"), "catalog", None) or base_catalog
records = {r.record_id:r for r in catalog.records}
sources = {s.source_id:s for s in catalog.sources}
course_lookup = {c.code:c for c in course_directory.courses} if course_directory is not None else {}
course_lookup.update({r.code:r for r in catalog.records if r.kind == "course"})
course_lookup = dict(sorted(course_lookup.items()))
standings = ["Incoming", "Freshman", "Sophomore", "Junior", "Senior", "Other"]
background_names = {"new":"Getting started", "some":"Some programming experience", "experienced":"Comfortable with programming"}
if "profile" not in st.session_state:
    st.session_state.profile = StudentProfile()
    st.session_state.reset_profile_widgets = True
profile = st.session_state.profile
lesson_question = st.session_state.get("lesson_advisor_question")
reset_widgets = st.session_state.pop("reset_profile_widgets", False)
if reset_widgets:
    sync_profile_widgets(st.session_state, profile, course_lookup)
if (reset_widgets or destination == "Advisor") and st.session_state.get("lesson_question_pending"):
    st.session_state.question = lesson_question


def show_profile_error(exc):
    if isinstance(exc, ValidationError):
        return exc.errors()[0]["msg"].removeprefix("Value error, ")
    return str(exc)


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
        question = st.text_input("A question about your next step", key="question", max_chars=1200)
        submitted = st.form_submit_button("Update my roadmap",type="primary",width="stretch")
        recheck = st.form_submit_button("Check sources again",disabled=not settings.refresh_sources,
            help="Update the roadmap from these profile details and recheck selected official pages now.")
        if settings.refresh_sources:
            st.caption("Recent source checks are reused for up to 5 minutes. Check sources again to refresh them now.")
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

if submitted or recheck:
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
        st.session_state.force_source_check = recheck
        st.session_state.pop("profile_error",None)
        st.rerun()
    except (ValueError,TypeError) as exc:
        st.error("Please check your profile. "+show_profile_error(exc))

if st.session_state.pop("refresh_pending",False):
    force_source_check = st.session_state.pop("force_source_check",False)
    request_options = dict(api_key=api_key,use_ai=use_ai,
            method=method,embedding_model=embedding_model,generation_model=generation_model,
            dimensions=settings.embedding_dimensions,cache_dir=settings.cache_root/"embeddings",
            ai_time_budget_seconds=settings.ai_time_budget_seconds,
            refresh_sources=settings.refresh_sources,
            source_reuse_seconds=0 if force_source_check else SOURCE_REUSE_SECONDS,
            source_cache_dir=settings.cache_root/"sources", course_directory=course_directory)
    background = settings.refresh_sources or bool(use_ai and api_key)
    if background:
        try:
            st.session_state.advisor_job = start_advisor_job(base_catalog,profile,runner=run_advisor,**request_options)
        except (AdvisorBusy,RuntimeError,OSError):
            background = False
            request_options.update(use_ai=False, refresh_sources=False)
            adjustment = "Roadmap updates are busy. Showing saved data. Submit again to retry."
            if not settings.refresh_sources:
                adjustment = "AI assistance is busy. Showing the source plan. Submit again to retry."
            st.warning(adjustment)
    if not background:
        request_status = st.status("Updating your learning plan...",expanded=True)
        def show_request_phase(phase, label):
            request_status.update(label=label)
            request_status.write(label)
        try:
            st.session_state.result = run_advisor(base_catalog,profile,**request_options,progress=show_request_phase)
            request_status.update(label="More detail needed" if (st.session_state.result.coverage_notice
                                  or st.session_state.result.generation_status=="insufficient_evidence")
                                  else "Learning plan ready",state="complete",expanded=False)
        except (ValueError,OSError):
            request_status.update(label="The plan could not be updated",state="error",expanded=True)
            st.error("The plan could not be updated. Check the configuration and submit your profile again.")

job = st.session_state.get("advisor_job")
if job is not None:
    collect_advisor_job(st.session_state, job)


@st.fragment(run_every=0.5 if st.session_state.get("advisor_job") else None)
def advisor_activity():
    job = st.session_state.get("advisor_job")
    if job is not None:
        if collect_advisor_job(st.session_state,job):
            st.rerun()
        snapshot = job.snapshot()
        result = st.session_state.get("result")
        checking_sources = source_checks_pending(result)
        label = "Updating your learning plan..."
        if result is not None:
            label = ("Saved-data plan ready · checking official sources" if checking_sources
                     else "Source plan ready · AI assistance is running")
        with st.status(label, expanded=True):
            for phase in snapshot.phases:
                st.write(PHASE_LABELS[phase])
            if result is not None:
                st.caption("You can use the plan below or update your profile while this runs.")
                keep_label = "Keep saved-data plan" if checking_sources else "Keep source plan"
                if st.button(keep_label, key="keep_source_plan"):
                    keep_source_plan(st.session_state)
                    st.rerun()
    else:
        activity = st.session_state.get("advisor_activity")
        if activity:
            with st.status(activity["label"],state="error" if activity["error"] else "complete",expanded=activity["error"]):
                for phase in activity["phases"]:
                    st.write(PHASE_LABELS[phase])
            if activity["notice"]:
                st.info(activity["notice"])
            if activity["error"]:
                st.error("The plan could not be updated. Submit your profile again.")


advisor_activity()

active_result = st.session_state.get("result")
if active_result is not None:
    catalog = getattr(active_result, "catalog", None) or base_catalog
    records = {r.record_id:r for r in catalog.records}
    sources = {s.source_id:s for s in catalog.sources}

st.caption("ECE LEARNING ADVISOR")
st.title("Your next step, with a path forward.")
st.caption("Learning suggestions for UofA ECE students. Stages describe preparation, not guaranteed enrollment or semester placement.")
collection_summary.caption(f"Available collection · {sum(r.kind == 'course' for r in catalog.records)} courses · {sum(r.kind == 'resource' for r in catalog.records)} resources")
if course_directory is not None:
    st.sidebar.caption(f"ECE catalog · {len(course_directory.courses)} undergraduate courses · {course_directory.catalog_version}")
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
            rule = result.context.rule_results[rid]
            if rule.verification_status == "snapshot" and rule.status != "unknown":
                badge = ("Saved prerequisites satisfied" if rule.status == "satisfied" else "Saved prerequisites missing")
            else:
                badge = {"satisfied":"Recorded prerequisites satisfied","unsatisfied":"Prerequisites missing","unknown":"Enrollment requirements unverified"}[rule.status]
            credits = f"{record.credits:g} credits" if record.credits is not None else "Variable credits · see source"
            st.caption(badge+" · "+credits)
            if record.study_stage == "unreviewed":
                st.caption("Requested catalog course · preparation level and career connection unreviewed")
        else:
            st.caption("Online resource · independent study")
        if record.first_activity:
            st.write("**First activity:** "+record.first_activity)
        actions = st.columns(2) if is_course else [st.container()]
        actions[0].link_button("Official course source" if is_course else "Open learning resource",
                               sources[record.source_ids[0]].url,key="open_"+rid)
        if is_course:
            actions[1].button("Mark completed",key="complete_"+record.code,
                on_click=complete_course,args=(st.session_state,record.code),help="Record successful completion and refresh the plan.")
        details = roadmap_expander("Why this fits and sources", key="roadmap_details_"+rid)
        if not details.open:
            return
        with details:
            if record.learning_note:
                st.write(record.learning_note)
            st.write(record.summary)
            explanation = next((r for r in result.answer.recommendations if r.record_id==rid),None) if result.answer else None
            if explanation:
                st.caption("AI explanation")
                evidence = {e.chunk_id:e for e in result.context.evidence}
                for i,reason in enumerate(explanation.reasons):
                    st.write(reason.text)
                    cited = list(dict.fromkeys(s for eid in reason.evidence_ids for s in evidence[eid].source_ids))
                    for sid in cited:
                        st.link_button("Evidence: "+sources[sid].title,sources[sid].url,key=f"reason_{rid}_{i}_{sid}")
            if is_course:
                st.caption("Catalog "+record.catalog_version)
                if record.rule_reviewed or record.rule_verification == "changed":
                    st.write(" ".join(rule.reasons))
                if record.rule_reviewed:
                    st.caption("If a grade is needed, add it under Optional details in your profile.")
            source_details(record,"details_"+rid,sources)
            if is_course and rule.status == "unknown":
                references = enrollment_references if profile.catalog_version == record.catalog_version else None
                enrollment_details(record.code, sources[record.source_ids[0]].url, record.requirement_reference,
                                   record.catalog_version, references, key="roadmap_enrollment_"+rid)


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
    lesson_draft = lesson_question and question == lesson_question and profile.question != lesson_question
    if lesson_draft:
        st.info("Your lesson question is in Your starting point. Select Update my roadmap to use it.")
        if api_key:
            st.caption("For the embedding comparison, enable AI explanations with semantic or hybrid ranking.")
    elif profile.career_id=="exploring" or result is None:
        direction_cards()
    if result is None and not lesson_draft:
        st.info("Checking sources for your plan. You can update your profile while this finishes." if st.session_state.get("advisor_job") else
                "Complete your starting point and select Update my roadmap, or choose a direction above.")
    if result is not None:
        job = st.session_state.get("advisor_job")
        pending_sources = source_checks_pending(result)
        if pending_sources:
            st.caption("Saved-data plan · based on dated course and resource snapshots")
        if pending_sources and job and (result.coverage_notice or not result.context.allowed_record_ids):
            st.info("This question needs more evidence. Official source checks are in progress.")
        elif result.coverage_notice:
            st.info(result.coverage_notice)
        elif result.generation_status=="insufficient_evidence":
            st.info(result.answer.clarification if result.answer else "More source information is needed for this request.")
        elif result.generation_complete:
            st.caption("AI explanation available · based on selected sources")
        elif job and not pending_sources:
            st.caption("Source plan ready · AI assistance is still running")
        elif result.trace.get("source_refresh", {}).get("enabled"):
            st.caption("Learning suggestions from the available source evidence")
        elif not pending_sources:
            st.caption("Preview mode · learning suggestions from available sources")
        for issue in result.issues:
            st.warning(issue)
        reused = sum(check["status"] == "recent_cache"
                     for check in result.trace.get("source_refresh", {}).get("checks", []))
        if reused:
            st.caption(f"Used {reused} recent source checks for this update. Source details show check times.")
        if not result.coverage_notice and result.generation_status!="insufficient_evidence":
            st.caption("Start with the first suitable activity. Confirm course enrollment requirements before registering.")
            for phase,title in PHASE_NAMES.items():
                ids = [rid for rid in result.context.allowed_record_ids if result.context.suggested_phases.get(rid)==phase]
                if ids:
                    st.subheader(title)
                    for rid in ids:
                        render_card(records[rid],result)
            if not result.context.allowed_record_ids and not (pending_sources and job):
                st.info("No additional matches remain in this small collection. Explore Courses & Resources or try another direction.")
        render_inspector(result, catalog, lesson_question=lesson_question)

with collection:
    render_collection(base_catalog, course_directory, enrollment_references)

with opportunities:
    render_opportunities(settings)
