"""Measurement scope, failure retention and report boundaries; Chromium runs in CI."""

import builtins
from contextlib import contextmanager
import json
import sys

import pytest

from scripts.measure_browser import main
from src.browser_performance import METRICS, duration, preview_metadata, run_browser_measurements, summarize


def trace():
    return {"data_version": "fixture-v1", "corpus_hash": "a" * 64, "generation_complete": False,
            "generation_status": "not_requested", "embedding_model": None, "generation_model": None,
            "retrieval_mode": "keyword", "cache_state": "not_used", "source_refresh": {"enabled": False},
            "timings_seconds": {"total": 0.00123456, "retrieval": 0.00012345},
            "question": "private-profile", "source_freshness": {"private-url": "private-text"}}


@pytest.mark.parametrize("value", [True, False, None, "0", -1, float("nan"), float("inf"), -float("inf")])
def test_invalid_measurements_cannot_be_reported_as_finite_timings(value):
    with pytest.raises(ValueError):
        duration(value)


@pytest.mark.parametrize("change", [{"generation_complete": True}, {"generation_status": "failed"},
    {"embedding_model": "real-model"}, {"generation_model": "real-model"}, {"retrieval_mode": "hybrid"},
    {"cache_state": "hit"}, {"source_refresh": {"enabled": True}}, {"source_refresh": {}},
    {"corpus_hash": "missing"}, {"data_version": "private profile text"}, {"timings_seconds": {}},
    {"timings_seconds": {"total": float("nan")}}])
def test_ai_network_and_unidentified_collections_cannot_enter_preview_cohort(change):
    value = trace()
    value.update(change)
    with pytest.raises(ValueError):
        preview_metadata(value)


def test_downloaded_trace_whitelist_preserves_actual_provenance_without_personal_fields():
    from src.catalog import load_runtime_catalog
    from src.controller import run_advisor
    from src.models import StudentProfile
    result = run_advisor(load_runtime_catalog(), StudentProfile(), use_ai=False, refresh_sources=False)
    result.trace.update(question="private-profile", arbitrary_error="private-diagnostic")
    metadata = preview_metadata(result.trace)
    assert metadata["corpus_hash"] == result.trace["corpus_hash"]
    assert metadata["timings_seconds"]["total"] >= 0
    assert "private" not in json.dumps(metadata)
    assert metadata["source_refresh_enabled"] is False


def test_failed_or_partial_samples_stay_out_of_summary_without_being_deleted():
    rows = [{"passed": True, "metrics_ms": dict.fromkeys(METRICS, value)} for value in [10, 20, 90]]
    rows.append({"passed": False, "metrics_ms": {"navigation_to_interactive_ms": 9999},
                 "failure": {"stage": "roadmap", "error_type": "TimeoutError"}})
    summary = summarize(rows)
    assert summary[METRICS[0]] == {"n": 3, "min": 10, "median": 20, "max": 90}
    assert len(rows) == 4 and not rows[-1]["passed"]
    assert summarize([rows[-1]]) == {}
    rows[0]["metrics_ms"][METRICS[0]] = float("inf")
    with pytest.raises(ValueError):
        summarize(rows)


def test_existing_evidence_prevents_server_or_browser_side_effects(tmp_path, monkeypatch):
    output = tmp_path / "keep.json"
    output.write_text("original")
    def forbidden(*args, **kwargs):
        pytest.fail("No process should start before output reservation")
    monkeypatch.setattr("src.browser_checks.local_browser_server", forbidden)
    monkeypatch.setattr("src.browser_performance.run_browser_measurements", forbidden)
    monkeypatch.setattr(sys, "argv", ["measure_browser.py", "--output", str(output)])
    assert main() == 1 and output.read_text() == "original"


def test_startup_failure_is_saved_without_raw_error_details(tmp_path, monkeypatch):
    output = tmp_path / "new.json"
    @contextmanager
    def failed():
        assert output.exists()
        raise OSError("private-path-or-key")
        yield
    monkeypatch.setattr("src.browser_checks.local_browser_server", failed)
    monkeypatch.setattr(sys, "argv", ["measure_browser.py", "--output", str(output)])
    assert main() == 1
    report = json.loads(output.read_text())
    assert report["failure"]["error_type"] == "OSError" and report["samples"] == []
    assert "private" not in output.read_text() and report["checked_at"]


@pytest.mark.parametrize("count", [1, 21])
def test_invalid_sample_count_is_rejected_before_file_or_process_changes(count, tmp_path, monkeypatch):
    output = tmp_path / "new.json"
    monkeypatch.setattr(sys, "argv", ["measure_browser.py", "--samples", str(count), "--output", str(output)])
    with pytest.raises(SystemExit):
        main()
    assert not output.exists()


def test_optional_browser_failure_retains_scope_without_exposing_target_or_exception(monkeypatch):
    original = builtins.__import__
    def missing(name, *args, **kwargs):
        if name.startswith("playwright"):
            raise ImportError("private-diagnostic")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", missing)
    report = run_browser_measurements("http://127.0.0.1:8765/advisor-check/", samples=2)
    assert not report["passed"] and report["successful_samples"] == 0
    assert report["failure"] == {"stage": "browser_startup", "error_type": "ImportError"}
    assert "private" not in json.dumps(report) and "8765" not in json.dumps(report)


def test_measurement_never_accepts_an_unisolated_public_host():
    with pytest.raises(ValueError):
        run_browser_measurements("https://example.org")
