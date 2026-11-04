"""Portable profiles. Never deserialize pickle or executable input."""

from __future__ import annotations

import re

from .models import Completion, StudentProfile

MAX_PROFILE_BYTES = 1024 * 1024


def parse_completions(text: str) -> list[Completion]:
    items = []
    for token in re.split(r"[,;\n]+", text):
        if not token.strip():
            continue
        code, sep, grade = token.strip().partition(":")
        items.append(Completion(course_code=code, grade=grade.strip() if sep else None))
    # Also enforces uniqueness through the canonical profile contract.
    StudentProfile(completed=items)
    return items


def export_profile(profile: StudentProfile) -> str:
    return profile.model_dump_json(indent=2)


def import_profile(raw: bytes) -> StudentProfile:
    if len(raw) > MAX_PROFILE_BYTES:
        raise ValueError("Profile file is too large")
    return StudentProfile.model_validate_json(raw)


def edit_profile(profile: StudentProfile, **changes) -> StudentProfile:
    """Validate edited fields without dropping imported fields absent from the form."""
    return StudentProfile.model_validate({**profile.model_dump(), **changes})


def merge_completions(selected_codes, manual_text, previous):
    previous_by_code = {c.course_code: c for c in previous}
    items = {code: previous_by_code.get(code, Completion(course_code=code)) for code in selected_codes}
    for course in parse_completions(manual_text):
        items[course.course_code] = course
    return list(items.values())
