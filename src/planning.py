"""Small, explicit learning-stage policies. These do not define enrollment rules."""

import re

from .models import Record, StudentProfile
from .retrieval import tokenize
from .query import catalog_vocabulary, interpret_query

CAREER_NAMES = {"ai_ml": "AI / Machine Learning", "embedded": "Embedded Systems", "exploring": "Still exploring"}
PHASE_NAMES = {"next": "Start here", "build": "Build toward", "later": "Later goals", "explore":"Explore requested courses"}
BASIC_CODES = {"ECE101", "ECE175", "CSC110", "CSC120", "ISTA130"}
RESOURCE_TERMS = {
    "resource:pytorch": ("pytorch",), "resource:cs50": ("cs50",),
    "resource:python": ("python tutorial", "python"),
    "resource:numpy": ("numpy", "numerical arrays"),
    "resource:sklearn": ("scikit learn", "sklearn"),
    "resource:pico": ("raspberry pi pico", "pico", "c/c++ sdk"),
    "resource:mit_algorithms": ("mit 6.006", "6.006", "mit algorithms"),
    "resource:mit_structures": ("mit 6.004", "6.004", "mit computation structures", "computation structures"),
}


def requested_resource_ids(catalog, profile, *, question=None):
    """Explicit, whole-phrase resource preferences shared by checking and context."""
    def words(value):
        return " " + " ".join(re.findall(r"[a-z0-9]+(?:\+\+)?", value.casefold())) + " "
    value = profile.question if question is None else question
    text = words(value if value.strip() else profile.interests)
    positions = {}
    for record in catalog.records:
        if (record.kind != "resource" or record.career_ids and profile.career_id != "exploring"
                and profile.career_id not in record.career_ids):
            continue
        matches = [text.find(words(term)) for term in RESOURCE_TERMS.get(record.record_id, ()) if words(term) in text]
        if matches:
            positions[record.record_id] = min(matches)
    return sorted(positions, key=positions.get)


def requested_record_ids(catalog, profile, codes):
    """Resolve routing hints to relevant courses outside recorded coursework."""
    recorded = {item.course_code for item in profile.completed} | set(profile.current_enrollment)
    return list(dict.fromkeys(record.record_id for code in codes for record in catalog.records
        if record.kind == "course" and record.code == code and code not in recorded
        and record.catalog_version == profile.catalog_version
        and (profile.career_id == "exploring" or not record.career_ids or profile.career_id in record.career_ids)))


def needs_programming_foundations(profile: StudentProfile):
    completed = {c.course_code for c in profile.completed if c.grade not in {"E", "F"}}
    return profile.programming_background == "new" and not (completed & BASIC_CODES)


def learning_phase(record: Record, profile: StudentProfile, evaluation=None):
    if record.study_stage == "unreviewed":
        return "explore"
    if evaluation is not None and evaluation.status == "unsatisfied":
        return "later"
    if record.study_stage == "foundation":
        return "next" if needs_programming_foundations(profile) else "build"
    if record.study_stage == "advanced":
        if evaluation is not None and evaluation.status == "satisfied" and not needs_programming_foundations(profile):
            return "next"
        return "later"
    if record.kind == "resource":
        if needs_programming_foundations(profile):
            return "later"
        return "next" if profile.programming_background == "experienced" else "build"
    if evaluation is not None and evaluation.status == "satisfied":
        return "next"
    return "build"


def coverage_message(catalog, profile, question, *, allow_course_discovery=False):
    """A transparent vocabulary/alias guard before adding default career terms.

    This catches clear nonmatches, not semantic intent or every out-of-scope claim.
    The generator must still abstain when the retrieved facts do not answer a query.
    """
    text = question.strip() or profile.interests.strip()
    if allow_course_discovery and re.search(r"\b(?:ECE|CSC)\s*[1-4]\d{2}[A-Z]{0,2}\b", text, re.I):
        return None
    generic = {
        "want", "would", "like", "can", "could", "do", "does", "how", "me", "help", "please",
        "start", "get", "need", "needs", "learn", "learning", "study", "studies", "take", "about",
        "degree", "plan", "planning", "career", "careers", "path", "paths", "major", "student",
        "recommend", "recommended", "recommendations", "suggest", "suggested", "begin", "beginner",
        "which", "should", "is", "are", "be", "have", "has", "am", "it", "this", "that", "s", "to",
        "next", "first", "more", "i", "on", "at", "uofa", "university", "arizona", "courses", "course",
    }
    terms = set(tokenize(text)) - generic
    if not terms:
        return None
    interpretation = interpret_query(text, catalog)
    terms |= set(tokenize(" ".join(interpretation.added_terms)))
    vocabulary = catalog_vocabulary(catalog)
    # These broad words alone cannot establish computing-domain coverage.
    vocabulary -= {"training", "train", "model", "models", "learning", "study", "studies",
        "foundation", "foundations", "project", "projects", "practice", "basic", "introduction",
        "introductory", "engineering", "systems", "design", "control", "data", "patterns", "pattern",
        "coursework", "independent", "source", "saved", "parameters"}
    vocabulary |= {"ai", "ml", "ece", "csc", "python", "robotics", "robot", "math", "calculus", "algebra", "programming"}
    vocabulary |= {r.code.lower() for r in catalog.records if r.code}
    if terms & vocabulary:
        return None
    return "This starter collection covers AI/ML, embedded systems, and programming foundations. Which of these would you like to explore? Your request does not have a clear match in the available sources."


def format_duration(seconds):
    return f"{seconds * 1000:.1f} ms" if seconds < 1 else f"{seconds:.2f} s"
