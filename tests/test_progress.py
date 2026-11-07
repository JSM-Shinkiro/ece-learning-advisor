"""Progress reflects work actually attempted and cannot change request results."""

from concurrent.futures import ThreadPoolExecutor
import json
from threading import Barrier, get_ident

import pytest

from conftest import FakeProvider
from src.controller import run_advisor
from src.models import StudentProfile
from src.progress import RequestProgress
from src.providers import AIBudgetExceeded, ProviderError


class ObservedProvider(FakeProvider):
    def __init__(self, events, failure=None):
        super().__init__()
        self.events, self.failure = events, failure
        self.generations = self.closed = 0

    def embed_document(self, chunk):
        assert self.events[-1] == "embeddings"
        if self.failure == "embedding":
            raise ProviderError("controlled embedding failure")
        if self.failure == "budget":
            raise AIBudgetExceeded()
        return super().embed_document(chunk)

    def generate(self, context):
        self.generations += 1
        assert self.events[-1] == "generation"
        if self.failure == "generation":
            raise ProviderError("controlled generation failure")
        return super().generate(context)

    def close(self):
        self.closed += 1


def test_preview_reports_only_snapshot_search_and_preparation_work(catalog, tmp_path):
    events = []
    result = run_advisor(catalog, StudentProfile(), refresh_sources=False,
                         cache_dir=tmp_path, progress=lambda phase, _: events.append(phase))
    assert events == ["request", "snapshots", "ranking", "requirements"]
    assert not result.generation_complete and result.context.allowed_record_ids
    assert [p["phase"] for p in result.trace["request_phases"]["phases"]] == events


@pytest.mark.parametrize("failure,expected,status", [
    (None, ["embeddings", "ranking", "requirements", "generation", "validation"], "answered"),
    ("embedding", ["embeddings", "ranking", "requirements", "generation", "validation"], "answered"),
    ("budget", ["embeddings", "ranking", "requirements"], "time_budget_exceeded"),
    ("generation", ["embeddings", "ranking", "requirements", "generation"], "failed"),
])
def test_ai_phases_precede_actual_calls_and_skip_unattempted_validation(catalog, tmp_path, failure, expected, status):
    events = []
    provider = ObservedProvider(events, failure)
    result = run_advisor(catalog, StudentProfile(), refresh_sources=False, api_key="controlled-placeholder",
                         use_ai=True, provider_factory=lambda *a, **k: provider, cache_dir=tmp_path,
                         progress=lambda phase, _: events.append(phase))
    assert events == ["request", "snapshots", "ai_setup", *expected]
    assert result.generation_status == status and provider.closed == 1
    assert provider.generations == (0 if failure == "budget" else 1)
    assert result.context.allowed_record_ids


def test_keyword_ai_does_not_claim_to_prepare_embeddings(catalog, tmp_path):
    events = []
    provider = ObservedProvider(events)
    result = run_advisor(catalog, StudentProfile(), refresh_sources=False, api_key="controlled-placeholder",
                         use_ai=True, method="keyword", provider_factory=lambda *a, **k: provider,
                         cache_dir=tmp_path, progress=lambda phase, _: events.append(phase))
    assert result.generation_complete
    assert events == ["request", "snapshots", "ai_setup", "ranking", "requirements", "generation", "validation"]


def test_source_failure_is_reported_before_source_work_and_preserves_fallback(catalog, tmp_path):
    events, calls = [], []
    def refresh(*args, **kwargs):
        assert events[-1] == "sources"
        calls.append(1)
        raise OSError("controlled transport failure")
    result = run_advisor(catalog, StudentProfile(), source_refresher=refresh, cache_dir=tmp_path,
                         progress=lambda phase, _: events.append(phase))
    assert calls == [1] and events == ["request", "sources", "ranking", "requirements"]
    assert result.trace["source_refresh"]["error"] == "unavailable"
    assert result.context.allowed_record_ids and result.issues


def test_unsupported_request_has_no_source_provider_or_ranking_progress(catalog, tmp_path):
    events = []
    def forbidden(*a, **k): pytest.fail("Unsupported requests must not start external work")
    result = run_advisor(catalog, StudentProfile(question="marine biology and ocean fieldwork"),
                         api_key="controlled-placeholder", use_ai=True, source_refresher=forbidden,
                         provider_factory=forbidden, cache_dir=tmp_path,
                         progress=lambda phase, _: events.append(phase))
    assert result.coverage_notice and events == ["request"]
    assert result.trace["model_calls"] == 0


def test_observer_failure_is_sanitized_and_does_not_retry_or_fail_generation(catalog, tmp_path):
    secret, observer_calls = "private-fixture-diagnostic", []
    class Provider(FakeProvider):
        closed = generations = 0
        def generate(self, context):
            self.generations += 1
            return super().generate(context)
        def close(self): self.closed += 1
    provider = Provider()
    def broken(phase, label):
        observer_calls.append(phase)
        raise RuntimeError(secret)
    result = run_advisor(catalog, StudentProfile(interests="robotics " + secret), refresh_sources=False,
                         api_key="controlled-placeholder", use_ai=True,
                         provider_factory=lambda *a, **k: provider, cache_dir=tmp_path, progress=broken)
    report = result.trace["request_phases"]
    assert report["observer_failed"] and observer_calls == ["request"]
    assert result.generation_complete and provider.generations == provider.closed == 1
    assert secret not in json.dumps(report)
    assert [p["phase"] for p in report["phases"]][-1] == "validation"


def test_phase_durations_include_observer_work_and_snapshots_are_independent():
    now = [0.0]
    def observer(*a): now[0] += 0.5
    progress = RequestProgress(observer, clock=lambda: now[0])
    progress.start("request")
    now[0] += 2
    progress.start("sources")
    now[0] += 4
    report = progress.finish()
    assert [p["seconds"] for p in report["phases"]] == [2.5, 4.5]
    assert report["elapsed_seconds"] == 7
    report["phases"][0]["label"] = "edited snapshot"
    now[0] += 10
    progress.start("ranking")
    assert progress.finish()["elapsed_seconds"] == 7
    assert progress.finish()["phases"][0]["label"] != "edited snapshot"


def test_two_requests_keep_phase_callbacks_on_their_own_request_threads(catalog, tmp_path):
    barrier = Barrier(2)
    def request(index):
        owner, events = get_ident(), []
        def observe(phase, _):
            assert get_ident() == owner
            events.append(phase)
            if phase == "request": barrier.wait(timeout=5)
        result = run_advisor(catalog, StudentProfile(career_id="embedded" if index else "ai_ml"),
                             refresh_sources=False, cache_dir=tmp_path, progress=observe)
        return result.trace["request_phases"], events
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(request, (0, 1)))
    for report, events in results:
        assert not report["observer_failed"]
        assert [p["phase"] for p in report["phases"]] == events
    results[0][0]["phases"][0]["label"] = "edited snapshot"
    assert results[1][0]["phases"][0]["label"] != "edited snapshot"
