import pytest

from src.career_catalog import with_career_paths
from src.career_paths import CAREER_PATHS, question_direction
from src.catalog import load_runtime_catalog
from src.controller import run_advisor
from src.models import Completion, StudentProfile
from src.opportunities import CAREER_PATTERNS
from src.profiles import export_profile, import_profile
from src.sources import CatalogRefresh


@pytest.mark.parametrize("direction,question,bridge,goal,practice", [
    ("signals", "What courses teach wireless DSP?", "ECE340A", "ECE429", "pysdr"),
    ("controls", "How can I learn feedback control for robots?", "ECE320A", "ECE441A", "motor_pid"),
])
def test_exploring_question_uses_one_new_direction_in_early_and_final_plans(direction, question, bridge, goal, practice):
    catalog = load_runtime_catalog()
    before = catalog.model_dump_json()
    profile = StudentProfile(career_id="exploring", question=question)
    previews = []
    result = run_advisor(catalog, profile, on_plan=previews.append,
                         source_refresher=lambda active, *_args, **_kwargs: CatalogRefresh(active))
    assert profile.career_id == "exploring" and catalog.model_dump_json() == before
    assert len(previews) == 1
    for plan in [*previews, result]:
        context = plan.context
        assert context.profile.career_id == direction
        assert plan.trace["career_direction"] == {"from": "exploring", "matched": direction}
        assert [rid.split(":")[1] for rid in context.allowed_record_ids] == ["ECE220", bridge, goal, practice]
        assert all(rule.status == "unknown" for rule in context.rule_results.values())


@pytest.mark.parametrize("direction,elective,other", [("signals", "CSC425", "CSC437"), ("controls", "CSC437", "CSC425")])
def test_explicit_elective_uses_its_course_source_and_keeps_enrollment_unverified(direction, elective, other):
    catalog = load_runtime_catalog()
    profile = StudentProfile(career_id=direction, question=f"Can {elective} count as an ECE elective?",
                             current_enrollment=["ECE220"])
    assert import_profile(export_profile(profile)) == profile
    result = run_advisor(catalog, profile, refresh_sources=False)
    rid = f"uofa:{elective}:2026-2027"
    assert rid in result.context.allowed_record_ids
    assert all(":ECE220:" not in rid for rid in result.context.allowed_record_ids)
    assert result.context.rule_results[rid].status == "unknown"
    assert result.context.field_sources[rid]["credits"] == "catalog:" + elective
    assert not any(r.code == other for r in result.catalog.records)
    assert direction in CAREER_PATTERNS


def test_combined_collection_extends_each_path_once_and_ambiguous_questions_remain_open():
    catalog = load_runtime_catalog()
    combined = with_career_paths(catalog)
    assert with_career_paths(combined) == combined
    assert not question_direction("I'm interested in wireless DSP and feedback control.")
    assert not question_direction("I want to learn wireless DSP and semiconductor fabrication.")
    for direction, path in CAREER_PATHS.items():
        assert len(path.routes) >= 2
        mapped = {record.code for record in combined.records if direction in record.career_ids}
        assert {*path.progression, *path.electives} <= mapped


@pytest.mark.parametrize("question", [
    "How to combine AI and Robotics?",
    "What should I learn to build autonomous robots that use computer vision?",
    "How can I use A.I. for robotic perception?",
    "How can I run object detection on a mobile robot?",
])
def test_mixed_ai_and_robotics_questions_offer_two_starts_without_provider_calls(question):
    def unexpected_call(*_args, **_kwargs):
        pytest.fail("Choosing a starting direction should not check sources or use a provider")

    result = run_advisor(load_runtime_catalog(), StudentProfile(career_id="exploring", question=question),
                         api_key="controlled", use_ai=True, provider_factory=unexpected_call,
                         source_refresher=unexpected_call)
    assert result.direction_choices == ("ai_ml", "controls")
    assert not result.context.allowed_record_ids and result.trace["model_calls"] == 0


def test_related_direction_persists_in_saved_and_checked_roadmaps():
    profile = StudentProfile(career_id="controls", question="Robotic perception",
                             completed=[Completion(course_code="ECE220", grade="B")])
    previews = []
    result = run_advisor(load_runtime_catalog(), profile, on_plan=previews.append,
                         source_refresher=lambda active, *_args, **_kwargs: CatalogRefresh(active))
    assert len(previews) == 1
    for plan in [*previews, result]:
        assert plan.context.profile == profile and not plan.direction_choices and not plan.coverage_notice
        assert plan.trace["study_route"] == "Robotics & Autonomy"
        assert plan.trace["related_directions"] == ["ai_ml"]
        assert "uofa:ECE441A:2026-2027" in plan.context.allowed_record_ids
        assert "uofa:ECE220:2026-2027" not in plan.context.allowed_record_ids


def test_interests_can_suggest_a_second_direction_without_replacing_a_saved_one():
    catalog = load_runtime_catalog()
    profile = StudentProfile(career_id="ai_ml", interests="AI and robotics")
    result = run_advisor(catalog, profile, refresh_sources=False)
    assert result.context.profile == profile and not result.direction_choices
    assert result.trace["related_directions"] == ["controls"]

    profile = profile.model_copy(update={"interests": "Edge AI on a microcontroller"})
    result = run_advisor(catalog, profile, refresh_sources=False)
    assert result.context.profile == profile and not result.direction_choices
    assert result.trace["study_route"] == "Edge AI & On-Device Inference"
    assert "related_directions" not in result.trace


@pytest.mark.parametrize("question,completed,start,goal,unrelated", [
    ("I finished ECE 369A. What should I learn next for digital chip verification?",
     ["ECE369A"], "ECE274A", "ECE407", "ECE446"),
    ("How should I start learning chip fabrication for a wafer fab process role?",
     [], "ECE220", "ECE446", "ECE407"),
])
def test_semiconductor_questions_use_the_relevant_study_route(question, completed, start, goal, unrelated):
    profile = StudentProfile(career_id="exploring", question=question,
                             completed=[Completion(course_code=code, grade="A") for code in completed])
    catalog = load_runtime_catalog()
    result = run_advisor(catalog, profile, refresh_sources=False)
    assert result.context.profile.career_id == "semiconductors"
    assert result.trace["career_direction"]["matched"] == "semiconductors"
    allowed = {rid.split(":")[1] for rid in result.context.allowed_record_ids}
    assert {start, goal} <= allowed
    assert not allowed.intersection({*completed, unrelated, "SIE406", "MSE365"})
    assert all(rule.status == "unknown" for rule in result.context.rule_results.values())
    assert import_profile(export_profile(result.context.profile)) == result.context.profile


def test_two_explicit_semiconductor_electives_enter_an_incoming_students_plan():
    profile = StudentProfile(career_id="exploring", question="Can SIE 406 and MSE 365 count as technical electives?")
    result = run_advisor(load_runtime_catalog(), profile, refresh_sources=False)
    for code in ("SIE406", "MSE365"):
        rid = f"uofa:{code}:2026-2027"
        assert rid in result.context.allowed_record_ids
        assert result.context.rule_results[rid].status == "unknown"
        assert result.context.field_sources[rid]["credits"] == "catalog:" + code
    assert "semiconductors" in CAREER_PATTERNS


@pytest.mark.parametrize("direction,route", [
    pytest.param(direction, route, id=f"{direction}-{route.label}")
    for direction, path in CAREER_PATHS.items() for route in path.routes
])
def test_selected_specialization_suggests_unrecorded_courses_from_its_sequence(direction, route):
    profile = StudentProfile(career_id=direction, question=route.starting_question,
                             completed=[Completion(course_code=route.courses[0], grade="A")],
                             current_enrollment=[route.courses[1]])
    result = run_advisor(load_runtime_catalog(), profile, refresh_sources=False)
    assert result.trace["study_route"] == route.label
    assert not result.coverage_notice
    courses = [rid.split(":")[1] for rid in result.context.allowed_record_ids if rid.startswith("uofa:")]
    assert courses == list(route.courses[2:5])
    if route.resource_id:
        assert route.resource_id in result.context.allowed_record_ids
    assert route.practice and direction in CAREER_PATTERNS
    assert import_profile(export_profile(profile)) == profile


@pytest.mark.parametrize("question,direction,route,goal", [
    ("How should I learn optical imaging?", "photonics", "Imaging & Optical Systems", "ECE459"),
    ("What courses introduce building electrical systems?", "power", "Building Electrical Systems", "ARCE320"),
    ("Which course should I take for biomedical imaging?", "biomedical", "Biomedical Imaging", "BME416"),
    ("How can I learn on-device inference?", "embedded", "Edge AI & On-Device Inference", "ECE372A"),
])
def test_exploring_specialization_routes_to_the_matching_direction(question, direction, route, goal):
    result = run_advisor(load_runtime_catalog(), StudentProfile(career_id="exploring", question=question),
                         refresh_sources=False)
    assert result.trace["career_direction"]["matched"] == direction
    assert result.trace["study_route"] == route
    rid = f"uofa:{goal}:2026-2027"
    assert rid in result.context.allowed_record_ids
    assert result.context.rule_results[rid].status == "unknown"


def test_a_specific_course_request_is_kept_alongside_a_named_specialization():
    profile = StudentProfile(career_id="signals",
        question="For DSP & Wireless Communications, can I also learn about ECE 488?",
        current_enrollment=["ECE220"])
    result = run_advisor(load_runtime_catalog(), profile, refresh_sources=False)
    assert result.trace["study_route"] == "DSP & Wireless Communications"
    assert "uofa:ECE488:2026-2027" in result.context.allowed_record_ids
