"""Local deployment preflight and bounded, credential-free startup smoke checks."""

from __future__ import annotations

import importlib.metadata as metadata
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

import httpx

from .catalog import ROOT, build_evidence, load_runtime_catalog
from .discovery import load_discovery_plans
from .hosting import load_server_options
from .models import StudentProfile
from .opportunities import load_employer_boards
from .resource_sources import MAX_RESOURCE_SOURCES, RESOURCE_URLS, prepare_resource_jobs, resource_url_matches
from .settings import ConfigurationError, load_settings


def dependency_versions(root):
    versions = {}
    for line in (root / "requirements.txt").read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        package, required = line.strip().split("==")
        package = package.split("[", 1)[0]
        installed = metadata.version(package)
        versions[package] = {"required": required, "installed": installed}
    return versions


def _cache_probe(settings):
    for name in ("sources", "embeddings"):
        directory = settings.cache_root / name
        directory.mkdir(parents=True, exist_ok=True)
        descriptor, filename = tempfile.mkstemp(prefix="readiness-", dir=directory)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(b"cache readiness\n")
        finally:
            Path(filename).unlink(missing_ok=True)


_PREVIEW_CODE = r'''
import sys
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
root = Path(sys.argv[1])
sys.path.insert(0, str(root))
with patch("httpx.Client.send", side_effect=AssertionError("Network request during offline smoke")) as http, \
     patch("urllib.request.urlopen", side_effect=AssertionError("Network request during offline smoke")) as legacy_http:
    app = AppTest.from_file(root / "app.py", default_timeout=20).run()
    assert not app.exception and not app.error
    assert next(item for item in app.checkbox if item.label == "Generate AI explanations").disabled
    next(button for button in app.button if button.label == "Update my roadmap").click()
    app.run()
    assert not app.exception and not app.error
    result = app.session_state["result"]
    assert result.trace["source_refresh"]["enabled"] is False
    assert not result.generation_complete
    assert "uofa:ECE101:2026-2027" in result.context.allowed_record_ids
    assert not http.called and not legacy_http.called
print("offline-preview-ok")
'''


def startup_smoke(root=ROOT, *, timeout=20, settings=None):
    """Test server liveness and the same app's offline preview in separate children."""
    root = Path(root).resolve()
    try:
        settings = settings or load_settings(root=root)
    except ConfigurationError:
        return {"liveness": False, "offline_preview": False}
    with tempfile.TemporaryDirectory(prefix="ece-startup-") as temporary:
        env = os.environ.copy()
        # Explicit blanks prevent a local .env from reintroducing credentials.
        env.update({name: "" for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "ADZUNA_APP_ID", "ADZUNA_APP_KEY")})
        env.update(ECE_DEVELOPMENT_MODE="false", ECE_REFRESH_SOURCES="false", ECE_CACHE_DIR=temporary,
                   STREAMLIT_BROWSER_GATHER_USAGE_STATS="false", EMBEDDING_MODEL=settings.embedding_model,
                   GENERATION_MODEL=settings.generation_model, EMBEDDING_DIMENSION=str(settings.embedding_dimensions))
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        command = [sys.executable, str(root / "scripts/serve.py"), "--address", "127.0.0.1",
                   "--port", str(port), "--base-path", ""]
        process, live = None, False
        try:
            process = subprocess.Popen(command, cwd=root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            deadline = time.monotonic() + timeout
            with httpx.Client(timeout=0.5, trust_env=False, follow_redirects=False) as client:
                while process.poll() is None and time.monotonic() < deadline:
                    try:
                        with client.stream("GET", "http://127.0.0.1:" + str(port) + "/_stcore/health") as response:
                            body = bytearray()
                            for chunk in response.iter_bytes(chunk_size=64):
                                body.extend(chunk)
                                if len(body) > 128:
                                    break
                            live = response.status_code == 200 and bytes(body).strip() == b"ok"
                        if live:
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.1)
            if not live:
                return {"liveness": False, "offline_preview": False}
            preview = subprocess.run([sys.executable, "-c", _PREVIEW_CODE, str(root)], cwd=root, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=30)
            return {"liveness": process.poll() is None, "offline_preview": preview.returncode == 0
                    and preview.stdout.strip().endswith("offline-preview-ok")}
        except (OSError, subprocess.SubprocessError):
            return {"liveness": live, "offline_preview": False}
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)


def check_deployment(*, root=ROOT, environ=None, smoke=False):
    root = Path(root).resolve()
    report = {"scope": "Local/offline runtime readiness only; external sources and provider credentials are not verified.",
        "model_calls": 0, "external_source_requests": 0, "smoke_requested": smoke, "checks": []}

    def result(name, passed, detail):
        report["checks"].append({"name": name, "passed": bool(passed), "detail": detail})

    try:
        settings = load_settings(environ, root=root)
        report["configuration"] = settings.public_summary()
        result("configuration", True, "Runtime values validated; credentials excluded.")
        result("shared_mode", not settings.development_mode, "Shared hosting requires ECE_DEVELOPMENT_MODE=false.")
    except ConfigurationError as exc:
        result("configuration", False, str(exc))
        report["passed"] = False
        return report
    try:
        report["server"] = load_server_options(environ).public_summary()
        result("server_configuration", True, "Listen address, port, and URL prefix validated; no socket opened.")
    except ConfigurationError as exc:
        result("server_configuration", False, str(exc))
    try:
        report["dependencies"] = dependency_versions(root)
        result("dependencies", bool(report["dependencies"]) and all(v["required"] == v["installed"] for v in report["dependencies"].values()),
               "Installed versions compared with production requirements.")
    except (OSError, ValueError, metadata.PackageNotFoundError):
        result("dependencies", False, "Install the pinned production requirements.")
    try:
        catalog = load_runtime_catalog(root)
        result("catalog", bool(build_evidence(catalog)), "Expanded runtime catalog and frozen baseline validated.")
        plans = load_discovery_plans(root / "data/connectors/course_discovery.json")
        boards = load_employer_boards(root / "data/connectors/employer_boards.json")
        resources, skipped = prepare_resource_jobs(catalog, StudentProfile(career_id="exploring"))
        source_map = {source.source_id: source for source in catalog.sources}
        resource_records = [record for record in catalog.records if record.kind == "resource"]
        result("connectors", bool(plans and boards and len(resources) == min(MAX_RESOURCE_SOURCES, len(resource_records))
            and all(check.status == "skipped" for check in skipped)
            and all(record.record_id in RESOURCE_URLS and record.source_ids[0] == record.record_id
                    and resource_url_matches(record.record_id, source_map[record.source_ids[0]].url)
                    for record in resource_records)),
               "Connector configuration validated without network requests.")
    except (OSError, ValueError, TypeError, KeyError):
        result("catalog_and_connectors", False, "Reviewed data or connector configuration could not be validated.")
    try:
        _cache_probe(settings)
        result("cache", True, "Source and embedding cache directories are writable.")
    except OSError:
        result("cache", False, "Source and embedding cache directories are not writable.")
    if smoke and all(check["passed"] for check in report["checks"]):
        status = startup_smoke(root, settings=settings)
        result("liveness", status["liveness"], "Loopback Streamlit health endpoint.")
        result("offline_preview", status["offline_preview"], "Credential-free preview roadmap; HTTP clients blocked.")
    report["passed"] = all(check["passed"] for check in report["checks"])
    return report
