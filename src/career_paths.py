"""Career descriptions and team-authored learning paths."""

import re
from dataclasses import dataclass
from typing import Literal

NamedCareer = Literal["ai_ml", "embedded", "signals", "controls", "semiconductors"]
CareerDirection = NamedCareer | Literal["exploring"]


@dataclass(frozen=True)
class StudyRoute:
    label: str
    courses: tuple[str, ...]
    cue: str = ""


@dataclass(frozen=True)
class CareerPath:
    name: str
    roles: str
    starting_question: str
    routes: tuple[StudyRoute, ...]
    project: str = ""
    application: str = ""
    electives: tuple[str, ...] = ()
    related_courses: tuple[str, ...] = ()
    foundation_codes: tuple[str, ...] = ()
    foundation_query: str = ""

    @property
    def progression(self):
        return tuple(code for route in self.routes for code in route.courses)

    def matching_route(self, question):
        normalized = " ".join(re.findall(r"[a-z0-9]+", question.casefold()))
        matches = [route for route in self.routes if route.cue and re.search(route.cue, normalized)]
        return matches[0] if len(matches) == 1 else None


CAREER_PATHS = {
    "ai_ml": CareerPath(
        "AI / Machine Learning", "Machine learning engineer · Computer vision engineer",
        "How can I start learning AI and machine learning?",
        (StudyRoute("Example course progression", ("ECE101", "CSC120", "ECE425")),),
    ),
    "embedded": CareerPath(
        "Embedded Systems", "Firmware engineer · Embedded systems engineer",
        "How can I start learning embedded systems?",
        (StudyRoute("Example course progression", ("ECE101", "ECE369A", "ECE372A")),),
    ),
    "signals": CareerPath(
        "Signals & Communications", "DSP engineer · RF engineer · Wireless systems engineer",
        "How can I start learning digital signal processing and wireless communications?",
        (StudyRoute("Example course progression", ("ECE220", "ECE340A", "ECE429", "ECE435A")),),
        "Generate a noisy signal, filter it, and compare its frequency spectrum before and after.",
        "Apply signal processing to software-defined radio and next-generation wireless systems.",
        electives=("CSC425",), related_courses=("ECE310", "ECE320A", "ECE381A"),
        foundation_codes=("ECE220",), foundation_query="ECE220 circuits",
    ),
    "controls": CareerPath(
        "Controls & Robotics", "Controls engineer · Automation engineer · Robotics engineer",
        "How can I start learning feedback control for robots?",
        (StudyRoute("Example course progression", ("ECE220", "ECE320A", "ECE441A", "ECE442")),),
        "Simulate a motor speed controller. Change the gain and compare overshoot and settling time.",
        "Apply feedback and stability analysis to industrial automation and autonomous mobile robots.",
        electives=("CSC437",), related_courses=("ECE310", "ECE372A"),
        foundation_codes=("ECE220",), foundation_query="ECE220 circuits",
    ),
    "semiconductors": CareerPath(
        "Semiconductors & Digital Hardware",
        "Digital design engineer · Design verification engineer · Fab process engineer · Product test engineer",
        "What should I learn for digital chip design and verification?",
        (
            StudyRoute("Design & verification", ("ECE274A", "ECE369A", "ECE407", "ECE462"),
                       r"\b(?:design|verification|asic|rtl|vlsi|verilator|ece ?407|ece ?462)\b"),
            StudyRoute("Fabrication & test", ("ECE220", "ECE351C", "ECE352", "ECE446"),
                       r"\b(?:fabrication|fab|wafer|manufacturing|product test|process engineer|packaging|ece ?446)\b"),
        ),
        "Simulate a four-bit counter. Write checks for reset, counting and rollover.",
        "Explore digital chip design and semiconductor manufacturing. Advanced packaging connects device, process and test work.",
        electives=("SIE406", "MSE365"),
        foundation_codes=("ECE274A", "ECE369A", "ECE220", "ECE351C", "ECE352"),
        foundation_query="ECE274A digital logic ECE220 circuits",
    ),
}
CAREER_NAMES = {key: path.name for key, path in CAREER_PATHS.items()} | {"exploring": "Still exploring"}
EXPANDED_DIRECTIONS = ("signals", "controls", "semiconductors")

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
    "semiconductors": r"\b(?:semiconductors?|digital hardware|chip (?:design|verification|fabrication|manufacturing|testing)|"
                       r"(?:silicon|wafer|chip) fab(?:rication)?|asic|rtl|vlsi|verilator|"
                       r"ece ?407|ece ?446|ece ?462|sie ?406|mse ?365)\b",
}


def question_direction(question):
    """Route an open-ended profile only when one new direction clearly matches."""
    normalized = " ".join(re.findall(r"[a-z0-9]+", question.casefold()))
    matches = [key for key, pattern in _DIRECTION_CUES.items() if re.search(pattern, normalized)]
    return matches[0] if len(matches) == 1 else None
