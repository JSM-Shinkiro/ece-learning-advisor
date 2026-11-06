"""Bounded ECE core discovery and learning stages, never enrollment approval."""

import pytest
from pydantic import ValidationError

from src.catalog import corpus_hash
from src.controller import run_advisor
from src.discovery import DiscoveryPlan, load_discovery_plans, match_course_requests
from src.models import Completion, Record, StudentProfile
from src.planning import learning_phase
from src.rules import evaluate_course
from src.sources import refresh_catalog
from test_discovery import NOW, client_for, program_page
from test_discovery_priority import added, request_status
from test_sources import course_page

CORE = {"0362401": "ECE310", "0397381": "ECE311", "0121101": "ECE320A",
        "0377871": "ECE340A", "0366011": "ECE351C", "0121261": "ECE373"}
FOUNDATIONS = {"0432591": "ECE201", "0120881": "ECE220", "0360981": "ECE274A"}


def core_refresh(catalog, path, profile, *, seen=None, programs=None, courses=None, headers=None, omit=None, plans=None):
    plans = load_discovery_plans() if plans is None else plans
    pages, records = {}, {}
    proofs = next(r for r in catalog.records if r.code == "CSC120").rule_evidence
    for plan in plans:
        if plan.program_code == "COSCBS":
            labels = {entry.course_id: entry.course_code for entry in plan.reviewed_rules}
            refs = {entry.course_code: entry.requirement_reference for entry in plan.reviewed_rules}
            ids = {entry.proof.section_id: [entry.course_id] for entry in plan.reviewed_rules}
            def descriptions(primary, nodes):
                for node, entry in zip(nodes, plan.reviewed_rules):
                    node["description"] = entry.proof.reviewed_text
            pages[plan.program_code] = program_page(plan, ids_by_section=ids, proofs=proofs, modify=descriptions)
        else:
            labels, refs = {**FOUNDATIONS, **CORE}, {}
            ids = {"R17348/L320": ["0432351", *FOUNDATIONS],
                   "R15612/L10": [*list(CORE)[:5], "0367521"],
                   "R15487/L10": ["0366021", "0121261"]}
            ids = {section: [identity for identity in values if identity != omit] for section, values in ids.items()}
            pages[plan.program_code] = program_page(plan, ids_by_section=ids)
        for identity, code in labels.items():
            records[identity] = Record(record_id="fixture:" + code, kind="course", code=code,
                title="Fixture " + code, summary="Fixture engineering mathematics, circuits, and software concepts.",
                credits=3, source_ids=["fixture"], catalog_version="2026-2027", review_status="synthetic_fixture",
                requirement_reference=refs.get(code, "123456"))
    pages.update(programs or {})
    with client_for(catalog, plans, records, programs=pages, courses=courses, seen=seen, headers=headers) as client:
        return refresh_catalog(catalog, profile, client=client, cache_dir=path, discovery_plans=plans, now=NOW)


@pytest.mark.parametrize("identity,code", list(CORE.items()))
def test_requested_core_course_has_verified_provenance_and_unknown_condition(catalog, tmp_path, identity, code):
    seen = []
    before = corpus_hash(catalog)
    result = core_refresh(catalog, tmp_path, StudentProfile(question=code), seen=seen)
    record = next(r for r in result.catalog.records if r.code == code)
    assert added(result) == [code, "CSC110", "CSC144"]
    assert record.study_stage == "intermediate" and not record.rule_reviewed and not record.rule_evidence
    assert evaluate_course(record, StudentProfile()).status == "unknown"
    assert learning_phase(record, StudentProfile(), evaluate_course(record, StudentProfile())) == "build"
    assert record.discovery.course_id == identity
    assert record.discovery.section_ids == (["R15487/L10"] if code == "ECE373" else ["R15612/L10"])
    assert record.field_sources["summary"] == "catalog:" + code
    assert len([url for url in seen if "/courses/" in url]) == 6
    assert len([url for url in seen if "/programs/" in url]) == 2
    trace = result.trace()["discovered_courses"][record.record_id]
    assert trace["study_stage"] == "intermediate" and trace["stage_origin"] == "team_learning_annotation"
    assert corpus_hash(catalog) == before


@pytest.mark.parametrize("phrase,code", [("eigenvalues", "ECE310"), ("engineering ethics", "ECE311"),
    ("circuit theory", "ECE320A"), ("pulse shaping", "ECE340A"),
    ("small-signal models", "ECE351C"), ("class hierarchies", "ECE373")])
def test_new_reviewed_phrases_select_bound_core_courses(catalog, tmp_path, phrase, code):
    assert match_course_requests(StudentProfile(question=phrase), load_discovery_plans()).codes == [code]
    result = core_refresh(catalog, tmp_path, StudentProfile(question=phrase))
    assert added(result)[0] == code and request_status(result, code) == "added"
    assert result.discovery_selection["selected"][0]["reason"] == "reviewed_phrase"


@pytest.mark.parametrize("career", ["ai_ml", "embedded", "exploring"])
def test_core_topics_reach_grounded_generation_in_each_supported_direction(catalog, tmp_path, fake_provider, career):
    fake_provider.close = lambda: None
    def refresher(catalog, profile, **kwargs): return core_refresh(catalog, tmp_path / "sources", profile)
    result = run_advisor(catalog, StudentProfile(career_id=career, question="class hierarchies"),
        source_refresher=refresher, provider_factory=lambda *a, **k: fake_provider,
        use_ai=True, api_key="fixture", cache_dir=tmp_path / "vectors")
    rid = "uofa:ECE373:2026-2027"
    assert result.generation_complete and result.statement_validation_passed
    assert result.trace["focused_record_ids"] == [rid]
    assert rid in result.context.allowed_record_ids and result.context.suggested_phases[rid] == "build"
    assert result.context.rule_results[rid].status == "unknown"
    assert "ECE373" in result.trace["discovery_query_terms"]


def test_novice_and_existing_direction_defaults_stay_in_source_order(catalog, tmp_path):
    ai = core_refresh(catalog, tmp_path / "ai", StudentProfile())
    embedded = core_refresh(catalog, tmp_path / "embedded", StudentProfile(career_id="embedded"))
    assert added(ai) == ["CSC110", "CSC144", "CSC210"]
    assert added(embedded) == ["ECE201", "ECE220", "ECE274A"]
    assert all(r.study_stage == "foundation" for r in embedded.catalog.records if r.discovery)


def test_completed_foundations_release_discovery_slots_for_core_courses(catalog, tmp_path):
    seen = []
    profile = StudentProfile(career_id="embedded", completed=[Completion(course_code=code, grade="B")
        for code in FOUNDATIONS.values()], programming_background="experienced")
    result = core_refresh(catalog, tmp_path, profile, seen=seen)
    assert added(result) == ["ECE310", "ECE311", "ECE320A"]
    assert result.discovery_selection["skipped_completed_codes"] == sorted(FOUNDATIONS.values())
    assert not any(url.rsplit('/', 1)[-1] in FOUNDATIONS for url in seen)
    assert len([url for url in seen if "/courses/" in url]) == 6


@pytest.mark.parametrize("grade", [None, "B", "P", "D"])
def test_completion_filters_suggestions_without_reinterpreting_grades(catalog, tmp_path, grade):
    profile = StudentProfile(career_id="embedded", question="ECE201 and ECE373",
        completed=[Completion(course_code="ECE201", grade=grade)])
    seen = []
    result = core_refresh(catalog, tmp_path, profile, seen=seen)
    assert added(result) == ["ECE373", "ECE220", "ECE274A"]
    assert request_status(result, "ECE201") == "completed"
    assert not any(url.endswith("0432591") for url in seen)
    assert all(evaluate_course(r, profile).status == "unknown" for r in result.catalog.records if r.discovery)


def test_concurrent_courses_still_receive_descriptive_discovery(catalog, tmp_path):
    result = core_refresh(catalog, tmp_path, StudentProfile(career_id="embedded", question="ECE201",
        current_enrollment=["ECE201"]))
    assert added(result)[0] == "ECE201" and request_status(result, "ECE201") == "added"


def test_completed_phrase_is_reported_and_cannot_become_a_generation_focus(catalog, tmp_path):
    profile = StudentProfile(question="class hierarchies", completed=[Completion(course_code="ECE373", grade="B")])
    def refresher(catalog, profile, **kwargs): return core_refresh(catalog, tmp_path, profile)
    def forbidden(*a, **k): pytest.fail("A completed phrase target cannot initialize generation")
    result = run_advisor(catalog, profile, source_refresher=refresher, provider_factory=forbidden, api_key="fixture", use_ai=True)
    assert result.coverage_notice and not result.context.allowed_record_ids
    request = result.trace["source_refresh"]["discovery_selection"]["requests"][0]
    assert request["code"] == "ECE373" and request["status"] == "completed"


def test_request_and_shared_download_limits_apply_to_core_and_foundations_together(catalog, tmp_path):
    result = core_refresh(catalog, tmp_path, StudentProfile(question="ECE373 ECE310 ECE320A CSC210"))
    assert added(result) == ["ECE373", "ECE310", "ECE320A"]
    assert request_status(result, "CSC210") == "budget_limit"


@pytest.mark.parametrize("failure", ["missing_link", "program", "course", "wrong_code", "edition"])
def test_core_hints_cannot_bypass_source_identity_and_edition(catalog, tmp_path, failure):
    seen, options = [], {}
    profile = StudentProfile(question="ECE373")
    if failure == "missing_link": options["omit"] = "0121261"
    elif failure == "program": options["programs"] = {"ECEBSECE": 503}
    elif failure == "course": options["courses"] = {"0121261": 503}
    elif failure == "edition": profile.catalog_version = "2025-2026"
    else:
        record = Record(record_id="fixture:wrong", kind="course", code="ECE374", title="Fixture wrong course",
            summary="Fixture wrong identity.", credits=3, source_ids=["fixture"], catalog_version="2026-2027")
        options["courses"] = {"0121261": course_page(record, course_id="0121261")}
    result = core_refresh(catalog, tmp_path, profile, seen=seen, **options)
    assert "ECE373" not in added(result) and "ECE374" not in added(result)
    if failure in {"missing_link", "program", "edition"}:
        assert not any(url.endswith("0121261") for url in seen)


def test_failed_core_refresh_can_reuse_dated_description_with_unknown_condition(catalog, tmp_path):
    profile = StudentProfile(question="ECE373")
    core_refresh(catalog, tmp_path, profile)
    result = core_refresh(catalog, tmp_path, profile, courses={"0121261": 503})
    assert request_status(result, "ECE373") == "stale_added"
    record = next(r for r in result.catalog.records if r.code == "ECE373")
    assert record.study_stage == "intermediate" and evaluate_course(record, profile).status == "unknown"


def test_completion_filter_is_recomputed_on_304_and_never_enters_public_cache(catalog, tmp_path):
    first = core_refresh(catalog, tmp_path, StudentProfile(career_id="embedded"), headers={"ETag": '"fixture"'})
    second = core_refresh(catalog, tmp_path, StudentProfile(career_id="embedded", question="private-ece-core-sentinel ECE373",
        completed=[Completion(course_code="ECE201", grade="B")]), programs={"ECEBSECE": 304})
    assert added(first) == ["ECE201", "ECE220", "ECE274A"]
    assert added(second) == ["ECE373", "ECE220", "ECE274A"]
    assert second.discovery_selection["skipped_completed_codes"] == ["ECE201"]
    assert all("private-ece-core-sentinel" not in path.read_text() for path in tmp_path.rglob("*.json"))


@pytest.mark.parametrize("stages", [{"ECE499": "advanced"}, {"ECE310": "next"}, {"ece310": "intermediate"}])
def test_preparation_stages_require_bound_codes_and_supported_values(stages):
    data = next(plan for plan in load_discovery_plans() if plan.program_code == "ECEBSECE").model_dump(mode="json")
    data["course_stages"] = stages
    with pytest.raises(ValidationError): DiscoveryPlan.model_validate(data)


def test_preparation_stage_cannot_conflict_with_a_reviewed_entry():
    data = load_discovery_plans()[0].model_dump(mode="json")
    data["course_stages"] = {"CSC210": "foundation"}
    with pytest.raises(ValidationError, match="Conflicting"):
        DiscoveryPlan.model_validate(data)


def test_unbound_link_cannot_borrow_a_stage_from_another_course_identity(catalog, tmp_path):
    plans = load_discovery_plans()
    ece = next(plan for plan in plans if plan.program_code == "ECEBSECE")
    ece.course_stages["ECE373"] = "advanced"
    # The unbound fixture ID reports the same code, but it is not the bound ID.
    def modify(primary, nodes):
        nodes[0]["value"]["values"][0]["value"] = ["7654321"]
        for node in nodes[1:]:
            node["value"]["values"][0]["value"] = ["7654321"]
    page = program_page(ece, modify=modify)
    record = Record(record_id="fixture:unbound", kind="course", code="ECE373", title="Fixture unbound",
        summary="Fixture software.", credits=3, source_ids=["fixture"], catalog_version="2026-2027")
    result = core_refresh(catalog, tmp_path, StudentProfile(career_id="embedded"), plans=plans,
        programs={"ECEBSECE": page}, courses={"7654321": course_page(record, course_id="7654321")})
    assert "ECE373" not in added(result)
    assert next(c for c in result.checks if c.code == "ECE373").failure_kind == "validation"


@pytest.mark.parametrize("topic", ["marine biology", "contemporary issues"])
def test_unsupported_broad_topic_or_offline_hint_makes_no_new_request(catalog, topic):
    def forbidden(*a, **k): pytest.fail("Unfetched or unsupported hints must not start remote work")
    outside = run_advisor(catalog, StudentProfile(question=topic), source_refresher=forbidden)
    offline = run_advisor(catalog, StudentProfile(question="class hierarchies"), source_refresher=forbidden,
        provider_factory=forbidden, refresh_sources=False, use_ai=True, api_key="fixture")
    assert outside.coverage_notice and offline.coverage_notice
