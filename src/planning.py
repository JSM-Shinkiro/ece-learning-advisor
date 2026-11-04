"""Small, explicit learning-stage policies. These do not define enrollment rules."""

from .models import Record, StudentProfile
from .retrieval import tokenize

CAREER_NAMES = {"ai_ml": "AI / Machine Learning", "embedded": "Embedded Systems", "exploring": "Still exploring"}
PHASE_NAMES = {"next": "Start here", "build": "Build toward", "later": "Later goals"}
BASIC_CODES = {"ECE101", "ECE175", "CSC110", "CSC120", "ISTA130"}


def needs_programming_foundations(profile: StudentProfile):
    completed = {c.course_code for c in profile.completed if c.grade not in {"E", "F"}}
    return profile.programming_background == "new" and not (completed & BASIC_CODES)


def learning_phase(record: Record, profile: StudentProfile, evaluation=None):
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


def coverage_message(catalog, profile, question):
    """A transparent vocabulary guard before adding default career terms.

    This catches clear nonmatches, not semantic intent or every out-of-scope claim.
    The generator must still abstain when the retrieved facts do not answer a query.
    """
    text = question.strip() or profile.interests.strip()
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
    vocabulary = set(tokenize(" ".join(r.title + " " + r.summary + " " + " ".join(r.topics) for r in catalog.records)))
    vocabulary |= {"ai", "ml", "ece", "csc", "python", "robotics", "robot", "math", "calculus", "algebra", "programming"}
    vocabulary |= {r.code.lower() for r in catalog.records if r.code}
    if terms & vocabulary:
        return None
    return "This starter collection covers AI/ML, embedded systems, and programming foundations. Which of these would you like to explore? Your request does not have a clear match in the available sources."


def format_duration(seconds):
    return f"{seconds * 1000:.1f} ms" if seconds < 1 else f"{seconds:.2f} s"
