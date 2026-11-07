"""Preflight failure handling; real startup is verified by the separate smoke CLI."""

import importlib.metadata as metadata
import json
import os
import subprocess
import sys

import pytest

from src.deployment import check_deployment, startup_smoke
from src.settings import load_settings
from src.catalog import ROOT


def checks(report):
    return {item["name"]: item["passed"] for item in report["checks"]}


def test_preflight_validates_local_inputs_without_provider_or_source_requests(tmp_path, monkeypatch):
    def forbidden(*a, **k): pytest.fail("Preflight must not call remote services")
    monkeypatch.setattr("httpx.Client.send", forbidden)
    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    report = check_deployment(environ={"ECE_CACHE_DIR": str(tmp_path)})
    assert report["passed"] and all(checks(report).values())
    assert report["model_calls"] == report["external_source_requests"] == 0


def test_preflight_report_excludes_credentials_and_raw_configuration_errors(tmp_path):
    secret = "fixture-never-in-report"
    report = check_deployment(environ={"GEMINI_API_KEY": secret, "ECE_CACHE_DIR": str(tmp_path)})
    assert report["configuration"]["ai_key_present"]
    assert secret not in json.dumps(report)
    report = check_deployment(environ={"EMBEDDING_MODEL": secret}, smoke=True)
    assert not report["passed"] and report["smoke_requested"]
    assert secret not in json.dumps(report)


def test_development_widgets_prevent_shared_deployment_readiness(tmp_path, monkeypatch):
    monkeypatch.setattr("src.deployment.startup_smoke", lambda *a, **k: pytest.fail("Invalid shared mode must not start a server"))
    report = check_deployment(environ={"ECE_DEVELOPMENT_MODE": "true", "ECE_CACHE_DIR": str(tmp_path)}, smoke=True)
    assert not report["passed"] and not checks(report)["shared_mode"]


def test_missing_dependency_is_a_structured_failure(tmp_path, monkeypatch):
    def missing(name): raise metadata.PackageNotFoundError(name)
    monkeypatch.setattr("src.deployment.metadata.version", missing)
    report = check_deployment(environ={"ECE_CACHE_DIR": str(tmp_path)})
    assert not report["passed"] and not checks(report)["dependencies"]


def test_corrupt_catalog_does_not_expose_raw_parser_diagnostics(tmp_path, monkeypatch):
    def fail(*a, **k): raise ValueError("private-parser-diagnostic")
    monkeypatch.setattr("src.deployment.load_runtime_catalog", fail)
    report = check_deployment(environ={"ECE_CACHE_DIR": str(tmp_path)})
    assert not report["passed"] and not checks(report)["catalog_and_connectors"]
    assert "private-parser-diagnostic" not in json.dumps(report)


def test_cache_probe_preserves_existing_files_when_the_path_is_not_a_directory(tmp_path):
    cache = tmp_path / "existing-file"
    cache.write_text("keep this file")
    report = check_deployment(environ={"ECE_CACHE_DIR": str(cache)})
    assert not report["passed"] and not checks(report)["cache"]
    assert cache.read_text() == "keep this file"


@pytest.mark.parametrize("live,preview", [(True, True), (True, False), (False, False)])
def test_liveness_alone_cannot_pass_the_requested_startup_check(tmp_path, monkeypatch, live, preview):
    monkeypatch.setattr("src.deployment.startup_smoke", lambda *a, **k: {"liveness": live, "offline_preview": preview})
    report = check_deployment(environ={"ECE_CACHE_DIR": str(tmp_path)}, smoke=True)
    assert checks(report)["liveness"] is live and checks(report)["offline_preview"] is preview
    assert report["passed"] is (live and preview)


def test_failed_server_launch_returns_a_sanitized_status(monkeypatch):
    def fail(*a, **k): raise OSError("private-process-diagnostic")
    monkeypatch.setattr("src.deployment.subprocess.Popen", fail)
    assert startup_smoke() == {"liveness": False, "offline_preview": False}


def test_smoke_child_gets_no_credentials_and_is_terminated_on_timeout(monkeypatch):
    captured = {}
    class Process:
        terminated = False
        def poll(self): return 0 if self.terminated else None
        def terminate(self): self.terminated = True
        def wait(self, **kwargs): return 0
    process = Process()
    def start(*args, **kwargs): captured.update(kwargs); captured["command"] = args[0]; return process
    monkeypatch.setenv("GEMINI_API_KEY", "fixture-private-parent-key")
    monkeypatch.setattr("src.deployment.subprocess.Popen", start)
    settings = load_settings({"EMBEDDING_DIMENSION": "1536", "GENERATION_MODEL": "gemini-fixture-model"})
    assert startup_smoke(timeout=0, settings=settings) == {"liveness": False, "offline_preview": False}
    assert process.terminated
    assert all(captured["env"][name] == "" for name in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "ADZUNA_APP_ID", "ADZUNA_APP_KEY"])
    assert captured["env"]["ECE_REFRESH_SOURCES"] == captured["env"]["ECE_DEVELOPMENT_MODE"] == "false"
    assert captured["env"]["EMBEDDING_DIMENSION"] == "1536"
    assert captured["env"]["GENERATION_MODEL"] == "gemini-fixture-model"
    assert captured["command"][:2] == [sys.executable, str(ROOT / "scripts/serve.py")]
    assert captured["command"][-2:] == ["--base-path", ""]


def test_cli_report_uses_the_configured_cache_even_from_another_directory(tmp_path):
    env = os.environ.copy()
    env.update({key: "" for key in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "ADZUNA_APP_ID", "ADZUNA_APP_KEY"]})
    env.update(ECE_CACHE_DIR=str(tmp_path / "runtime"), ECE_DEVELOPMENT_MODE="false", ECE_REFRESH_SOURCES="false",
        EMBEDDING_DIMENSION="768", EMBEDDING_MODEL="gemini-embedding-2", GENERATION_MODEL="gemini-3.5-flash-lite")
    result = subprocess.run([sys.executable, str(ROOT / "scripts/check_deployment.py")], cwd=tmp_path,
        env=env, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0
    report = json.loads((tmp_path / "runtime/deployment_check.json").read_text())
    assert report["passed"] and not report["smoke_requested"]
    assert report["configuration"]["refresh_sources"] is False
