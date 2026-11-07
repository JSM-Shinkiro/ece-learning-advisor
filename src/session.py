"""Profile transitions shared by forms, restore, direction choices, and completion."""

from .models import Completion
from .profiles import edit_profile, import_profile
from .advisor_jobs import discard_advisor_job

PROFILE_WIDGET_KEYS = [
    "standing", "programming_background", "career_id", "interests", "completed_courses",
    "current_courses", "current_course_text", "catalog_version", "course_text", "history_complete", "experience", "question",
]


def sync_profile_widgets(state, profile, course_codes):
    """Publish authoritative values to keyed widgets after a profile transition.

    Deleting a key and changing its default can leave the browser's retained value
    intact. Explicit assignments make Streamlit send a value update to the client.
    Call before creating widgets, and only when applying a saved profile change.
    """
    known = set(course_codes)
    for key in list(state):
        if key.startswith("grade_"):
            state.pop(key, None)
    values = {key: getattr(profile, key) for key in (
        "standing", "career_id", "programming_background", "interests", "catalog_version",
        "history_complete", "experience", "question")}
    values.update(
        completed_courses=[item.course_code for item in profile.completed if item.course_code in known],
        current_courses=[code for code in profile.current_enrollment if code in known],
        course_text=", ".join(item.course_code + (":" + item.grade if item.grade else "")
                              for item in profile.completed if item.course_code not in known),
        current_course_text=", ".join(code for code in profile.current_enrollment if code not in known))
    values.update({"grade_" + item.course_code: item.grade for item in profile.completed if item.course_code in known})
    state.update(values)


def apply_profile(state, profile, *, refresh=True, reset_widgets=True):
    discard_advisor_job(state)
    previous = state.get("profile")
    notices = []
    if previous:
        old = {c.course_code for c in previous.completed}
        new = {c.course_code for c in profile.completed}
        if new - old:
            notices.append("Added to completed coursework: " + ", ".join(sorted(new - old)))
        if old - new:
            notices.append("Removed from completed coursework: " + ", ".join(sorted(old - new)))
        old_current, new_current = set(previous.current_enrollment), set(profile.current_enrollment)
        if new_current - old_current:
            notices.append("Added to currently taking: " + ", ".join(sorted(new_current - old_current)))
        if old_current - new_current:
            notices.append("Removed from currently taking: " + ", ".join(sorted(old_current - new_current)))
        if previous.career_id != profile.career_id:
            notices.append("Career direction updated. The learning plan was refreshed.")
    state["profile"] = profile
    state["profile_notices"] = notices
    for key in ["result", "job_result", "jobs_cache", "job_error", "job_detail", "job_detail_error", "job_page_error", "pending_posting_detail"]:
        state.pop(key, None)
    state["refresh_pending"] = refresh
    if reset_widgets:
        for key in list(state):
            if key in PROFILE_WIDGET_KEYS or key.startswith("grade_"):
                state.pop(key, None)
        state["reset_profile_widgets"] = True


def restore_profile(state, raw):
    profile = import_profile(raw)
    apply_profile(state, profile)
    return profile


def complete_course(state, code):
    profile = state["profile"]
    completion = Completion(course_code=code)
    if completion.course_code not in {c.course_code for c in profile.completed}:
        apply_profile(state, edit_profile(profile, completed=[*profile.completed, completion],
            current_enrollment=[item for item in profile.current_enrollment if item != completion.course_code]))


def choose_direction(state, career_id):
    names = {"ai_ml":"AI and machine learning", "embedded":"embedded systems"}
    apply_profile(state, edit_profile(state["profile"], career_id=career_id,
                                    question="How can I start learning "+names[career_id]+"?"))
