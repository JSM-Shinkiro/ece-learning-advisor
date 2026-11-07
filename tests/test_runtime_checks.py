"""Controlled integration adapters; no public model or source requests."""

from dataclasses import replace
import json

import numpy as np
import pytest

from src.catalog import load_runtime_catalog
from src.models import ExplanationSelection, SelectedRecommendation
from src.providers import ProviderError
from src.runtime_checks import CallBudget, runtime_cases, verify_runtime
from src.discovery import load_discovery_plans
from src.sources import refresh_catalog
from test_runtime_catalog import runtime_client
from test_resource_sources import resource_page
from test_track_coverage import mit_page
from src.resource_sources import RESOURCE_URLS

SECRET = "fixture-private-provider-diagnostic"


class ControlledProvider:
    def __init__(self, key, *, embedding_model="gemini-embedding-2", generation_model="gemini-3.5-flash-lite", dimensions=7):
        self.embedding_model, self.generation_model, self.dimensions = embedding_model, generation_model, dimensions
        self.closed = False
        self.generations = 0

    def embed_document(self, chunk):
        slots = {"uofa:ECE101:2026-2027": 0, "uofa:CSC372:2026-2027": 1,
                 "uofa:ECE381A:2026-2027": 2, "resource:mit_algorithms": 3,
                 "resource:mit_structures": 4, "uofa:ECE372A:2026-2027": 5, "uofa:ECE352:2026-2027": 6}
        vector = np.full(self.dimensions, .01)
        vector[slots.get(chunk.record_id, 0)] = 1
        return vector

    def embed_query(self, query):
        query = query.upper()
        vector = np.full(self.dimensions, .01)
        for code, slot in [("CSC372", 1), ("ECE381A", 2), ("ECE372A", 5), ("ECE352", 6)]:
            if code in query:
                vector[slot] = 1
                return vector
        vector[3 if "6.006" in query else 0] = 1
        if "6.004" in query: vector[4] = 1
        return vector

    def generate(self, context):
        self.generations += 1
        return ExplanationSelection(status="answered", recommendations=[SelectedRecommendation(record_id=rid,
            statement_ids=[next(s.statement_id for s in context.allowed_statements if s.record_id == rid)])
            for rid in context.allowed_record_ids])

    def close(self):
        self.closed = True


def run(tmp_path, **kwargs):
    return verify_runtime(load_runtime_catalog(), SECRET, dimensions=7, provider_factory=ControlledProvider,
        cache_dir=tmp_path / "vectors", source_cache_dir=tmp_path / "sources", **kwargs)


def test_saved_runtime_scenarios_use_the_real_controller_and_share_vectors(tmp_path, monkeypatch):
    monkeypatch.setattr("httpx.Client.send", lambda *a, **k: pytest.fail("Saved checks must not request sources"))
    report = run(tmp_path)
    assert report["all_checks_passed"] and len(report["cases"]) == 6
    counts = report["call_counts"]
    assert counts["document_embeddings"] == 34 and counts["query_embeddings"] == 4 and counts["generations"] == 5
    assert counts["providers_started"] == counts["providers_closed"] == 5
    assert not counts["errors"] and not any(counts["blocked_calls"].values())
    cases = {row["case_id"]: row for row in report["cases"]}
    assert cases["ai_semantic"]["trace"]["cache_state"] == "miss"
    assert cases["embedded_hybrid"]["trace"]["cache_state"] == "hit"
    assert SECRET not in json.dumps(report)
    again = run(tmp_path)
    assert again["all_checks_passed"] and again["call_counts"]["document_embeddings"] == 0


def source_refresh(catalog, profile, *, cache_dir, **kwargs):
    pages = {RESOURCE_URLS["resource:mit_structures"]: mit_page("resource:mit_structures"),
             RESOURCE_URLS["resource:cs50"]: resource_page("resource:cs50")}
    with runtime_client(catalog, [], pages) as client:
        return refresh_catalog(catalog, profile, client=client, discovery_plans=load_discovery_plans(),
            cache_dir=cache_dir, resource_checks=True)


def test_optional_source_scenario_checks_current_evidence_and_caps(tmp_path):
    report = run(tmp_path, with_sources=True, source_refresher=source_refresh)
    assert report["all_checks_passed"] and len(report["cases"]) == 7
    row = report["cases"][-1]
    assert row["expectations"]["selected_sources_verified"] and row["expectations"]["source_limits"]
    assert row["context"]["source_freshness"]["catalog:ECE352"]["verification_status"] == "verified"
    assert report["call_counts"]["document_embeddings"] <= 64
    assert report["call_counts"]["generations"] == 6


def test_guard_does_not_initialize_provider_or_refresh_sources(tmp_path):
    def forbidden(*a, **k): pytest.fail("Guard must run before providers or source calls")
    report = verify_runtime(load_runtime_catalog(), SECRET, cases=[runtime_cases(True)[0]], with_sources=True,
        provider_factory=forbidden, source_refresher=forbidden, cache_dir=tmp_path)
    assert report["all_checks_passed"]
    assert report["call_counts"]["providers_started"] == report["call_counts"]["generations"] == 0


class StatusError(Exception):
    code = 429


class FailingGenerator(ControlledProvider):
    def generate(self, context):
        try: raise StatusError(SECRET)
        except StatusError as error: raise ProviderError(SECRET) from error


def test_provider_failure_stops_later_calls_and_excludes_raw_diagnostics(tmp_path):
    report = verify_runtime(load_runtime_catalog(), SECRET, dimensions=7, cache_dir=tmp_path,
        provider_factory=FailingGenerator)
    assert not report["all_checks_passed"]
    assert report["call_counts"]["generations"] == 1
    assert report["call_counts"]["document_embeddings"] == report["call_counts"]["query_embeddings"] == 0
    assert report["call_counts"]["errors"][0]["http_status"] == 429
    assert report["call_counts"]["providers_closed"] == 1
    assert all(row["status"] == "not_run" for row in report["cases"][2:])
    assert SECRET not in json.dumps(report)


def test_failed_embeddings_cannot_trigger_a_generation_fallback_call(tmp_path):
    class Broken(ControlledProvider):
        def embed_document(self, chunk): raise RuntimeError(SECRET)
        def generate(self, context): pytest.fail("Verifier must stop after embedding error")
    report = verify_runtime(load_runtime_catalog(), SECRET, dimensions=7, cases=[runtime_cases()[2]],
        cache_dir=tmp_path, provider_factory=Broken)
    counts = report["call_counts"]
    assert counts["document_embeddings"] == 1 and counts["generations"] == counts["query_embeddings"] == 0
    assert counts["blocked_calls"]["generations"] == 1 and not report["all_checks_passed"]
    assert report["cases"][0]["expectations"]["requested_retrieval"] is False
    assert SECRET not in json.dumps(report)


def test_initialization_and_close_errors_are_sanitized_and_retained(tmp_path):
    def broken(*a, **k): raise RuntimeError(SECRET)
    report = verify_runtime(load_runtime_catalog(), SECRET, cache_dir=tmp_path, provider_factory=broken)
    assert not report["all_checks_passed"] and report["call_counts"]["providers_started"] == 0
    assert report["call_counts"]["errors"][0]["operation"] == "initialization"
    class BadClose(ControlledProvider):
        def close(self): raise RuntimeError(SECRET)
    closed = verify_runtime(load_runtime_catalog(), SECRET, cases=[runtime_cases()[1]], dimensions=7,
        cache_dir=tmp_path, provider_factory=BadClose)
    assert not closed["all_checks_passed"] and closed["call_counts"]["providers_closed"] == 0
    assert any(e["operation"] == "close" for e in closed["call_counts"]["errors"])
    assert SECRET not in json.dumps([report, closed])


@pytest.mark.parametrize("budget", [CallBudget(document_embeddings=1), CallBudget(query_embeddings=1), CallBudget(generations=1)])
def test_budgets_block_calls_before_the_underlying_adapter_runs(tmp_path, budget):
    report = run(tmp_path, budget=budget)
    assert not report["all_checks_passed"]
    for name in ("document_embeddings", "query_embeddings", "generations"):
        assert report["call_counts"][name] <= getattr(budget, name)
    assert any(error["error_type"] == "call_budget" for error in report["call_counts"]["errors"])


def test_valid_but_irrelevant_selection_is_an_integration_failure(tmp_path):
    class OtherRecord(ControlledProvider):
        def generate(self, context):
            selection = super().generate(context)
            selection.recommendations = [rec for rec in selection.recommendations if rec.record_id.startswith("resource:")][:1]
            return selection
    report = verify_runtime(load_runtime_catalog(), SECRET, cases=[runtime_cases()[1]], dimensions=7,
        provider_factory=OtherRecord, cache_dir=tmp_path)
    checks = report["cases"][0]["expectations"]
    assert checks["answered"] and checks["statement_contract"] and not checks["focus_selected"]
    assert not report["all_checks_passed"] and not report["call_counts"]["errors"]


def test_invalid_statement_ids_are_not_counted_as_a_pass(tmp_path):
    class WrongStatement(ControlledProvider):
        def generate(self, context):
            result = super().generate(context)
            result.recommendations[0].statement_ids = ["invented-statement"]
            return result
    report = verify_runtime(load_runtime_catalog(), SECRET, cases=[runtime_cases()[1]], dimensions=7,
        provider_factory=WrongStatement, cache_dir=tmp_path)
    assert not report["all_checks_passed"]
    assert report["cases"][0]["expectations"]["statement_contract"] is False


def test_failed_source_check_remains_a_failure_when_the_model_answers(tmp_path):
    def stale(catalog, profile, **kwargs):
        result = source_refresh(catalog, profile, **kwargs)
        target = next(c for c in result.checks if c.code == "ECE352")
        target.status = "bundled_fallback"
        return result
    report = run(tmp_path, cases=[runtime_cases(True)[-1]], with_sources=True, source_refresher=stale)
    checks = report["cases"][0]["expectations"]
    assert checks["answered"] and checks["statement_contract"] and not checks["selected_sources_verified"]
    assert not report["all_checks_passed"]


@pytest.mark.parametrize("bad", ["empty_key", "bad_budget", "empty_cases", "duplicate_id", "method", "record", "source_flag"])
def test_invalid_verification_inputs_fail_before_calls(tmp_path, bad):
    def forbidden(*a, **k): pytest.fail("Invalid inputs must not use a provider")
    kwargs = {"cases": [runtime_cases()[1]], "api_key": SECRET}
    if bad == "empty_key": kwargs["api_key"] = ""
    elif bad == "bad_budget": kwargs["budget"] = False
    elif bad == "empty_cases": kwargs["cases"] = []
    elif bad == "duplicate_id": kwargs["cases"] *= 2
    elif bad == "method": kwargs["cases"] = [replace(runtime_cases()[1], method="other")]
    elif bad == "record": kwargs["cases"] = [replace(runtime_cases()[1], expected_record_ids=("missing",))]
    else: kwargs["cases"] = [runtime_cases(True)[-1]]
    with pytest.raises(ValueError): verify_runtime(load_runtime_catalog(), cache_dir=tmp_path, provider_factory=forbidden, **kwargs)


@pytest.mark.parametrize("kwargs", [{"document_embeddings": 0}, {"document_embeddings": 65}, {"query_embeddings": 9},
    {"generations": 9}, {"generations": True}, {"generations": 1.5}])
def test_invalid_call_limits_are_rejected(kwargs):
    with pytest.raises(ValueError): CallBudget(**kwargs)


def cli_setup(monkeypatch, tmp_path, provider=ControlledProvider):
    from scripts import verify_runtime as cli
    original = verify_runtime
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    monkeypatch.setenv("GEMINI_API_KEY", SECRET)
    monkeypatch.setenv("EMBEDDING_DIMENSION", "7")
    monkeypatch.setenv("ECE_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(cli, "verify_runtime", lambda *a, **k: original(*a, provider_factory=provider, source_refresher=source_refresh, **k))
    output = tmp_path / "report.json"
    monkeypatch.setattr("sys.argv", ["verify", "--live-models", "--output", str(output)])
    return cli, output


def test_cli_requires_explicit_opt_in_before_configuration(monkeypatch, tmp_path):
    from scripts import verify_runtime as cli
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: pytest.fail("No credential reads without opt-in"))
    output = tmp_path / "report.json"
    monkeypatch.setattr("sys.argv", ["verify", "--output", str(output)])
    with pytest.raises(SystemExit) as error: cli.main()
    assert error.value.code == 2 and not output.exists()


@pytest.mark.parametrize("with_sources", [False, True])
def test_cli_success_and_existing_output_preservation(monkeypatch, tmp_path, with_sources):
    cli, output = cli_setup(monkeypatch, tmp_path)
    if with_sources:
        import sys
        monkeypatch.setattr("sys.argv", [*sys.argv, "--with-sources"])
    assert cli.main() == 0
    before = output.read_bytes()
    report = json.loads(before)
    assert report["all_checks_passed"] and report["catalog"] == {"courses": 20, "resources": 8, "chunks": 34}
    assert report["source_case_requested"] is with_sources
    assert SECRET.encode() not in before
    monkeypatch.setattr(cli, "verify_runtime", lambda *a, **k: pytest.fail("Existing output must not spend quota"))
    assert cli.main() == 2 and output.read_bytes() == before


def test_cli_retains_failed_check_report_and_sanitizes_logs(monkeypatch, tmp_path, capsys):
    cli, output = cli_setup(monkeypatch, tmp_path, FailingGenerator)
    assert cli.main() == 1
    report = json.loads(output.read_text())
    assert not report["all_checks_passed"] and report["call_counts"]["generations"] == 1
    logs = capsys.readouterr()
    assert SECRET not in output.read_text() + logs.out + logs.err


def test_cli_missing_key_and_unwritable_output_fail_before_quota(monkeypatch, tmp_path):
    cli, output = cli_setup(monkeypatch, tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setattr(cli, "verify_runtime", lambda *a, **k: pytest.fail("Invalid startup must not spend quota"))
    assert cli.main() == 2 and not output.exists()
    monkeypatch.setenv("GEMINI_API_KEY", SECRET)
    parent = tmp_path / "existing_file"
    parent.write_text("keep")
    monkeypatch.setattr("sys.argv", ["verify", "--live-models", "--output", str(parent / "report.json")])
    assert cli.main() == 2 and parent.read_text() == "keep"
