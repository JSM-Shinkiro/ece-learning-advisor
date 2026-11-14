"""Career descriptions and team-authored learning paths."""

import re
from dataclasses import dataclass
from typing import Literal

NamedCareer = Literal["ai_ml", "embedded", "signals", "controls"]
CareerDirection = NamedCareer | Literal["exploring"]


@dataclass(frozen=True)
class CareerPath:
    name: str
    roles: str
    starting_question: str
    progression: tuple[str, ...]
    project: str = ""
    application: str = ""
    elective: str = ""
    related_courses: tuple[str, ...] = ()


CAREER_PATHS = {
    "ai_ml": CareerPath("AI / Machine Learning", "Machine learning engineer · Computer vision engineer",
                       "How can I start learning AI and machine learning?", ("ECE101", "CSC120", "ECE425")),
    "embedded": CareerPath("Embedded Systems", "Firmware engineer · Embedded systems engineer",
                           "How can I start learning embedded systems?", ("ECE101", "ECE369A", "ECE372A")),
    "signals": CareerPath(
        "Signals & Communications", "DSP engineer · RF engineer · Wireless systems engineer",
        "How can I start learning digital signal processing and wireless communications?",
        ("ECE220", "ECE340A", "ECE429", "ECE435A"),
        "Generate a noisy signal, filter it, and compare its frequency spectrum before and after.",
        "Apply signal processing to software-defined radio and next-generation wireless systems.",
        "CSC425", ("ECE310", "ECE320A", "ECE381A"),
    ),
    "controls": CareerPath(
        "Controls & Robotics", "Controls engineer · Automation engineer · Robotics engineer",
        "How can I start learning feedback control for robots?",
        ("ECE220", "ECE320A", "ECE441A", "ECE442"),
        "Simulate a motor speed controller. Change the gain and compare overshoot and settling time.",
        "Apply feedback and stability analysis to industrial automation and autonomous mobile robots.",
        "CSC437", ("ECE310", "ECE372A"),
    ),
}
CAREER_NAMES = {key: path.name for key, path in CAREER_PATHS.items()} | {"exploring": "Still exploring"}
EXPANDED_DIRECTIONS = ("signals", "controls")

ELECTIVE_RULE = "https://catalog.arizona.edu/programs/ECEBSECE/program-requirements-a1nCj"
ELECTIVE_GUIDANCE = (
    "The 2026–27 catalog lists 300- and 400-level courses under Technical Electives II, excluding 390s and 490s. "
    "Ask ECE advising whether this course can fulfill that requirement for your catalog year, "
    "and check the section's enrollment requirements before registering."
)

_DIRECTION_CUES = {
    "signals": r"\b(?:digital signal processing|dsp|signals? and communications?|signal processing|"
               r"wireless(?: communications?| systems?| dsp)?|software defined radio|"
               r"radio frequency|open ran|computer networking|ece ?429|ece ?435a|csc ?425)\b",
    "controls": r"\b(?:controls? and robotics|feedback control|automatic control|digital control|"
                r"robotics|industrial automation|motor control|pid control(?:ler)?|geometric algorithms|"
                r"ece ?441a|ece ?442|csc ?437)\b",
}


def question_direction(question):
    """Route an open-ended profile only when one new direction clearly matches."""
    normalized = " ".join(re.findall(r"[a-z0-9]+", question.casefold()))
    matches = [key for key, pattern in _DIRECTION_CUES.items() if re.search(pattern, normalized)]
    return matches[0] if len(matches) == 1 else None
