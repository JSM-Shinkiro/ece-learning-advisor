"""Conservative three-state academic rules, independent of generation."""

from __future__ import annotations

from .models import Record, Rule, RuleEvaluation, StudentProfile, normalize_code

STANDING = {"Incoming": 0, "Freshman": 1, "Sophomore": 2, "Junior": 3, "Senior": 4}
GRADES = {"A+": 4.3, "A": 4, "A-": 3.7, "B+": 3.3, "B": 3, "B-": 2.7,
          "C+": 2.3, "C": 2, "C-": 1.7, "D+": 1.3, "D": 1, "D-": .7, "E": 0, "F": 0}


def result(status, reason, rule):
    return RuleEvaluation(status=status, reasons=[reason], evidence_ids=rule.evidence_ids)


def evaluate_rule(rule: Rule, profile: StudentProfile) -> RuleEvaluation:
    kind = rule.type
    if kind in {"all_of", "any_of"}:
        evaluated = [evaluate_rule(child, profile) for child in rule.children]
        statuses = [r.status for r in evaluated]
        if kind == "all_of":
            status = "unsatisfied" if "unsatisfied" in statuses else ("unknown" if "unknown" in statuses else "satisfied")
        else:
            status = "satisfied" if "satisfied" in statuses else ("unknown" if "unknown" in statuses else "unsatisfied")
        return RuleEvaluation(
            status=status,
            reasons=list(dict.fromkeys(reason for r in evaluated for reason in r.reasons)),
            evidence_ids=list(dict.fromkeys(e for r in evaluated for e in r.evidence_ids)),
        )
    if kind == "unknown":
        return result("unknown", rule.note or "The academic requirement needs review.", rule)
    if kind == "none":
        return result("satisfied", "The reviewed source lists no prerequisite for this condition.", rule)
    if kind == "standing":
        actual, required = STANDING.get(profile.standing), STANDING.get(rule.value)
        if actual is None or required is None:
            return result("unknown", "Academic standing needs confirmation.", rule)
        return result("satisfied" if actual >= required else "unsatisfied", f"Standing condition: {rule.value} or above.", rule)
    if kind == "consent":
        confirmed = rule.value in profile.consents
        return result("satisfied" if confirmed else "unknown", "Permission is recorded." if confirmed else "Permission needs confirmation.", rule)
    code = normalize_code(rule.course_code or "")
    completion = next((c for c in profile.completed if c.course_code == code), None)
    if kind == "completed_or_concurrent" and code in profile.current_enrollment:
        return result("satisfied", f"{code} is recorded as concurrent enrollment.", rule)
    if completion is None:
        status = "unsatisfied" if profile.history_complete else "unknown"
        return result(status, f"{code} is not in the supplied completion history.", rule)
    if completion.grade in {"E", "F"}:
        return result("unsatisfied", f"{code} has a failed attempt, not a successful completion.", rule)
    if rule.minimum_grade:
        actual, minimum = GRADES.get(completion.grade), GRADES.get(rule.minimum_grade.upper())
        if actual is None or minimum is None:
            return result("unknown", f"{code} needs a confirmed grade of {rule.minimum_grade} or higher.", rule)
        return result("satisfied" if actual >= minimum else "unsatisfied", f"{code}: grade {completion.grade}, required {rule.minimum_grade}.", rule)
    return result("satisfied", f"{code} is recorded as completed.", rule)


def evaluate_course(course: Record, profile: StudentProfile) -> RuleEvaluation:
    if not course.rule_reviewed:
        return RuleEvaluation(status="unknown", reasons=["The catalog rule has not been resolved and reviewed."])
    if profile.catalog_version != course.catalog_version:
        return RuleEvaluation(status="unknown", reasons=["The student's catalog edition does not match this reviewed rule."])
    return evaluate_rule(course.rule, profile)


def dependency_codes(rule: Rule) -> list[str]:
    """Collect possible dependency references, without declaring every OR branch required."""
    codes = [rule.course_code] if rule.course_code else []
    for child in rule.children:
        codes.extend(dependency_codes(child))
    return list(dict.fromkeys(codes))
