"""Host bindings and startup failures, with no external services or model calls."""

import builtins
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from src.catalog import ROOT
from src.deployment import check_deployment
from src import hosting
from src.hosting import launch_server, load_server_options
from src.settings import ConfigurationError


SECRET = "fixture-private-startup-diagnostic"


def test_default_shared_server_options_do_not_open_files_or_start_services():
    options = load_server_options({})
    assert options.public_summary() == {"address": "0.0.0.0", "port": 8501, "base_path": "", "health_path": "/_stcore/health"}


@pytest.mark.parametrize("env,port", [({"PORT": "8100"}, 8100), ({"STREAMLIT_SERVER_PORT": "8101"}, 8101),
    ({"PORT": "8102", "STREAMLIT_SERVER_PORT": "8103"}, 8102), ({"PORT": "1"}, 1), ({"PORT": "65535"}, 65535)])
def test_host_port_precedence_and_range_boundaries(env, port):
    assert load_server_options(env).port == port


def test_explicit_bindings_override_invalid_environment_values_without_echoing_them(tmp_path):
    env = {key: SECRET for key in ("PORT", "STREAMLIT_SERVER_PORT", "STREAMLIT_SERVER_ADDRESS", "STREAMLIT_SERVER_BASE_URL_PATH")}
    env["GEMINI_API_KEY"] = SECRET
    options = load_server_options(env, port="8300", address="127.0.0.1", base_path="")
    rewritten = options.environment(env)
    assert rewritten["PORT"] == rewritten["STREAMLIT_SERVER_PORT"] == "8300"
    assert rewritten["STREAMLIT_SERVER_ADDRESS"] == "127.0.0.1" and rewritten["STREAMLIT_SERVER_BASE_URL_PATH"] == ""
    assert rewritten["GEMINI_API_KEY"] == SECRET and env["PORT"] == SECRET
    assert SECRET not in json.dumps(options.public_summary()) + repr(options) + str(options.command(root=tmp_path))


@pytest.mark.parametrize("env,expected", [
    ({"STREAMLIT_SERVER_ADDRESS": "LOCALHOST", "STREAMLIT_SERVER_BASE_URL_PATH": "/"}, ("localhost", "", "/_stcore/health")),
    ({"STREAMLIT_SERVER_ADDRESS": "127.0.0.1", "STREAMLIT_SERVER_BASE_URL_PATH": "/ece/advisor/"}, ("127.0.0.1", "ece/advisor", "/ece/advisor/_stcore/health")),
    ({"STREAMLIT_SERVER_ADDRESS": "2001:0db8::1", "STREAMLIT_SERVER_BASE_URL_PATH": "advisor-v1"}, ("2001:db8::1", "advisor-v1", "/advisor-v1/_stcore/health")),
])
def test_address_and_prefix_normalization(env, expected):
    options = load_server_options(env)
    assert (options.address, options.base_path, options.public_summary()["health_path"]) == expected


@pytest.mark.parametrize("name,value", [
    ("PORT", "0"), ("PORT", "65536"), ("PORT", ""), ("PORT", "8501.5"),
    ("PORT", "--server.port=1234"), ("PORT", True), ("STREAMLIT_SERVER_PORT", "9" * 20),
    ("STREAMLIT_SERVER_ADDRESS", "https://invalid.example/" + SECRET),
    ("STREAMLIT_SERVER_ADDRESS", ""), ("STREAMLIT_SERVER_ADDRESS", "unreviewed-hostname"),
    ("STREAMLIT_SERVER_ADDRESS", "fe80::1%eth0"),
    ("STREAMLIT_SERVER_BASE_URL_PATH", "../advisor"), ("STREAMLIT_SERVER_BASE_URL_PATH", "ece//advisor"),
    ("STREAMLIT_SERVER_BASE_URL_PATH", "https://invalid.example/" + SECRET),
    ("STREAMLIT_SERVER_BASE_URL_PATH", "ece%2Fadvisor"), ("STREAMLIT_SERVER_BASE_URL_PATH", "ece\nadvisor"),
    ("STREAMLIT_SERVER_BASE_URL_PATH", "x" * 201),
])
def test_invalid_server_values_have_safe_field_errors(name, value):
    with pytest.raises(ConfigurationError) as error:
        load_server_options({name: value})
    assert name in str(error.value) and SECRET not in str(error.value)
    if isinstance(value, str) and len(value) > 8:
        assert value not in str(error.value)


def test_launch_command_uses_the_current_python_and_absolute_app_path_without_a_shell(tmp_path):
    root = tmp_path / "project with spaces"
    options = load_server_options({}, address="127.0.0.1", port=8600, base_path="/advisor/")
    command = options.command(root=root)
    assert command[:5] == [sys.executable, "-m", "streamlit", "run", str(root / "app.py")]
    assert "--server.port=8600" in command and "--server.baseUrlPath=advisor" in command
    assert "--server.headless=true" in command and "--server.fileWatcherType=none" in command
    assert "--browser.gatherUsageStats=false" in command


@pytest.mark.parametrize("field", ["PORT", "STREAMLIT_SERVER_ADDRESS", "STREAMLIT_SERVER_BASE_URL_PATH"])
def test_readiness_rejects_invalid_server_bindings_before_smoke(tmp_path, monkeypatch, field):
    monkeypatch.setattr("src.deployment.startup_smoke", lambda *a, **k: pytest.fail("Invalid bindings must not open a server"))
    report = check_deployment(environ={"ECE_CACHE_DIR": str(tmp_path), field: "invalid:" + SECRET}, smoke=True)
    assert not report["passed"] and not next(c["passed"] for c in report["checks"] if c["name"] == "server_configuration")
    assert SECRET not in json.dumps(report)


def test_readiness_records_bindings_and_keeps_liveness_and_preview_separate(tmp_path, monkeypatch):
    monkeypatch.setattr("src.deployment.startup_smoke", lambda *a, **k: {"liveness": True, "offline_preview": True})
    report = check_deployment(environ={"PORT": "8301", "STREAMLIT_SERVER_BASE_URL_PATH": "/advisor/", "ECE_CACHE_DIR": str(tmp_path)}, smoke=True)
    assert report["passed"] and len(report["checks"]) == 9
    assert report["server"]["port"] == 8301 and report["server"]["health_path"] == "/advisor/_stcore/health"
    assert report["model_calls"] == report["external_source_requests"] == 0


def cli_setup(monkeypatch, tmp_path):
    from scripts import serve
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    for key in ("PORT", "STREAMLIT_SERVER_PORT", "STREAMLIT_SERVER_ADDRESS", "STREAMLIT_SERVER_BASE_URL_PATH"):
        monkeypatch.delenv(key, raising=False)
    for key, value in {"ECE_CACHE_DIR": str(tmp_path / "cache"), "ECE_DEVELOPMENT_MODE": "false", "ECE_REFRESH_SOURCES": "false",
        "EMBEDDING_MODEL": "gemini-embedding-2", "GENERATION_MODEL": "gemini-3.5-flash-lite", "EMBEDDING_DIMENSION": "768",
        "GEMINI_API_KEY": SECRET, "GOOGLE_API_KEY": "", "ADZUNA_APP_ID": "", "ADZUNA_APP_KEY": ""}.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(sys, "argv", ["serve"])
    monkeypatch.setattr(serve.os, "execve", lambda *a, **k: pytest.fail("Invalid/check-only launch must not execute a server"))
    monkeypatch.setattr(hosting, "launch_server", lambda *a, **k: pytest.fail("Invalid/check-only launch must not enter a server"))
    monkeypatch.setattr(serve.os, "chdir", lambda *a: pytest.fail("Invalid/check-only launch must not change directories"))
    return serve


def test_check_only_validates_and_redacts_without_starting_a_server(tmp_path, monkeypatch, capsys):
    cli = cli_setup(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv", ["serve", "--check", "--port", "8302"])
    assert cli.main() == 0
    logs = capsys.readouterr()
    report = json.loads(logs.out)
    assert report["passed"] and not report["smoke_requested"] and len(report["checks"]) == 7
    assert report["server"]["port"] == 8302 and report["configuration"]["ai_key_present"]
    assert SECRET not in logs.out + logs.err


def test_valid_launch_passes_credentials_only_through_environment_and_uses_project_directory(tmp_path, monkeypatch, capsys):
    cli = cli_setup(monkeypatch, tmp_path)
    captured = {}
    monkeypatch.setenv("PORT", SECRET)
    monkeypatch.setattr(sys, "argv", ["serve", "--port", "8303", "--address", "127.0.0.1", "--base-path", "advisor"])
    monkeypatch.setattr(cli.os, "chdir", lambda path: captured.update(cwd=path))
    def capture(options, env, *, root):
        command = options.command(root=root)
        captured.update(executable=command[0], command=command, env=env)
    monkeypatch.setattr(hosting, "launch_server", capture)
    assert cli.main() == 0
    assert captured["cwd"] == ROOT and captured["executable"] == sys.executable
    assert captured["env"]["GEMINI_API_KEY"] == SECRET
    assert captured["env"]["PORT"] == captured["env"]["STREAMLIT_SERVER_PORT"] == "8303"
    assert "--server.baseUrlPath=advisor" in captured["command"]
    logs = capsys.readouterr()
    assert SECRET not in str(captured["command"]) + logs.out + logs.err


@pytest.mark.parametrize("fault", ["shared_mode", "runtime_settings", "cache", "port"])
def test_failed_startup_cannot_execute_a_server_or_echo_private_values(tmp_path, monkeypatch, capsys, fault):
    cli = cli_setup(monkeypatch, tmp_path)
    if fault == "shared_mode":
        monkeypatch.setenv("ECE_DEVELOPMENT_MODE", "true")
    elif fault == "runtime_settings":
        monkeypatch.setenv("EMBEDDING_DIMENSION", SECRET)
    elif fault == "cache":
        blocked = tmp_path / "existing-file"
        blocked.write_text("keep")
        monkeypatch.setenv("ECE_CACHE_DIR", str(blocked))
    else:
        monkeypatch.setenv("PORT", SECRET)
    assert cli.main() == 1
    logs = capsys.readouterr()
    assert SECRET not in logs.out + logs.err
    if fault == "cache":
        assert blocked.read_text() == "keep"


@pytest.mark.parametrize("stage", ["dotenv", "exec"])
def test_operating_system_failures_have_safe_diagnostics(tmp_path, monkeypatch, capsys, stage):
    cli = cli_setup(monkeypatch, tmp_path)

    def broken(*a, **k):
        raise OSError(SECRET)

    if stage == "dotenv":
        monkeypatch.setattr("dotenv.load_dotenv", broken)
    else:
        monkeypatch.setattr(cli.os, "chdir", lambda *a: None)
        monkeypatch.setattr(hosting, "launch_server", broken)
    assert cli.main() == 1
    logs = capsys.readouterr()
    assert SECRET not in logs.out + logs.err


def test_missing_runtime_dependencies_do_not_echo_import_diagnostics(tmp_path, monkeypatch, capsys):
    cli = cli_setup(monkeypatch, tmp_path)
    original = builtins.__import__

    def missing(name, *args, **kwargs):
        if name == "dotenv":
            raise ImportError(SECRET)
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing)
    assert cli.main() == 1
    logs = capsys.readouterr()
    assert "requirements.txt" in logs.err and SECRET not in logs.out + logs.err


def test_check_command_works_from_another_directory(tmp_path):
    env = os.environ.copy()
    env.update({key: "" for key in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "ADZUNA_APP_ID", "ADZUNA_APP_KEY"]})
    env.update(ECE_CACHE_DIR=str(tmp_path / "cache"), ECE_DEVELOPMENT_MODE="false", ECE_REFRESH_SOURCES="false",
        EMBEDDING_DIMENSION="768", EMBEDDING_MODEL="gemini-embedding-2", GENERATION_MODEL="gemini-3.5-flash-lite",
        PORT="8304", STREAMLIT_SERVER_ADDRESS="127.0.0.1", STREAMLIT_SERVER_BASE_URL_PATH="advisor")
    result = subprocess.run([sys.executable, str(ROOT / "scripts/serve.py"), "--check"], cwd=tmp_path,
        env=env, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["passed"] and report["server"]["port"] == 8304
    assert report["server"]["health_path"] == "/advisor/_stcore/health"
    assert not report["configuration"]["ai_key_present"]


def test_posix_launch_uses_process_replacement_with_private_values_only_in_environment(tmp_path, monkeypatch):
    options = load_server_options({}, port=8400)
    env = {"GEMINI_API_KEY": SECRET}
    captured = {}
    monkeypatch.setattr(hosting.os, "execve", lambda executable, command, environment: captured.update(
        executable=executable, command=command, environment=environment))
    monkeypatch.setattr(hosting.runpy, "run_module", lambda *a, **k: pytest.fail("POSIX must replace the launcher"))
    launch_server(options, env, root=tmp_path, platform="linux")
    assert captured["executable"] == sys.executable and captured["environment"] is env
    assert captured["command"] == options.command(root=tmp_path)
    assert SECRET not in str(captured["command"])


@pytest.mark.parametrize("outcome", ["return", "exit", "failure", "interrupted"])
def test_windows_entrypoint_stays_in_process_and_restores_startup_state(tmp_path, monkeypatch, outcome):
    options = load_server_options({}, address="127.0.0.1", port=8401, base_path="advisor")
    before_env, before_argv = os.environ.copy(), sys.argv
    env = options.environment(before_env)
    env.update(GEMINI_API_KEY=SECRET, HOSTING_ONLY_DURING_START="controlled")
    captured = {}
    monkeypatch.setattr(hosting.os, "execve", lambda *a: pytest.fail("Windows must not detach through execve"))

    def module(name, **kwargs):
        captured.update(name=name, kwargs=kwargs, argv=list(sys.argv), pid=os.getpid())
        assert os.environ["GEMINI_API_KEY"] == SECRET and os.environ["PORT"] == "8401"
        assert os.environ["HOSTING_ONLY_DURING_START"] == "controlled"
        if outcome == "exit":
            raise SystemExit(0)
        if outcome == "failure":
            raise RuntimeError(SECRET)
        if outcome == "interrupted":
            raise KeyboardInterrupt()

    monkeypatch.setattr(hosting.runpy, "run_module", module)
    try:
        if outcome == "return":
            launch_server(options, env, root=tmp_path, platform="win32")
        else:
            expected = {"exit": SystemExit, "failure": RuntimeError, "interrupted": KeyboardInterrupt}[outcome]
            with pytest.raises(expected):
                launch_server(options, env, root=tmp_path, platform="win32")
    finally:
        assert sys.argv is before_argv and dict(os.environ) == before_env
    assert captured["name"] == "streamlit" and captured["kwargs"] == {"run_name": "__main__", "alter_sys": True}
    assert captured["argv"] == ["streamlit", *options.command(root=tmp_path)[3:]]
    assert captured["pid"] == os.getpid() and SECRET not in str(captured["argv"])
