import json

import pytest
from pydantic import ValidationError

from src.controller import run_advisor
from src.models import Completion, GeneratedAnswer, Rule, StudentProfile
from src.planning import format_duration
from src.profiles import MAX_PROFILE_BYTES, edit_profile, export_profile, import_profile, merge_completions
from src.providers import ProviderError
from src.rules import evaluate_rule
from src.service import recommend
from src.session import apply_profile, choose_direction, complete_course, restore_profile


@pytest.mark.parametrize("grade",["E","F","f"])
def test_failed_attempt_cannot_enter_completed_history(grade):
    with pytest.raises(ValidationError,match="Failed attempts"):
        Completion(course_code="ECE101",grade=grade)


def test_failed_legacy_object_does_not_pass_completion_rule():
    legacy=Completion.model_construct(course_code="ECE101",grade="F")
    profile=StudentProfile.model_construct(completed=[legacy])
    assert evaluate_rule(Rule(type="completed",course_code="ECE101"),profile).status=="unsatisfied"


@pytest.mark.parametrize("background",["some","experienced"])
def test_programming_familiarity_alone_does_not_promote_deep_learning(catalog,background):
    result=recommend(catalog,StudentProfile(programming_background=background))
    assert result.context.suggested_phases["uofa:ECE425:2026-2027"]=="later"


def test_blocked_course_stays_later_even_for_experienced_student(catalog):
    changed=catalog.model_copy(deep=True)
    course=next(r for r in changed.records if r.code=="ECE425")
    course.rule_reviewed=True
    course.rule=Rule(type="completed",course_code="CSC120")
    result=recommend(changed,StudentProfile(programming_background="experienced",history_complete=True))
    assert result.context.rule_results[course.record_id].status=="unsatisfied"
    assert result.context.suggested_phases[course.record_id]=="later"


def test_real_csc120_alternative_is_sufficient_without_all_alternative_records(catalog):
    profile=StudentProfile(completed=[Completion(course_code="ECE101",grade="B")])
    result=recommend(catalog,profile)
    assert result.context.rule_results["uofa:CSC120:2026-2027"].status=="satisfied"


def test_exploring_keeps_both_career_goals(catalog):
    result=recommend(catalog,StudentProfile(career_id="exploring",interests="AI and Hardware Integration"))
    assert {"uofa:ECE425:2026-2027","uofa:ECE372A:2026-2027"} <= set(result.context.allowed_record_ids)
    assert result.context.suggested_phases["resource:pytorch"]=="later"
    assert result.context.suggested_phases["resource:cs50"]=="next"


def test_beginner_gets_bridge_course_in_chosen_direction(catalog):
    result=recommend(catalog,StudentProfile())
    assert "uofa:CSC120:2026-2027" in result.context.allowed_record_ids
    assert result.context.suggested_phases["uofa:CSC120:2026-2027"]=="build"


def test_outside_collection_does_not_call_provider(catalog,fake_provider,tmp_path):
    result=recommend(catalog,StudentProfile(),"I want a marine biology degree and ocean fieldwork",
                     provider=fake_provider,cache_dir=tmp_path)
    assert result.coverage_notice
    assert result.context.allowed_record_ids==[]
    assert fake_provider.context is None and fake_provider.document_calls==0
    assert not result.generation_complete


def test_generic_question_is_supported(catalog):
    assert recommend(catalog,StudentProfile(),"What should I learn next?").context.allowed_record_ids


def test_abstention_is_not_successful_recommendation(catalog,fake_provider,tmp_path):
    fake_provider.generate=lambda _:GeneratedAnswer(status="insufficient_evidence",clarification="Which topic do you mean?")
    result=recommend(catalog,StudentProfile(),provider=fake_provider,cache_dir=tmp_path)
    assert not result.generation_complete
    assert result.generation_status=="insufficient_evidence"
    assert result.trace["reference_checks_passed"] is True


def test_profile_edit_preserves_fields_not_in_form():
    original=StudentProfile(current_enrollment=["MATH129"],consents=["permission"],question="Programming next steps")
    edited=edit_profile(original,interests="robotics")
    assert edited.current_enrollment==original.current_enrollment and edited.consents==original.consents
    assert import_profile(export_profile(edited).encode())==edited


def test_restore_and_completion_invalidate_dependent_state():
    state={"profile":StudentProfile(),"result":"old","job_result":"old","jobs_cache":"old"}
    restore_profile(state,export_profile(StudentProfile(career_id="embedded",current_enrollment=["MATH129"])).encode())
    assert not {"result","job_result","jobs_cache"} & state.keys()
    complete_course(state,"ECE101")
    complete_course(state,"ECE101")
    assert len(state["profile"].completed)==1
    assert state["profile"].current_enrollment==["MATH129"]
    assert state["refresh_pending"]


def test_course_picker_preserves_known_grades_and_allows_manual_override():
    previous=[Completion(course_code="ECE101",grade="B")]
    assert merge_completions(["ECE101"],"MATH129",previous)[0].grade=="B"
    assert merge_completions(["ECE101"],"ECE101:C",previous)[0].grade=="C"


def test_provider_initialization_failure_has_current_profile_fallback(catalog):
    def fail(*args,**kwargs):
        raise ProviderError("Do not display raw provider details")
    profile=StudentProfile(career_id="embedded")
    result=run_advisor(catalog,profile,use_ai=True,api_key="dummy",provider_factory=fail)
    assert result.context.profile==profile
    assert result.context.allowed_record_ids and result.issues
    assert not result.generation_complete


def test_profile_limit_matches_one_megabyte_uploader():
    assert MAX_PROFILE_BYTES==1024*1024
    with pytest.raises(ValueError,match="too large"):
        import_profile(json.dumps({"interests":"x"*MAX_PROFILE_BYTES}).encode())


def test_subsecond_timing_is_not_rounded_to_zero():
    assert format_duration(.0009853)=="1.0 ms"
