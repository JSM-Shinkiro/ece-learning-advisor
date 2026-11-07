"""Real Streamlit browser acceptance flow, with controlled profiles and count-only diagnostics."""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
import traceback
from urllib.parse import urlsplit, urlunsplit

import httpx

from .catalog import ROOT


def browser_url(value: str) -> str:
    """Accept a plain app URL, never credentials, query strings, or fragments."""
    try:
        parsed = urlsplit(value)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.query or parsed.fragment or parsed.port == 0
                or re.search(r"[\s\\]", value)
                or not re.fullmatch(r"(?:/[A-Za-z0-9_-]+)*/?", parsed.path)):
            raise ValueError
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/") + "/", "", ""))
    except ValueError:
        raise ValueError("Use an http(s) app URL with an optional simple path, without credentials, query, or fragment.") from None


def stop_server(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)


@contextmanager
def local_browser_server(*, root=ROOT, timeout=25):
    """Use the production launcher, a URL prefix, and isolated offline settings."""
    with tempfile.TemporaryDirectory(prefix="ece-browser-server-") as temporary:
        env = os.environ.copy()
        env.update({key: "" for key in (
            "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY", "ADZUNA_APP_ID", "ADZUNA_APP_KEY")})
        env.update(ECE_DEVELOPMENT_MODE="false", ECE_REFRESH_SOURCES="false", ECE_CACHE_DIR=temporary,
                   STREAMLIT_BROWSER_GATHER_USAGE_STATS="false")
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        url = f"http://127.0.0.1:{port}/advisor-check/"
        process = subprocess.Popen(
            [sys.executable, str(Path(root) / "scripts/serve.py"), "--address", "127.0.0.1",
             "--port", str(port), "--base-path", "advisor-check"],
            cwd=root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + timeout
            with httpx.Client(timeout=0.5, trust_env=False, follow_redirects=False) as client:
                while process.poll() is None and time.monotonic() < deadline:
                    try:
                        response = client.get(url + "_stcore/health")
                        if response.status_code == 200 and response.text.strip() == "ok":
                            break
                    except httpx.HTTPError:
                        pass
                    time.sleep(0.1)
                else:
                    raise RuntimeError("The isolated production server did not become healthy.")
            yield url
        finally:
            stop_server(process)


def run_browser_checks(url, *, local=False, executable_path=None, timeout_ms=20000):
    """Exercise two real sessions; return no profile data, frame payloads, or raw errors."""
    report = {"passed": False, "mode": "local_offline" if local else "provided_host",
              "checks": [], "sessions": [], "browser": None,
              "external_browser_requests_blocked": 0,
              "limits": ["Preview mode only; no AI, relevance, or participant evaluation.",
                         "Local checks do not establish public-host availability or TLS/proxy behavior.",
                         "Browser request counts do not measure server-side network calls."]}
    stage = "browser_startup"
    started = time.monotonic()

    def passed(name, detail, begin):
        report["checks"].append({"name": name, "passed": True, "detail": detail,
                                 "seconds": round(time.monotonic() - begin, 3)})

    try:
        # Keep this optional dependency out of production and the ordinary pytest suite.
        from playwright.sync_api import expect, sync_playwright

        url = browser_url(url)
        origin = urlsplit(url)
        stream_path = origin.path + "_stcore/stream"
        with tempfile.TemporaryDirectory(prefix="ece-browser-downloads-") as temporary, sync_playwright() as driver:
            browser = driver.chromium.launch(executable_path=executable_path)
            report["browser"] = {"engine": "chromium", "version": browser.version}
            contexts = []
            try:
                def new_session():
                    context = browser.new_context(accept_downloads=True, viewport={"width": 1500, "height": 1100})
                    contexts.append(context)
                    counts = {"stream_connections": 0, "frames_sent": 0, "frames_received": 0,
                              "streams_closed": 0, "page_errors": 0}
                    report["sessions"].append(counts)

                    def route_request(route):
                        target = urlsplit(route.request.url)
                        if (target.scheme, target.netloc) == (origin.scheme, origin.netloc):
                            route.continue_()
                        else:
                            report["external_browser_requests_blocked"] += 1
                            route.abort()

                    context.route("**/*", route_request)
                    page = context.new_page()
                    page.set_default_timeout(timeout_ms)
                    page.set_default_navigation_timeout(timeout_ms)

                    def increment(key):
                        counts[key] += 1

                    def websocket(stream):
                        if urlsplit(stream.url).path == stream_path:
                            increment("stream_connections")
                            stream.on("framesent", lambda _: increment("frames_sent"))
                            stream.on("framereceived", lambda _: increment("frames_received"))
                            stream.on("close", lambda: increment("streams_closed"))

                    page.on("websocket", websocket)
                    page.on("pageerror", lambda _: increment("page_errors"))
                    page.goto(url, wait_until="domcontentloaded")
                    expect(page.get_by_role("heading", name="Your next step, with a path forward.", exact=True)).to_be_visible(timeout=timeout_ms)
                    return page

                def expand(page, label):
                    summary = page.locator("summary").filter(has=page.get_by_text(label, exact=True))
                    if summary.locator("..").get_attribute("open") is None:
                        summary.click()

                def choose(page, label, value):
                    page.get_by_role("combobox", name=label, exact=True).click()
                    page.get_by_role("option", name=value, exact=True).click()

                def saved(page, career, completed, current):
                    expect(page.get_by_text(
                        f"Saved profile: Incoming · {career} · {completed} completed courses · {current} currently taking",
                        exact=True)).to_be_visible(timeout=timeout_ms)

                def export(page, name):
                    expand(page, "Saved profile")
                    with page.expect_download(timeout=timeout_ms) as pending:
                        page.get_by_role("button", name="Download my profile", exact=True).click()
                    path = Path(temporary) / name
                    pending.value.save_as(path)
                    return path, json.loads(path.read_text(encoding="utf-8"))

                def submit(page):
                    page.get_by_role("button", name="Update my roadmap", exact=True).click()

                def course_cards(page):
                    return page.get_by_role("tabpanel", name="My Roadmap").locator("strong").filter(
                        has_text=re.compile(r"^[A-Z]+\d+[A-Z]? · "))

                stage, begin = "initial_roadmap", time.monotonic()
                a = new_session()
                expand(a, "AI and ranking options")
                ai = a.get_by_role("checkbox", name="Generate AI explanations", exact=True)
                expect(ai).not_to_be_checked()
                if local:
                    expect(ai).to_be_disabled()
                submit(a)
                saved(a, "AI / Machine Learning", 0, 0)
                expect(course_cards(a).filter(has_text=re.compile(r"^ECE101 · "))).to_have_count(1)
                if local:
                    expect(a.get_by_text("Official-source checks are disabled. Showing dated saved evidence.", exact=True)).to_be_visible()
                passed(stage, "Production UI renders and submits a preview roadmap; AI remains off.", begin)

                stage, begin = "current_course_filtering", time.monotonic()
                choose(a, "Career direction", "Embedded Systems")
                a.get_by_role("textbox", name="What interests you?", exact=True).fill("Microcontrollers and robotics")
                current = a.get_by_role("combobox", name="Currently taking (optional)", exact=True)
                current.fill("ECE101")
                a.get_by_role("option").filter(has_text=re.compile(r"^ECE101 · ")).click()
                current.press("Escape")
                submit(a)
                saved(a, "Embedded Systems", 0, 1)
                expect(a.get_by_text("Currently taking (1)", exact=True)).to_be_visible()
                expect(course_cards(a).filter(has_text=re.compile(r"^ECE101 · "))).to_have_count(0)
                passed(stage, "Current ECE101 is visible as coursework and absent from next-step cards.", begin)

                stage, begin = "completion_transition", time.monotonic()
                current_section = a.get_by_test_id("stExpander").filter(has=a.get_by_text("Currently taking (1)", exact=True))
                current_section.get_by_role("button", name="Mark completed", exact=True).click()
                saved(a, "Embedded Systems", 1, 0)
                expect(a.get_by_text("Completed coursework (1)", exact=True)).to_be_visible()
                _, completed = export(a, "completed.json")
                assert completed["completed"] == [{"course_code": "ECE101", "grade": None}]
                assert completed["current_enrollment"] == []
                passed(stage, "Completion moves ECE101 out of current study and retains its unknown grade.", begin)

                stage, begin = "profile_export", time.monotonic()
                expand(a, "Optional details")
                a.get_by_role("textbox", name="Other current course codes", exact=True).fill("MATH129")
                submit(a)
                saved(a, "Embedded Systems", 1, 1)
                original_path, original = export(a, "original.json")
                assert original["career_id"] == "embedded" and original["current_enrollment"] == ["MATH129"]
                assert original["interests"] == "Microcontrollers and robotics"
                passed(stage, "The UI downloads a valid controlled profile including manual current coursework.", begin)

                stage, begin = "profile_restore", time.monotonic()
                choose(a, "Career direction", "AI / Machine Learning")
                a.get_by_role("textbox", name="What interests you?", exact=True).fill("Temporary edit")
                submit(a)
                saved(a, "AI / Machine Learning", 1, 1)
                expand(a, "Saved profile")
                a.get_by_label("Restore a saved profile", exact=True).set_input_files(original_path)
                saved(a, "Embedded Systems", 1, 1)
                expect(a.get_by_role("textbox", name="What interests you?", exact=True)).to_have_value("Microcontrollers and robotics")
                _, restored = export(a, "restored.json")
                assert restored == original
                passed(stage, "An uploaded UI export restores the edited profile exactly, including all saved fields.", begin)

                stage, begin = "session_isolation", time.monotonic()
                b = new_session()
                saved(b, "AI / Machine Learning", 0, 0)
                b.get_by_role("textbox", name="What interests you?", exact=True).fill("Computer vision and neural networks")
                submit(b)
                saved(b, "AI / Machine Learning", 0, 0)
                _, independent = export(b, "independent.json")
                assert independent["completed"] == [] and independent["current_enrollment"] == []
                assert independent["interests"] == "Computer vision and neural networks"
                _, unchanged = export(a, "unchanged.json")
                assert unchanged == original
                passed(stage, "Two isolated browser contexts retain different profiles while both sessions remain open.", begin)

                stage, begin = "unsupported_request", time.monotonic()
                b.get_by_role("textbox", name="What interests you?", exact=True).fill("")
                expand(b, "Optional details")
                b.get_by_role("textbox", name="A question about your next step", exact=True).fill("I want to study marine biology and coral reef ecology")
                submit(b)
                expect(b.get_by_text(re.compile(r"This starter collection covers AI/ML, embedded systems, and programming foundations\."))).to_be_visible()
                expect(course_cards(b)).to_have_count(0)
                _, unchanged = export(a, "still-unchanged.json")
                assert unchanged == original
                passed(stage, "An unsupported question requests clarification, without course cards or cross-session changes.", begin)

                stage, begin = "websocket_sessions", time.monotonic()
                for page in (a, b):
                    expect(page.get_by_role("heading", name="Your next step, with a path forward.", exact=True)).to_be_visible()
                assert all(item["stream_connections"] >= 1 and item["frames_sent"] > 0
                           and item["frames_received"] > 0 and item["streams_closed"] == 0
                           and item["page_errors"] == 0 for item in report["sessions"])
                passed(stage, "Both real Streamlit WebSockets exchange frames with no stream closure or page JavaScript errors.", begin)
                report["passed"] = True
            finally:
                # Snapshot the in-session counters before intentional cleanup closes sockets.
                report["sessions"] = [dict(item) for item in report["sessions"]]
                for context in reversed(contexts):
                    context.close()
                browser.close()
    except Exception as exc:
        # Browser/server diagnostics can contain URLs or application data. Keep them out of artifacts.
        report["passed"] = False
        report["checks"].append({"name": stage, "passed": False,
                                 "detail": "Browser check failed; inspect the named workflow step locally.",
                                 "error_type": type(exc).__name__})
        frames = [frame for frame in traceback.extract_tb(exc.__traceback__)
                  if Path(frame.filename).resolve() == Path(__file__).resolve()]
        if frames:
            report["checks"][-1]["failure_line"] = frames[-1].lineno
    report["seconds"] = round(time.monotonic() - started, 3)
    return report
