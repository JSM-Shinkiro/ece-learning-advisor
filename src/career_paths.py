"""Career descriptions and team-authored learning paths."""

import re
from dataclasses import dataclass
from typing import Literal

NamedCareer = Literal[
    "ai_ml", "embedded", "signals", "controls", "semiconductors", "photonics", "power", "biomedical",
]
CareerDirection = NamedCareer | Literal["exploring"]
CORE_DIRECTIONS = ("ai_ml", "embedded")


def _words(text):
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


@dataclass(frozen=True)
class StudyRoute:
    label: str
    courses: tuple[str, ...]
    cue: str
    practice: str
    resource_id: str | None = None

    @property
    def starting_question(self):
        return f"What should I learn for {self.label}?"


@dataclass(frozen=True)
class CareerPath:
    name: str
    roles: str
    starting_question: str
    routes: tuple[StudyRoute, ...]
    application: str = ""
    electives: tuple[str, ...] = ()
    related_courses: tuple[str, ...] = ()
    foundation_codes: tuple[str, ...] = ()
    foundation_query: str = ""

    @property
    def progression(self):
        return tuple(dict.fromkeys(code for route in self.routes for code in route.courses))

    def matching_route(self, question):
        normalized = _words(question)
        named = [route for route in self.routes if f" {_words(route.label)} " in f" {normalized} "]
        matches = named or [route for route in self.routes if re.search(route.cue, normalized)]
        return matches[0] if len(matches) == 1 else None


EDGE_AI = StudyRoute(
    "Edge AI & On-Device Inference", ("ECE101", "ECE369A", "ECE372A", "ECE425", "CSC477"),
    r"\b(?:edge ai|on device inference|tinyml|model quantization|litert)\b",
    "Compare the file size, accuracy and CPU inference time of a small image model before and after quantization.",
    "resource:litert",
)

CAREER_PATHS = {
    "ai_ml": CareerPath(
        "AI / Machine Learning", "Machine learning engineer · Computer vision engineer",
        "How can I start learning AI and machine learning?",
        (
            StudyRoute("Computer Vision & Perception", ("ECE101", "CSC120", "CSC477", "ECE425"),
                       r"\b(?:computer vision|machine vision|image recognition|object detection|csc ?477)\b",
                       "Evaluate an image classifier and explain two errors from its confusion matrix.", "resource:pytorch"),
            StudyRoute("Applied ML", ("ECE101", "CSC120", "CSC480", "ECE425"),
                       r"\b(?:applied (?:ml|machine learning)|principles of machine learning|csc ?480)\b",
                       "Compare a simple baseline and a trained model on the same held-out data.", "resource:sklearn"),
            EDGE_AI,
        ),
        electives=("CSC477", "CSC480"),
    ),
    "embedded": CareerPath(
        "Embedded Systems", "Firmware engineer · Embedded systems engineer",
        "How can I start learning embedded systems?",
        (
            StudyRoute("Firmware & Real-Time Systems", ("ECE101", "ECE369A", "ECE372A", "ECE402C"),
                       r"\b(?:firmware|real time systems|rtos|freertos|ece ?402c)\b",
                       "Simulate a priority-based schedule for a sensor task and a logging task.", "resource:freertos"),
            EDGE_AI,
        ),
        electives=("CSC477",),
    ),
    "signals": CareerPath(
        "Signals & Communications", "DSP engineer · RF engineer · Wireless systems engineer",
        "How can I start learning digital signal processing and wireless communications?",
        (
            StudyRoute("DSP & Wireless Communications", ("ECE220", "ECE340A", "ECE429", "ECE435A"),
                       r"\b(?:dsp|digital signal processing|wireless|software defined radio|ece ?429|ece ?435a)\b",
                       "Generate a noisy signal, filter it, and compare its frequency spectrum before and after.", "resource:pysdr"),
            StudyRoute("RF & Microwave Engineering", ("ECE220", "ECE381A", "ECE486", "ECE488", "ECE484"),
                       r"\b(?:rf|radio frequency|microwave|antennas?|ece ?48(?:4|6|8))\b",
                       "Simulate a simple impedance mismatch and compare reflected power across frequency."),
        ),
        "Apply signal processing to software-defined radio and next-generation wireless systems.",
        electives=("CSC425",), related_courses=("ECE310", "ECE320A", "ECE381A"),
        foundation_codes=("ECE220",), foundation_query="ECE220 circuits",
    ),
    "controls": CareerPath(
        "Controls & Robotics", "Controls engineer · Automation engineer · Robotics engineer",
        "How can I start learning feedback control for robots?",
        (
            StudyRoute("Industrial Automation & Motion Control", ("ECE220", "ECE320A", "ECE441A", "ECE442", "ECE447A"),
                       r"\b(?:industrial automation|motion control|motor (?:control|speed)|ece ?447a)\b",
                       "Simulate a motor speed controller. Change the gain and compare overshoot and settling time.", "resource:motor_pid"),
            StudyRoute("Robotics & Autonomy", ("ECE220", "ECE320A", "ECE441A", "CSC437", "ECE372A"),
                       r"\b(?:robots?|robotics|autonom(?:y|ous)|motion planning|geometric algorithms|csc ?437)\b",
                       "Simulate a robot following a planned path and measure tracking error at two speeds.", "resource:motor_pid"),
        ),
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
                       r"\b(?:design|verification|asic|rtl|vlsi|verilator|ece ?407|ece ?462)\b",
                       "Simulate a four-bit counter. Write checks for reset, counting and rollover.", "resource:verilator"),
            StudyRoute("Fabrication & test", ("ECE220", "ECE351C", "ECE352", "ECE446"),
                       r"\b(?:fabrication|fab|wafer|manufacturing|product test|process engineer|packaging|ece ?446)\b",
                       "Compare process variation and test yield for two simulated wafer lots."),
        ),
        "Explore digital chip design and semiconductor manufacturing. Advanced packaging connects device, process and test work.",
        electives=("SIE406", "MSE365"),
        foundation_codes=("ECE274A", "ECE369A", "ECE220", "ECE351C", "ECE352"),
        foundation_query="ECE274A digital logic ECE220 circuits",
    ),
    "photonics": CareerPath(
        "Photonics & Electro-Optics",
        "Optical engineer · Electro-optical test engineer · Photonics engineer",
        "What should I learn for Imaging & Optical Systems?",
        (
            StudyRoute("Imaging & Optical Systems", ("ECE220", "ECE381A", "OPTI300", "ECE459"),
                       r"\b(?:optical (?:imaging|systems)|imaging optics|lenses|ece ?459|opti ?300)\b",
                       "Sketch rays for two lens positions and compare the image size and focus.", "resource:wyant_photonics"),
            StudyRoute("Lasers & Optical Communications", ("ECE220", "ECE381A", "ECE370", "ECE430"),
                       r"\b(?:lasers?|optical communications?|fiber optics?|optical link|ece ?370|ece ?430)\b",
                       "Calculate received power in a simulated fiber link with two loss assumptions.", "resource:wyant_photonics"),
        ),
        "Explore optical imaging, laser devices, and the optical links used in communications.",
        electives=("OPTI300",), foundation_codes=("ECE220", "ECE381A"),
        foundation_query="ECE220 circuits ECE381A electromagnetics",
    ),
    "power": CareerPath(
        "Power & Energy Systems",
        "Electrical design engineer · Renewable energy engineer · Power systems engineer",
        "What should I learn for Solar PV & Energy Storage?",
        (
            StudyRoute("Solar PV & Energy Storage", ("ECE220", "ECE320A", "ECE414A"),
                       r"\b(?:solar|photovoltaics?|energy storage|battery storage|ece ?414a)\b",
                       "Plot a fictional solar and load profile and estimate how much energy a battery could shift.", "resource:solar_storage"),
            StudyRoute("Building Electrical Systems", ("ECE220", "ECE320A", "ARCE320"),
                       r"\b(?:building (?:electrical|power)|arce ?320)\b",
                       "Calculate the real and apparent power for a fictional load and compare the two values."),
        ),
        "Use circuit and power concepts to analyze solar systems, storage and building electrical loads.",
        electives=("ARCE320",), foundation_codes=("ECE220", "ECE320A"),
        foundation_query="ECE220 circuits ECE320A AC power",
    ),
    "biomedical": CareerPath(
        "Biomedical Instrumentation & Sensors",
        "Instrumentation engineer · Medical device test engineer · Imaging systems engineer",
        "What should I learn for Biosignals & Instrumentation?",
        (
            StudyRoute("Biosignals & Instrumentation", ("ECE220", "ECE351C", "ECE417", "BME330"),
                       r"\b(?:biosignals?|biomedical instrumentation|physiological|electrocardiogra\w*|ece ?417|bme ?330)\b",
                       "Filter a synthetic pulse signal and measure how the filter changes signal and noise."),
            StudyRoute("Biomedical Imaging", ("ECE220", "ECE381A", "BME416", "ECE429"),
                       r"\b(?:(?:biomedical|medical) imaging|bme ?416)\b",
                       "Compare contrast and resolution in two synthetic images made with different blur settings.", "resource:medical_imaging"),
        ),
        "Apply circuit, measurement, and signal-processing concepts to biomedical instrumentation and imaging.",
        electives=("BME330", "BME416"), foundation_codes=("ECE220", "ECE351C"),
        foundation_query="ECE220 circuits electronics measurement",
    ),
}
CAREER_NAMES = {key: path.name for key, path in CAREER_PATHS.items()} | {"exploring": "Still exploring"}

ELECTIVE_RULE = "https://catalog.arizona.edu/programs/ECEBSECE/program-requirements-a1nCj"
ELECTIVE_GUIDANCE = (
    "The 2026–27 catalog lists 300- and 400-level courses under Technical Electives II, excluding 390s and 490s. "
    "Ask ECE advising whether this course can fulfill that requirement for your catalog year, "
    "and check the section's enrollment requirements before registering."
)

_DIRECTION_CUES = {
    "embedded": r"\b(?:edge ai|on device inference|tinyml|firmware|freertos|rtos|ece ?402c)\b",
    "signals": r"\b(?:digital signal processing|dsp|signals? and communications?|signal processing|"
               r"wireless(?: communications?| systems?| dsp)?|software defined radio|"
               r"rf|radio frequency|microwave|open ran|computer networking|ece ?429|ece ?435a|ece ?48(?:4|6|8)|csc ?425)\b",
    "controls": r"\b(?:controls? and robotics|feedback control|automatic control|digital control|"
                r"robotics|industrial automation|motor control|pid control(?:ler)?|geometric algorithms|"
                r"ece ?441a|ece ?442|ece ?447a|csc ?437)\b",
    "semiconductors": r"\b(?:semiconductors?|digital hardware|chip (?:design|verification|fabrication|manufacturing|testing)|"
                       r"(?:silicon|wafer|chip) fab(?:rication)?|asic|rtl|vlsi|verilator|"
                       r"ece ?407|ece ?446|ece ?462|sie ?406|mse ?365)\b",
    "photonics": r"\b(?:photonics|optics|electro optics|optical (?:communications?|systems|imaging)|lasers?|"
                  r"fiber optics?|opti ?300|ece ?370|ece ?430|ece ?459)\b",
    "power": r"\b(?:power (?:systems?|electronics)|solar|photovoltaics?|(?:energy|battery) storage|"
               r"building (?:electrical|power)|ece ?414a|arce ?320)\b",
    "biomedical": r"\b(?:biomedical|biosignals?|medical (?:imaging|devices?|sensors?)|ece ?417|bme ?330|bme ?416)\b",
}


def question_direction(question):
    """Route an open-ended profile only when one direction clearly matches."""
    normalized = _words(question)
    matches = [key for key, pattern in _DIRECTION_CUES.items() if re.search(pattern, normalized)]
    return matches[0] if len(matches) == 1 else None
