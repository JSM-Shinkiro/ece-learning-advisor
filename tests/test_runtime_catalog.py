"""Expanded production coverage, frozen evaluation isolation, and bounded on-use checks."""

import hashlib
import json

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from src.catalog import ROOT, build_evidence, corpus_hash, load_catalog, load_runtime_catalog
from src.controller import run_advisor
from src.discovery import load_discovery_plans
from src.models import Completion, StudentProfile
from src.planning import learning_phase
from src.rules import evaluate_course
from src.sources import MAX_SOURCES, refresh_catalog
from test_discovery import program_page
from test_sources import NOW, course_page


def test_runtime_expansion_preserves_the_frozen_collection_and_labels():
    frozen, runtime = load_catalog(), load_runtime_catalog()
    assert corpus_hash(frozen) == "8df543f9bfe5d83374385ea5f756160d42144d9ab04bfc20b49e7f78059d643d"
    assert hashlib.sha256((ROOT / "data/evaluation/reviewed_v1.json").read_bytes()).hexdigest() == "b639a6870e4d7ce4f9bfa25745224e1cb7cd7a1c9d95ef2ca977b69585754248"
    assert sum(r.kind == "course" for r in runtime.records) == 17
    assert sum(r.kind == "resource" for r in runtime.records) == 6
    assert len(build_evidence(frozen)) == 10 and len(build_evidence(runtime)) == 29
    assert runtime.records[:len(frozen.records)] == frozen.records
    assert runtime.sources[:len(frozen.sources)] == frozen.sources
    assert corpus_hash(runtime) != corpus_hash(frozen)
    runtime.records[0].summary = "A local edit must not change a later load."
    assert load_runtime_catalog().records[0] == frozen.records[0]


@pytest.mark.parametrize("bad", ["baseline_hash", "edition", "replace_record", "replace_source", "duplicate_code",
    "duplicate_url", "synthetic", "missing_source", "record_edition"])
def test_runtime_loader_rejects_conflicting_or_unbound_extensions(tmp_path, bad):
    directory = tmp_path / "data/reviewed"
    directory.mkdir(parents=True)
    (directory / "catalog.json").write_bytes((ROOT / "data/reviewed/catalog.json").read_bytes())
    extension = json.loads((ROOT / "data/reviewed/runtime_extension.json").read_text())
    record, source = extension["records"][0], extension["sources"][0]
    if bad == "baseline_hash": extension["baseline_corpus_hash"] = "0" * 64
    elif bad == "edition": extension["catalog_version"] = "2025-2026"
    elif bad == "replace_record": record["record_id"] = "uofa:ECE101:2026-2027"
    elif bad == "replace_source": source["source_id"] = "catalog:ECE101"
    elif bad == "duplicate_code":
        other = dict(record, record_id="duplicate-course")
        extension["records"].append(other)
    elif bad == "duplicate_url": extension["sources"].append(dict(source, source_id="duplicate-source"))
    elif bad == "synthetic": record["review_status"] = "synthetic_fixture"
    elif bad == "missing_source": record["source_ids"] = ["missing"]
    elif bad == "record_edition": record["catalog_version"] = "2025-2026"
    (directory / "runtime_extension.json").write_text(json.dumps(extension))
    with pytest.raises(ValueError): load_runtime_catalog(tmp_path)


def test_added_ece_descriptions_do_not_grant_enrollment_or_degree_credit():
    catalog = load_runtime_catalog()
    for record in catalog.records:
        if record.code and record.code.startswith("ECE"):
            assert not record.rule_reviewed and not record.rule_evidence
            assert evaluate_course(record, StudentProfile(standing="Senior", programming_background="experienced")).status == "unknown"
        if record.kind == "resource":
            assert record.catalog_version is None and record.credits is None
    resource = next(r for r in catalog.records if r.record_id == "resource:python")
    assert learning_phase(resource, StudentProfile()) == "later"
    assert "programming experience" in resource.learning_note


def runtime_client(catalog, seen, overrides=None):
    plans = load_discovery_plans()
    sources = {s.source_id: s for s in catalog.sources}
    pages = {}
    for record in catalog.records:
        if record.kind == "course":
            source = sources[record.source_ids[0]]
            pages[source.url] = course_page(record, course_id=source.url.rsplit("/", 1)[-1])
    for plan in plans:
        proofs = [proof for record in catalog.records for proof in record.rule_evidence
                  if proof.source_id == plan.source.source_id]
        proof_map = {proof.section_id: proof.reviewed_text for proof in proofs}
        def describe(primary, rules):
            for section, rule in zip(plan.section_ids, rules):
                if section in proof_map:
                    rule["description"] = proof_map[section]
        pages[plan.source.url] = program_page(plan, ids_by_section={section: list(plan.known_course_codes)
            for section in plan.section_ids}, proofs=[proof for proof in proofs if proof.section_id not in plan.section_ids], modify=describe)
    pages.update(overrides or {})
    def respond(request):
        url = str(request.url)
        seen.append(url)
        content = pages[url]
        return httpx.Response(content) if isinstance(content, int) else httpx.Response(200, text=content, headers={"Content-Type": "text/html"})
    return httpx.Client(transport=httpx.MockTransport(respond))


@pytest.mark.parametrize("question,expected", [("ECE373 and ECE351C", ["ECE373", "ECE351C"]),
    ("object oriented software design", ["ECE373"]), ("electronic circuits", ["ECE351C"])])
def test_existing_requested_courses_receive_checks_before_the_cap(tmp_path, question, expected):
    catalog = load_runtime_catalog()
    original = catalog.model_dump_json()
    seen = []
    with runtime_client(catalog, seen) as client:
        result = refresh_catalog(catalog, StudentProfile(career_id="embedded", question=question),
            discovery_plans=load_discovery_plans(), client=client, cache_dir=tmp_path, now=NOW)
    trace = result.trace()["course_check_selection"]
    assert trace["selected_codes"][:len(expected)] == expected
    assert len(trace["selected_codes"]) == MAX_SOURCES
    assert len([url for url in seen if "/courses/" in url]) == MAX_SOURCES
    assert len(set(seen)) == len(seen)
    for code in expected:
        source = next(s for s in result.catalog.sources if s.source_id == "catalog:" + code)
        assert source.verification_status == "verified" and source.last_checked_at == NOW
    for code in trace["snapshot_codes"]:
        assert next(s for s in result.catalog.sources if s.source_id == "catalog:" + code).verification_status == "snapshot"
    assert catalog.model_dump_json() == original
    assert all(request["status"] == "in_collection" for request in result.discovery_selection["requests"])


def test_completed_courses_yield_limited_check_slots_to_incomplete_records(tmp_path):
    catalog = load_runtime_catalog()
    completed = [Completion(course_code=r.code, grade="B") for r in catalog.records
                 if r.kind == "course" and r.code not in {"ECE373", "ECE351C"}]
    with runtime_client(catalog, []) as client:
        result = refresh_catalog(catalog, StudentProfile(career_id="embedded", completed=completed),
            client=client, cache_dir=tmp_path, now=NOW)
    assert result.course_check_selection["selected_codes"][:2] == ["ECE351C", "ECE373"]


def test_all_four_reviewed_cs_conditions_recheck_as_one_program_source(tmp_path):
    catalog = load_runtime_catalog()
    profile = StudentProfile(career_id="ai_ml", question="CSC210", completed=[Completion(course_code="CSC120", grade="B")])
    seen = []
    with runtime_client(catalog, seen) as client:
        result = refresh_catalog(catalog, profile, discovery_plans=load_discovery_plans(), client=client, cache_dir=tmp_path, now=NOW)
    cs = [r for r in result.catalog.records if r.rule_reviewed]
    assert {r.code for r in cs} == {"CSC110", "CSC120", "CSC144", "CSC210"}
    assert all(r.rule_verification == "verified" for r in cs)
    assert sum("/programs/COSCBS/" in url for url in seen) == 1
    assert evaluate_course(next(r for r in cs if r.code == "CSC210"), profile).status == "satisfied"


def test_unavailable_saved_cs_rule_revokes_its_interpretation(tmp_path):
    catalog = load_runtime_catalog()
    seen = []
    # A successful course fetch must not repair missing program proof.
    profile = StudentProfile(question="CSC210", completed=[Completion(course_code="CSC120", grade="B")])
    plan = load_discovery_plans()[0]
    with runtime_client(catalog, seen, {plan.source.url: 404}) as failing:
        result = refresh_catalog(catalog, profile, client=failing, cache_dir=tmp_path, now=NOW)
    record = next(r for r in result.catalog.records if r.code == "CSC210")
    assert record.rule_verification == "unavailable"
    assert evaluate_course(record, profile).status == "unknown"


def test_course_budget_cannot_turn_verified_program_text_into_enrollment_approval(tmp_path):
    catalog = load_runtime_catalog()
    profile = StudentProfile(question="ECE201 ECE220 ECE274A ECE310 ECE311 ECE320A ECE340A ECE351C",
        completed=[Completion(course_code="CSC120", grade="B")])
    with runtime_client(catalog, []) as client:
        result = refresh_catalog(catalog, profile, client=client, cache_dir=tmp_path, now=NOW)
    record = next(r for r in result.catalog.records if r.code == "CSC210")
    assert record.rule_evidence[0].verification_status == "verified"
    assert record.rule_verification == "stale"
    assert evaluate_course(record, profile).status == "unknown"
    assert "CSC210" in result.course_check_selection["snapshot_codes"]


@pytest.mark.parametrize("code,career", [("ECE373", "embedded"), ("ECE310", "ai_ml"), ("CSC210", "ai_ml")])
def test_expanded_requests_reach_context_with_source_evidence(code, career):
    result = run_advisor(load_runtime_catalog(), StudentProfile(career_id=career,
        programming_background="experienced", question=code), refresh_sources=False)
    rid = "uofa:" + code + ":2026-2027"
    assert rid in result.context.allowed_record_ids
    assert any(e.record_id == rid and "catalog:" + code in e.source_ids for e in result.context.evidence)
    assert result.context.rule_results[rid].status == "unknown"
    assert not result.generation_complete


def test_expansion_preserves_the_novice_start_and_allows_an_explicit_alternative():
    catalog = load_runtime_catalog()
    default = run_advisor(catalog, StudentProfile(), refresh_sources=False)
    assert default.context.allowed_record_ids[0] == "uofa:ECE101:2026-2027"
    assert "uofa:ECE425:2026-2027" in default.context.allowed_record_ids
    alternative = run_advisor(catalog, StudentProfile(question="CSC110"), refresh_sources=False)
    assert alternative.context.allowed_record_ids[0] == "uofa:CSC110:2026-2027"


@pytest.fixture
def expanded_app(monkeypatch):
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    monkeypatch.setenv("ECE_REFRESH_SOURCES", "false")
    for name in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "ADZUNA_APP_ID", "ADZUNA_APP_KEY", "ECE_DEVELOPMENT_MODE"]:
        monkeypatch.delenv(name, raising=False)
    return AppTest.from_file(ROOT / "app.py", default_timeout=20).run()


def test_app_uses_expanded_collection_without_network_on_rerender(expanded_app, monkeypatch):
    def forbidden(*a, **k): pytest.fail("Offline app must not make public requests")
    monkeypatch.setattr("httpx.Client.send", forbidden)
    app = expanded_app
    assert not app.exception
    assert any("17 courses · 6 resources" in caption.value for caption in app.caption)
    app.text_input(key="question").set_value("CSC210")
    next(b for b in app.button if b.label == "Update my roadmap").click()
    app.run()
    assert not app.exception and not app.error
    result = app.session_state["result"]
    assert "uofa:CSC210:2026-2027" in result.context.allowed_record_ids
    assert result.trace["source_refresh"]["enabled"] is False
    app.run()
    assert not app.exception
