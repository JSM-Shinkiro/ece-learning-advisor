"""Browser-check entrypoint boundaries; full UI acceptance runs in optional Chromium CI."""

import builtins
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.check_browser import main
from src.browser_checks import browser_url, local_browser_server, run_browser_checks, stop_server


@pytest.mark.parametrize("url", ["https://user:private@example.org/app", "https://example.org/?key=private",
    "https://example.org/#private", "file:///tmp/app", "https://example.org:0/app",
    "https://example.org/a/../app", "https://example.org/app\\other", "https://example.org:bad/app"])
def test_browser_target_rejects_ambiguous_or_sensitive_urls_without_echoing_input(url):
    with pytest.raises(ValueError) as error:
        browser_url(url)
    assert url not in str(error.value) and "private" not in str(error.value)


def test_browser_target_preserves_a_plain_host_and_prefix():
    assert browser_url("https://example.org/advisor-check") == "https://example.org/advisor-check/"
    assert browser_url("http://127.0.0.1:8501/") == "http://127.0.0.1:8501/"


def test_existing_browser_report_prevents_starting_a_server_or_browser(tmp_path, monkeypatch):
    output = tmp_path / "keep.json"
    output.write_text("prior evidence")
    def forbidden(*a, **k):
        pytest.fail("An existing report must be rejected before side effects")
    monkeypatch.setattr("src.browser_checks.local_browser_server", forbidden)
    monkeypatch.setattr("src.browser_checks.run_browser_checks", forbidden)
    monkeypatch.setattr(sys, "argv", ["check_browser.py", "--output", str(output)])
    assert main() == 1
    assert output.read_text() == "prior evidence"


def test_browser_failure_is_saved_without_raw_errors_urls_or_profile_data(tmp_path, monkeypatch):
    original = builtins.__import__
    secret = "fixture-private-diagnostic"
    def missing(name, *a, **k):
        if name.startswith("playwright"):
            raise ImportError(secret)
        return original(name, *a, **k)
    monkeypatch.setattr(builtins, "__import__", missing)
    report = run_browser_checks("https://example.org/app")
    assert not report["passed"]
    assert report["checks"][-1]["name"] == "browser_startup"
    assert report["checks"][-1]["error_type"] == "ImportError"
    assert secret not in json.dumps(report) and "example.org" not in json.dumps(report)
    output = tmp_path / "failure.json"
    monkeypatch.setattr(sys, "argv", ["check_browser.py", "--url", "https://example.org/app", "--output", str(output)])
    assert main() == 1
    assert json.loads(output.read_text())["checks"][-1]["error_type"] == "ImportError"


def test_local_browser_server_uses_offline_environment_and_cleans_up_on_workflow_failure(monkeypatch):
    captured = {}
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY", "ADZUNA_APP_ID", "ADZUNA_APP_KEY"):
        monkeypatch.setenv(name, "fixture-private")
    class Process:
        stopped = False
        def poll(self): return 0 if self.stopped else None
        def terminate(self): self.stopped = True
        def wait(self, **kwargs): return 0
    process = Process()
    def spawn(command, **kwargs):
        captured.update(command=command, **kwargs)
        return process
    class Client:
        def __init__(self, **kwargs):
            assert kwargs["trust_env"] is False
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, url):
            assert url.endswith("/advisor-check/_stcore/health")
            return type("Response", (), {"status_code": 200, "text": "ok"})()
    monkeypatch.setattr("src.browser_checks.subprocess.Popen", spawn)
    monkeypatch.setattr("src.browser_checks.httpx.Client", Client)
    with pytest.raises(RuntimeError, match="controlled flow failure"):
        with local_browser_server() as url:
            assert url.startswith("http://127.0.0.1:") and url.endswith("/advisor-check/")
            env = captured["env"]
            assert all(env[name] == "" for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY", "ADZUNA_APP_ID", "ADZUNA_APP_KEY"))
            assert env["ECE_REFRESH_SOURCES"] == env["ECE_DEVELOPMENT_MODE"] == "false"
            assert Path(env["ECE_CACHE_DIR"]).is_dir()
            assert "scripts/serve.py" in captured["command"][1]
            raise RuntimeError("controlled flow failure")
    assert process.stopped and not Path(captured["env"]["ECE_CACHE_DIR"]).exists()


def test_server_cleanup_reaps_a_child_that_ignores_termination():
    calls = []
    class Process:
        def poll(self): return None
        def terminate(self): calls.append("terminate")
        def kill(self): calls.append("kill")
        def wait(self, timeout):
            calls.append("wait")
            if "kill" not in calls:
                raise subprocess.TimeoutExpired("controlled", timeout)
    stop_server(Process())
    assert calls == ["terminate", "wait", "kill", "wait"]
