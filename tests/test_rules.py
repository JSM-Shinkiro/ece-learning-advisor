import pytest
from pydantic import ValidationError

from src.models import Completion, Rule, StudentProfile
from src.rules import evaluate_course, evaluate_rule


def completed(code="ECE101", grade=None):
    return Rule(type="completed", course_code=code, minimum_grade=grade)


def test_incomplete_history_is_unknown():
    assert evaluate_rule(completed(),StudentProfile()).status == "unknown"


def test_complete_history_makes_absence_unsatisfied():
    assert evaluate_rule(completed(),StudentProfile(history_complete=True)).status == "unsatisfied"


def test_missing_minimum_grade_stays_unknown():
    profile=StudentProfile(completed=[Completion(course_code="ECE101")])
    assert evaluate_rule(completed(grade="C"),profile).status == "unknown"


@pytest.mark.parametrize("actual,expected",[("B","satisfied"),("D","unsatisfied"),("P","unknown")])
def test_grade_conditions(actual,expected):
    p=StudentProfile(completed=[Completion(course_code="ECE101",grade=actual)])
    assert evaluate_rule(completed(grade="C"),p).status == expected


def test_or_does_not_require_both_branches():
    rule=Rule(type="any_of",children=[completed(),completed("CSC110")])
    p=StudentProfile(completed=[Completion(course_code="ECE101")])
    assert evaluate_rule(rule,p).status == "satisfied"


def test_and_false_dominates_unknown():
    rule=Rule(type="all_of",children=[completed(),Rule(type="unknown")])
    assert evaluate_rule(rule,StudentProfile(history_complete=True)).status == "unsatisfied"


def test_or_unknown_dominates_false():
    rule=Rule(type="any_of",children=[completed(),Rule(type="unknown")])
    assert evaluate_rule(rule,StudentProfile(history_complete=True)).status == "unknown"


def test_concurrent_and_standing():
    p=StudentProfile(current_enrollment=["ECE 101"],standing="Senior")
    assert evaluate_rule(Rule(type="completed_or_concurrent",course_code="ECE101"),p).status=="satisfied"
    assert evaluate_rule(Rule(type="standing",value="Junior"),p).status=="satisfied"


def test_empty_rule_rejected():
    with pytest.raises(ValidationError):
        Rule(type="all_of")


def test_unreviewed_catalog_rules_do_not_pass(catalog):
    p=StudentProfile(standing="Senior",history_complete=True)
    for course in [r for r in catalog.records if r.kind=="course" and not r.rule_reviewed]:
        assert evaluate_course(course,p).status=="unknown"


def test_catalog_version_mismatch(catalog):
    course=next(r for r in catalog.records if r.kind=="course").model_copy(deep=True)
    course.rule_reviewed=True
    course.rule=Rule(type="none")
    assert evaluate_course(course,StudentProfile(catalog_version="2025-2026")).status=="unknown"
