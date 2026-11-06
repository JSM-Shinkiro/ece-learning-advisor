"""Literal course requests prioritize verified links, never guessed catalog URLs."""

import json

import pytest
from pydantic import ValidationError

from src.controller import run_advisor
from src.discovery import DiscoveryPlan, load_discovery_plans, requested_course_codes
from src.models import Completion, Record, StudentProfile
from src.rules import evaluate_course
from src.sources import refresh_catalog
from test_discovery import NOW, client_for, program_page
from test_sources import course_page


ECE_CODES = {"0432591": "ECE201", "0120881": "ECE220", "0360981": "ECE274A"}


def priority_refresh(catalog, path, profile, *, seen=None, programs=None, courses=None,
                     headers=None, plans=None, omit_ece_id=None):
    plans = load_discovery_plans() if plans is None else plans
    records, pages = {}, {}
    proofs = next(r for r in catalog.records if r.code == "CSC120").rule_evidence
    for plan in plans:
        if plan.program_code == "COSCBS":
            entries = plan.reviewed_rules
            ids = {entry.proof.section_id: [entry.course_id] for entry in entries}
            def descriptions(primary, rules):
                for node, entry in zip(rules, entries):
                    node["description"] = entry.proof.reviewed_text
            pages[plan.program_code] = program_page(plan, ids_by_section=ids, proofs=proofs, modify=descriptions)
            labels = {entry.course_id: entry.course_code for entry in entries}
            refs = {entry.course_code: entry.requirement_reference for entry in entries}
        else:
            labels, refs = ECE_CODES, {}
            ids = ["0432351", *(identity for identity in labels if identity != omit_ece_id)]
            pages[plan.program_code] = program_page(plan, ids=ids)
        for identity, code in labels.items():
            records[identity] = Record(record_id="fixture:" + code, kind="course", code=code,
                title="Requested fixture " + code, summary="Fixture programming, circuits, and digital logic.",
                credits=3, source_ids=["fixture"], catalog_version="2026-2027", review_status="synthetic_fixture",
                requirement_reference=refs.get(code, "123456"))
    pages.update(programs or {})
    with client_for(catalog, plans, records, programs=pages, courses=courses, seen=seen, headers=headers) as client:
        return refresh_catalog(catalog, profile, client=client, cache_dir=path, discovery_plans=plans, now=NOW)


def added(result):
    return [r.code for r in result.catalog.records if r.discovery]


def request_status(result, code):
    return next(item["status"] for item in result.discovery_selection["requests"] if item["code"] == code)


@pytest.mark.parametrize("text,expected", [
    ("Can I take ece 201?", ["ECE201"]),
    ("Compare CSC210, ECE220, csc 210 and ECE274A", ["CSC210", "ECE220", "ECE274A"]),
    ("ECE201A differs from ECE201", ["ECE201A", "ECE201"]),
    ("preECE201 ECE201999 ECE201ABC ECE201_suffix", []),
    ("MATH112 CSC525 ECE999 /courses/0432591", []),
    ("ECE\n274A", ["ECE274A"]),
])
def test_priority_parses_only_whole_supported_codes(text, expected):
    codes, origin, truncated = requested_course_codes(StudentProfile(question=text))
    assert codes == expected and origin == "question" and not truncated


def test_question_takes_precedence_over_interests_and_other_profile_fields():
    profile = StudentProfile(question="Which ECE201 topics?", interests="CSC210", experience="ECE220",
        completed=[Completion(course_code="ECE274A", grade="B")])
    assert requested_course_codes(profile) == (["ECE201"], "question", False)
    profile.question = "A general programming question"
    assert requested_course_codes(profile)[0] == []
    profile.question = "  "
    assert requested_course_codes(profile) == (["CSC210"], "interests", False)
    assert requested_course_codes(StudentProfile()) == ([], "none", False)


def test_priority_caps_distinct_mentions_without_creating_downloads():
    profile = StudentProfile(question=" ".join("ECE" + str(100 + i) for i in range(18)))
    codes, _, truncated = requested_course_codes(profile)
    assert len(codes) == 16 and codes[-1] == "ECE115" and truncated


def test_empty_question_preserves_existing_source_order(catalog, tmp_path):
    result = priority_refresh(catalog, tmp_path, StudentProfile())
    assert added(result) == ["CSC110", "CSC144", "CSC210"]
    assert all(row["reason"] == "source_order" for row in result.discovery_selection["selected"])


@pytest.mark.parametrize("code", ["ECE201", "ECE220", "ECE274A"])
def test_requested_ece_foundation_displaces_a_later_cs_candidate(catalog, tmp_path, code):
    seen = []
    result = priority_refresh(catalog, tmp_path, StudentProfile(question="Prepare for " + code), seen=seen)
    assert added(result) == [code, "CSC110", "CSC144"]
    assert request_status(result, code) == "added"
    assert result.discovery_selection["selected"][0]["reason"] == "requested_course"
    assert len([url for url in seen if "/courses/" in url]) == 6
    assert len([url for url in seen if "/programs/" in url]) == 2
    record = next(r for r in result.catalog.records if r.code == code)
    assert not record.rule_reviewed and evaluate_course(record, StudentProfile()).status == "unknown"


def test_ordered_multiple_requests_share_the_same_cap(catalog, tmp_path):
    result = priority_refresh(catalog, tmp_path,
        StudentProfile(question="Compare ECE220, CSC210, ECE201, then CSC144"))
    assert added(result) == ["ECE220", "CSC210", "ECE201"]
    assert request_status(result, "CSC144") == "budget_limit"
    assert result.discovery_selection["requested_codes"] == ["ECE220", "CSC210", "ECE201", "CSC144"]


@pytest.mark.parametrize("available,expected", [(0, []), (1, ["ECE201"]), (2, ["ECE201", "ECE220"])])
def test_priority_respects_remaining_course_download_slots(catalog, tmp_path, monkeypatch, available, expected):
    monkeypatch.setattr("src.sources.MAX_SOURCES", 3 + available)
    seen = []
    result = priority_refresh(catalog, tmp_path,
        StudentProfile(question="ECE201, ECE220, CSC210"), seen=seen)
    assert added(result) == expected
    assert len([url for url in seen if "/courses/" in url]) == 3 + available
    assert request_status(result, "CSC210") == "budget_limit"


def test_interests_can_prioritize_when_question_is_empty(catalog, tmp_path):
    result = priority_refresh(catalog, tmp_path, StudentProfile(interests="C++ and ECE201"))
    assert added(result)[0] == "ECE201" and result.discovery_selection["input"] == "interests"


def test_existing_course_uses_no_new_discovery_slot(catalog, tmp_path):
    result = priority_refresh(catalog, tmp_path, StudentProfile(question="ECE425 and ECE201"))
    assert request_status(result, "ECE425") == "in_collection"
    assert added(result) == ["ECE201", "CSC110", "CSC144"]


def test_priority_keeps_the_selected_career_source_scope(catalog, tmp_path):
    seen = []
    result = priority_refresh(catalog, tmp_path,
        StudentProfile(career_id="embedded", question="CSC210 and ECE274A"), seen=seen)
    assert added(result) == ["ECE274A", "ECE201", "ECE220"]
    assert request_status(result, "CSC210") == "not_available"
    assert not any("/COSCBS/" in url for url in seen)


def test_unknown_requested_code_cannot_create_a_url_or_model_answer(catalog, tmp_path):
    seen = []
    def refresh(catalog, profile, **kwargs):
        return priority_refresh(catalog, tmp_path / "sources", profile, seen=seen)
    def forbidden(*args, **kwargs):
        pytest.fail("An unavailable exact course must not initialize the model")
    result = run_advisor(catalog, StudentProfile(question="ECE499"), use_ai=True, api_key="fixture",
        provider_factory=forbidden, source_refresher=refresh)
    assert result.coverage_notice and not result.context.allowed_record_ids
    assert result.trace["source_refresh"]["discovery_selection"]["requests"] == [{"code": "ECE499", "status": "not_available"}]
    assert not any("ECE499" in url for url in seen)


def test_manifest_hint_without_a_live_section_link_cannot_select_a_course(catalog, tmp_path):
    seen = []
    result = priority_refresh(catalog, tmp_path, StudentProfile(question="ECE201"),
        omit_ece_id="0432591", seen=seen)
    assert request_status(result, "ECE201") == "not_available"
    assert not any(url.endswith("0432591") for url in seen)


def test_failed_program_check_cannot_use_stale_links_for_priority(catalog, tmp_path):
    profile = StudentProfile(question="ECE201")
    priority_refresh(catalog, tmp_path, profile)
    seen = []
    result = priority_refresh(catalog, tmp_path, profile, programs={"ECEBSECE": 503}, seen=seen)
    assert added(result) == ["CSC110", "CSC144", "CSC210"]
    assert request_status(result, "ECE201") == "not_available"
    assert not any(url.endswith("0432591") for url in seen)


def test_changed_question_reuses_only_public_cache_metadata_not_old_priority(catalog, tmp_path):
    first = priority_refresh(catalog, tmp_path, StudentProfile(question="route-private-sentinel ECE201"),
        headers={"ETag": '"fixture-program"'})
    second = priority_refresh(catalog, tmp_path, StudentProfile(question="ECE274A"),
        programs={"COSCBS": 304, "ECEBSECE": 304})
    assert added(first)[0] == "ECE201" and added(second)[0] == "ECE274A"
    assert request_status(first, "ECE201") == request_status(second, "ECE274A") == "added"
    assert all("route-private-sentinel" not in path.read_text() for path in tmp_path.rglob("*.json"))


@pytest.mark.parametrize("code,identity", [("ECE201", "0432591"), ("CSC210", "0393711")])
def test_fetched_code_must_confirm_the_routing_hint_even_on_304(catalog, tmp_path, code, identity):
    record = Record(record_id="fixture:ECE202", code="ECE202", kind="course", title="Wrong fixture code",
        summary="Fixture mismatched course identity.", credits=3, source_ids=["fixture"], catalog_version="2026-2027")
    wrong = course_page(record, course_id=identity)
    profile = StudentProfile(question=code)
    first = priority_refresh(catalog, tmp_path, profile, courses={identity: wrong}, headers={"ETag": '"fixture-course"'})
    second = priority_refresh(catalog, tmp_path, profile, courses={identity: 304}, programs={"COSCBS": 304, "ECEBSECE": 304})
    for result in [first, second]:
        assert code not in added(result) and "ECE202" not in added(result)
        assert request_status(result, code) == "unavailable"
        check = next(c for c in result.checks if c.code == code)
        assert check.status == "unavailable" and check.failure_kind == "validation"


def test_failed_target_has_no_hidden_extra_download_or_placeholder(catalog, tmp_path):
    seen = []
    result = priority_refresh(catalog, tmp_path, StudentProfile(question="ECE201"),
        courses={"0432591": 503}, seen=seen)
    assert added(result) == ["CSC110", "CSC144"]
    assert request_status(result, "ECE201") == "unavailable"
    assert len({url for url in seen if "/courses/" in url}) == 6
    assert sum(url.endswith("0432591") for url in seen) == 2
    assert next(c for c in result.checks if c.url.endswith("0432591")).retry_count == 1


def test_cached_target_failure_is_labeled_stale_without_academic_approval(catalog, tmp_path):
    profile = StudentProfile(question="ECE201")
    priority_refresh(catalog, tmp_path, profile)
    result = priority_refresh(catalog, tmp_path, profile, courses={"0432591": 503})
    assert request_status(result, "ECE201") == "stale_added"
    record = next(r for r in result.catalog.records if r.code == "ECE201")
    assert evaluate_course(record, profile).status == "unknown"


@pytest.mark.parametrize("codes", [{"bad": "ECE201"}, {"0432591": "ECE999"},
    {"0432591": "ece201"}, {"0432591": "ECE201", "0120881": "ECE201"},
    {"0393681": "CSC144"}, {"7654321": "CSC110"}])
def test_ambiguous_or_malformed_routing_bindings_are_rejected(codes):
    plan = load_discovery_plans()[0].model_dump(mode="json")
    plan["course_codes"] = codes
    with pytest.raises(ValidationError):
        DiscoveryPlan.model_validate(plan)


def test_conflicting_bindings_across_programs_are_rejected(tmp_path):
    plans = [p.model_dump(mode="json") for p in load_discovery_plans()]
    plans[0]["course_codes"] = {"7654321": "ECE201"}
    path = tmp_path / "plans.json"
    path.write_text(json.dumps(plans))
    with pytest.raises(ValueError, match="identities"):
        load_discovery_plans(path)


@pytest.mark.parametrize("code", ["ECE201", "ECE274A"])
def test_prioritized_course_reaches_grounded_generation_with_unknown_rule(catalog, tmp_path, fake_provider, code):
    fake_provider.close = lambda: None
    def refresh(catalog, profile, **kwargs):
        return priority_refresh(catalog, tmp_path / "sources", profile)
    result = run_advisor(catalog, StudentProfile(question="How should I prepare for " + code + "?"),
        use_ai=True, api_key="fixture", provider_factory=lambda *a, **k: fake_provider,
        source_refresher=refresh, cache_dir=tmp_path / "vectors")
    rid = "uofa:" + code + ":2026-2027"
    assert result.generation_complete and result.statement_validation_passed
    assert rid in result.context.allowed_record_ids
    assert rid in result.trace["focused_record_ids"]
    assert result.context.rule_results[rid].status == "unknown"
    assert fake_provider.context.field_sources[rid]["summary"] == "catalog:" + code
