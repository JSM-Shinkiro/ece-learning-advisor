"""A simulated clock verifies budget boundaries without real model calls or sleeps."""

from types import SimpleNamespace

import httpx
import pytest

from src import providers
from src.catalog import build_evidence, load_runtime_catalog
from src.controller import run_advisor
from src.models import ExplanationSelection, SelectedRecommendation, StudentProfile
from src.providers import AIBudgetExceeded, AIRequestBudget, BudgetedProvider, EmbeddingCache, GeminiProvider, ProviderError
from src.service import recommend
from src.settings import ConfigurationError, load_settings


class Clock:
    def __init__(self): self.now = 0.0
    def __call__(self): return self.now
    def advance(self, seconds): self.now += seconds


class ControlledProvider:
    embedding_model = "fixture-budget-embedding"
    generation_model = "fixture-budget-generator"
    dimensions = 3

    def __init__(self, clock, *, document=1, query=1, generation=1, fail_document=False):
        self.clock = clock
        self.costs = {"document": document, "query": query, "generation": generation}
        self.counts = {"document": 0, "query": 0, "generation": 0, "closed": 0}
        self.fail_document = fail_document

    def set_request_budget(self, budget): self.budget = budget

    def charge(self, operation):
        self.counts[operation] += 1
        self.clock.advance(self.costs[operation])

    def embed_document(self, chunk):
        self.charge("document")
        if self.fail_document: raise ProviderError("Controlled embedding failure")
        return [1, 2, 3]

    def embed_query(self, query):
        self.charge("query")
        return [1, 2, 3]

    def generate(self, context):
        self.charge("generation")
        statement = next(s for s in context.allowed_statements if s.claim_type == "recommendation")
        return ExplanationSelection(status="answered", recommendations=[
            SelectedRecommendation(record_id=statement.record_id, statement_ids=[statement.statement_id])])

    def close(self): self.counts["closed"] += 1


def request(monkeypatch, tmp_path, provider, *, seconds=5, method="hybrid", profile=None, catalog=None, **kwargs):
    monkeypatch.setattr("src.controller.AIRequestBudget", lambda seconds: AIRequestBudget(seconds, clock=provider.clock))
    return run_advisor(catalog or load_runtime_catalog(), profile or StudentProfile(),
        api_key="controlled-placeholder", use_ai=True, method=method, ai_time_budget_seconds=seconds,
        provider_factory=lambda *a, **k: provider, cache_dir=tmp_path, refresh_sources=False, **kwargs)


def test_cold_budget_stops_later_calls_and_next_request_reuses_partial_public_vectors(monkeypatch, tmp_path):
    clock = Clock()
    first = ControlledProvider(clock)
    profile = StudentProfile(current_enrollment=["ECE101"])
    result = request(monkeypatch, tmp_path, first, profile=profile)
    assert first.counts == {"document": 5, "query": 0, "generation": 0, "closed": 1}
    assert result.generation_status == "time_budget_exceeded" and result.retrieval_mode == "keyword"
    assert result.answer is None and result.statement_validation_passed is None and result.validation_error is None
    assert result.trace["reference_checks_passed"] is None and result.trace["ai_budget"]["exhausted"]
    assert result.trace["ai_budget"]["elapsed_seconds"] == 5
    assert len(list((tmp_path / "documents").glob("*.npz"))) == 4
    assert not list(tmp_path.glob("*.npz"))
    assert "uofa:ECE101:2026-2027" not in result.context.allowed_record_ids
    assert result.context.rule_results
    second = ControlledProvider(clock)
    recovered = request(monkeypatch, tmp_path, second, seconds=45, profile=profile)
    assert second.counts == {"document": 30, "query": 1, "generation": 1, "closed": 1}
    assert recovered.generation_complete and not recovered.trace["ai_budget"]["exhausted"]
    assert recovered.trace["ai_budget"]["elapsed_seconds"] == 32
    assert second.budget is not first.budget


@pytest.mark.parametrize("method", ["semantic", "hybrid"])
def test_warm_query_timeout_keeps_index_and_blocks_generation(monkeypatch, tmp_path, method):
    clock = Clock()
    warm = ControlledProvider(clock, document=0)
    catalog = load_runtime_catalog()
    EmbeddingCache(tmp_path).get(catalog, build_evidence(catalog), warm)
    provider = ControlledProvider(clock, query=6)
    result = request(monkeypatch, tmp_path, provider, method=method)
    assert provider.counts == {"document": 0, "query": 1, "generation": 0, "closed": 1}
    assert result.generation_status == "time_budget_exceeded" and result.cache_state == "hit"
    assert result.vectors is None and result.query_vector is None
    assert len(list(tmp_path.glob("*.npz"))) == 1


def test_late_generation_selection_is_rejected_without_a_format_error(monkeypatch, tmp_path):
    provider = ControlledProvider(Clock(), generation=6)
    result = request(monkeypatch, tmp_path, provider, method="keyword")
    assert provider.counts == {"document": 0, "query": 0, "generation": 1, "closed": 1}
    assert result.generation_status == "time_budget_exceeded" and not result.generation_complete
    assert result.answer is None and result.validation_error is None
    assert result.context.allowed_record_ids and result.context.source_freshness


@pytest.mark.parametrize("cost,expected", [(1, True), (6, False)])
def test_ordinary_embedding_errors_keep_fallback_only_while_budget_remains(monkeypatch, tmp_path, cost, expected):
    provider = ControlledProvider(Clock(), document=cost, fail_document=True)
    result = request(monkeypatch, tmp_path, provider)
    assert result.generation_complete is expected
    assert provider.counts["generation"] == int(expected)
    assert result.trace["ai_budget"]["exhausted"] is (not expected)


@pytest.mark.parametrize("acquired", [False, True])
def test_cache_wait_is_capped_and_releases_an_acquired_lock_on_expiration(monkeypatch, tmp_path, acquired):
    clock, waits, releases = Clock(), [], []
    class Lock:
        def acquire(self, *, timeout):
            waits.append(timeout)
            clock.advance(6)
            return acquired
        def release(self): releases.append(True)
    monkeypatch.setattr(providers, "_cache_lock_for", lambda path: Lock())
    provider = ControlledProvider(clock)
    result = request(monkeypatch, tmp_path, provider)
    assert 0 <= waits[0] <= 5 and len(waits) == 1
    assert releases == ([True] if acquired else [])
    assert provider.counts == {"document": 0, "query": 0, "generation": 0, "closed": 1}
    assert result.generation_status == "time_budget_exceeded"


def test_source_work_precedes_the_ai_budget_and_retains_the_refreshed_catalog(monkeypatch, tmp_path, catalog):
    from src.sources import CatalogRefresh
    clock = Clock()
    provider = ControlledProvider(clock, document=0)
    monkeypatch.setattr("src.controller.AIRequestBudget", lambda seconds: AIRequestBudget(seconds, clock=clock))
    def refresh(catalog, profile, **kwargs):
        clock.advance(100)
        updated = catalog.model_copy(deep=True)
        updated.records[0].summary += " Controlled source refresh."
        return CatalogRefresh(catalog=updated)
    result = run_advisor(catalog, StudentProfile(), api_key="controlled-placeholder", use_ai=True,
        provider_factory=lambda *a, **k: provider, source_refresher=refresh, cache_dir=tmp_path,
        ai_time_budget_seconds=5)
    assert result.generation_complete and result.trace["ai_budget"]["elapsed_seconds"] == 2
    assert result.catalog.records[0].summary.endswith("Controlled source refresh.")
    assert result.trace["source_refresh"]["enabled"]


def test_expiration_during_local_context_work_prevents_starting_generation(monkeypatch, tmp_path):
    import src.service
    clock = Clock()
    original = src.service.build_context
    def build(*args, **kwargs):
        context = original(*args, **kwargs)
        clock.advance(6)
        return context
    monkeypatch.setattr(src.service, "build_context", build)
    provider = ControlledProvider(clock)
    result = request(monkeypatch, tmp_path, provider, method="keyword")
    assert provider.counts["generation"] == 0 and result.context.allowed_record_ids
    assert result.generation_status == "time_budget_exceeded"


def test_expiration_during_answer_validation_does_not_publish_selection(monkeypatch, tmp_path):
    import src.service
    clock = Clock()
    original = src.service.validate_answer
    def validate(*args, **kwargs):
        answer = original(*args, **kwargs)
        clock.advance(6)
        return answer
    monkeypatch.setattr(src.service, "validate_answer", validate)
    provider = ControlledProvider(clock, generation=0)
    result = request(monkeypatch, tmp_path, provider, method="keyword")
    assert provider.counts["generation"] == 1 and provider.counts["closed"] == 1
    assert result.answer is None and result.selected_statement_ids == []
    assert result.generation_status == "time_budget_exceeded" and not result.generation_complete


def test_preview_and_unsupported_requests_never_initialize_ai_budgets(monkeypatch, tmp_path, catalog):
    def forbidden(*args, **kwargs): pytest.fail("No budget, source request, or provider expected")
    monkeypatch.setattr("src.controller.AIRequestBudget", forbidden)
    preview = run_advisor(catalog, StudentProfile(), use_ai=False, refresh_sources=False)
    guarded = run_advisor(catalog, StudentProfile(question="marine biology dolphin migration"),
        use_ai=True, api_key="controlled-placeholder", provider_factory=forbidden, source_refresher=forbidden)
    assert "ai_budget" not in preview.trace and "ai_budget" not in guarded.trace
    assert guarded.coverage_notice and guarded.trace["model_calls"] == 0


@pytest.mark.parametrize("seconds", [5, 45, 120])
def test_sdk_uses_remaining_time_for_both_timeout_units_and_preserves_no_retry_policy(catalog, seconds):
    clock, calls = Clock(), []
    def embed(**kwargs):
        calls.append(("embedding", kwargs))
        return SimpleNamespace(embeddings=[SimpleNamespace(values=[1, 2, 3])])
    def generate(**kwargs):
        calls.append(("generation", kwargs))
        return SimpleNamespace(output_text=ExplanationSelection(status="insufficient_evidence", clarification_code="insufficient_evidence").model_dump_json())
    sdk = GeminiProvider("controlled-placeholder", dimensions=3, client=SimpleNamespace(
        models=SimpleNamespace(embed_content=embed), interactions=SimpleNamespace(create=generate)))
    wrapped = BudgetedProvider(sdk, AIRequestBudget(seconds, clock=clock))
    clock.advance(2)
    wrapped.embed_query("query")
    clock.advance(1)
    wrapped.generate(recommend(catalog, StudentProfile()).context)
    assert calls[0][1]["config"].http_options.timeout == min(30, seconds - 2) * 1000
    assert calls[0][1]["config"].http_options.retry_options.attempts == 1
    assert calls[1][1]["timeout"] == min(30, seconds - 3) and calls[1][1]["store"] is False


def test_installed_sdk_propagates_shrinking_timeouts_to_the_http_transport(catalog, monkeypatch):
    from google import genai
    from google.genai import types
    observed = []
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda *a, **k: pytest.fail("No real HTTP requests"))
    def handle(request):
        observed.append(request.extensions["timeout"])
        if ":batchEmbedContents" in request.url.path or ":embedContent" in request.url.path:
            return httpx.Response(200, json={"embeddings": [{"values": [1, 2, 3]}]})
        return httpx.Response(400, json={"error": {"code": 400, "message": "Controlled rejection", "status": "INVALID_ARGUMENT"}})
    clock = Clock()
    with httpx.Client(transport=httpx.MockTransport(handle), trust_env=False) as http:
        client = genai.Client(api_key="controlled-placeholder", http_options=types.HttpOptions(
            httpx_client=http, retry_options=types.HttpRetryOptions(attempts=1)))
        try:
            provider = BudgetedProvider(GeminiProvider("controlled-placeholder", dimensions=3, client=client),
                AIRequestBudget(5, clock=clock))
            clock.advance(1)
            provider.embed_query("controlled query")
            clock.advance(1)
            with pytest.raises(ProviderError): provider.generate(recommend(catalog, StudentProfile()).context)
        finally:
            client.close()
    assert len(observed) == 2
    assert all(value == 4 for value in observed[0].values())
    assert all(value == 3 for value in observed[1].values())


@pytest.mark.parametrize("value", ["0", "4", "121", "NaN", "5.5", "true", "", "private-invalid-budget"])
def test_invalid_host_budgets_fail_with_a_sanitized_setting_name(tmp_path, value):
    with pytest.raises(ConfigurationError) as error:
        load_settings({"AI_TIME_BUDGET_SECONDS": value}, root=tmp_path)
    assert "AI_TIME_BUDGET_SECONDS" in str(error.value)
    assert "private-invalid-budget" not in str(error.value)


@pytest.mark.parametrize("value", [True, 4, 121, 5.5])
def test_direct_budgets_reject_invalid_ranges_or_types(value):
    with pytest.raises(ValueError): AIRequestBudget(value)


def test_budget_setting_is_public_but_credentials_remain_excluded(tmp_path):
    settings = load_settings({"AI_TIME_BUDGET_SECONDS": " 15 ", "GEMINI_API_KEY": "controlled-private-placeholder"}, root=tmp_path)
    assert settings.ai_time_budget_seconds == settings.public_summary()["ai_time_budget_seconds"] == 15
    assert "controlled-private-placeholder" not in str(settings.public_summary())


def test_budget_configuration_failure_closes_provider_and_keeps_source_plan(monkeypatch, tmp_path):
    class Broken(ControlledProvider):
        def set_request_budget(self, budget): raise ProviderError("Controlled setup failure")
    provider = Broken(Clock())
    result = request(monkeypatch, tmp_path, provider)
    assert provider.counts == {"document": 0, "query": 0, "generation": 0, "closed": 1}
    assert result.context.allowed_record_ids and not result.generation_complete
    assert any("AI could not start" in issue for issue in result.issues)


@pytest.mark.parametrize("value", [4, 121, True])
def test_runtime_verifier_rejects_invalid_time_limits_before_any_provider(value, tmp_path):
    from src.runtime_checks import verify_runtime
    def forbidden(*args, **kwargs): pytest.fail("No provider requests")
    with pytest.raises(ValueError):
        verify_runtime(load_runtime_catalog(), "controlled-placeholder", ai_time_budget_seconds=value,
            provider_factory=forbidden, source_refresher=forbidden, cache_dir=tmp_path)


def test_runtime_cli_uses_the_same_host_time_budget(monkeypatch, tmp_path):
    import json
    from test_runtime_checks import cli_setup
    cli, output = cli_setup(monkeypatch, tmp_path)
    monkeypatch.setenv("AI_TIME_BUDGET_SECONDS", "15")
    assert cli.main() == 0
    report = json.loads(output.read_text())
    assert report["ai_time_budget_seconds"] == 15
    assert all(case["trace"]["ai_budget"]["limit_seconds"] == 15 for case in report["cases"] if not case["case_id"] == "coverage_guard")
