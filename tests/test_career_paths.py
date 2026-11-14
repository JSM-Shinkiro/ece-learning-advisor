import pytest

from src.career_catalog import with_career_paths
from src.career_paths import CAREER_PATHS, question_direction
from src.catalog import load_runtime_catalog
from src.controller import run_advisor
from src.models import StudentProfile
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
    for direction in ("signals", "controls"):
        path = CAREER_PATHS[direction]
        mapped = {record.code for record in combined.records if direction in record.career_ids}
        assert {*path.progression, path.elective} <= mapped
