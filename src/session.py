"""Profile transitions shared by forms, restore, direction choices, and completion."""

from .models import Completion
from .profiles import edit_profile, import_profile

PROFILE_WIDGET_KEYS = [
    "standing", "programming_background", "career_id", "interests", "completed_courses",
    "catalog_version", "course_text", "history_complete", "experience", "question",
]


def apply_profile(state, profile, *, refresh=True, reset_widgets=True):
    previous = state.get("profile")
    notices = []
    if previous:
        old = {c.course_code for c in previous.completed}
        new = {c.course_code for c in profile.completed}
        if new - old:
            notices.append("Added to completed coursework: " + ", ".join(sorted(new - old)))
        if old - new:
            notices.append("Removed from completed coursework: " + ", ".join(sorted(old - new)))
        if previous.career_id != profile.career_id:
            notices.append("Career direction updated. The learning plan was refreshed.")
    state["profile"] = profile
    state["profile_notices"] = notices
    for key in ["result", "job_result", "jobs_cache"]:
        state.pop(key, None)
    state["refresh_pending"] = refresh
    if reset_widgets:
        for key in list(state):
            if key in PROFILE_WIDGET_KEYS or key.startswith("grade_"):
                state.pop(key, None)


def restore_profile(state, raw):
    profile = import_profile(raw)
    apply_profile(state, profile)
    return profile


def complete_course(state, code):
    profile = state["profile"]
    if code not in {c.course_code for c in profile.completed}:
        apply_profile(state, edit_profile(profile, completed=[*profile.completed, Completion(course_code=code)]))


def choose_direction(state, career_id):
    names = {"ai_ml":"AI and machine learning", "embedded":"embedded systems"}
    apply_profile(state, edit_profile(state["profile"], career_id=career_id,
                                    question="How can I start learning "+names[career_id]+"?"))
