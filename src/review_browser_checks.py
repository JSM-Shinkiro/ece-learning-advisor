"""Controlled browser tests for the local reviewer; fixture ratings are not human judgments."""

import json
from pathlib import Path
import tempfile
import time
import traceback
from urllib.parse import urlsplit


def run_review_browser_checks(url, *, executable_path=None, timeout_ms=20000):
    report = {"passed": False, "mode": "controlled_reviewer_fixture", "checks": [],
              "browser": None, "sessions": [], "blocked_external_browser_requests": 0,
              "limits": ["Only controlled fixture actions; no independent judgments or quality score.",
                         "No supplied-host, participant, or public hosting validation."]}
    stage, started = "reviewer_startup", time.monotonic()
    try:
        from playwright.sync_api import expect, sync_playwright
        from google.protobuf.message import DecodeError
        from streamlit.proto.ForwardMsg_pb2 import ForwardMsg
        from .browser_checks import browser_url
        url = browser_url(url)
        origin = urlsplit(url)
        with tempfile.TemporaryDirectory(prefix="ece-review-controls-") as temporary, sync_playwright() as driver:
            browser = driver.chromium.launch(executable_path=executable_path)
            contexts, states = [], {}
            report["browser"] = {"engine": "chromium", "version": browser.version}
            try:
                def settled(page, after=0):
                    deadline = time.monotonic() + timeout_ms / 1000
                    while states[page]["scripts_finished"] <= after and time.monotonic() < deadline:
                        page.wait_for_timeout(50)
                    assert states[page]["scripts_finished"] > after

                def act(page, action):
                    before = states[page]["scripts_finished"]
                    action()
                    settled(page, before)

                def open_session():
                    context = browser.new_context(accept_downloads=True, viewport={"width": 1500, "height": 1100})
                    contexts.append(context)
                    def route_request(route):
                        parsed = urlsplit(route.request.url)
                        if (parsed.scheme, parsed.netloc) == (origin.scheme, origin.netloc): route.continue_()
                        else:
                            report["blocked_external_browser_requests"] += 1
                            route.abort()
                    context.route("**/*", route_request)
                    page = context.new_page()
                    state = {"scripts_finished": 0, "page_errors": 0}
                    states[page] = state
                    report["sessions"].append(state)
                    page.set_default_timeout(timeout_ms)
                    page.set_default_navigation_timeout(timeout_ms)
                    def received(payload):
                        if not isinstance(payload, bytes): return
                        message = ForwardMsg()
                        try: message.ParseFromString(payload)
                        except DecodeError: return
                        if message.WhichOneof("type") == "script_finished" and message.script_finished == 0:
                            state["scripts_finished"] += 1
                    page.on("websocket", lambda stream: stream.on("framereceived", received)
                            if urlsplit(stream.url).path == origin.path + "_stcore/stream" else None)
                    def page_error(_): state["page_errors"] += 1
                    page.on("pageerror", page_error)
                    page.goto(url, wait_until="domcontentloaded")
                    settled(page)
                    expect(page.get_by_role("heading", name="Evidence review", exact=True)).to_be_visible()
                    return page

                def saved(page, count):
                    expect(page.get_by_text(f"Saved ratings: {count} of 408", exact=True)).to_be_visible()

                def save(page, label=None):
                    if label is not None:
                        page.get_by_role("radio", name=label, exact=True).check()
                    button = page.get_by_role("button", name="Save grade and next", exact=True)
                    button.focus()
                    act(page, button.click)

                def download(page, name):
                    with page.expect_download() as pending:
                        page.get_by_role("button", name="Download review draft", exact=True).click()
                    path = Path(temporary) / name
                    pending.value.save_as(path)
                    return path, json.loads(path.read_text(encoding="utf-8"))

                def passed(name, detail):
                    report["checks"].append({"name": name, "passed": True, "detail": detail})

                stage = "blank_review"
                a = open_session()
                saved(a, 0)
                assert not a.get_by_role("radio").evaluate_all("nodes => nodes.some(node => node.checked)")
                passed(stage, "All 408 ratings start blank, with no chosen grade or reviewer role.")

                stage = "explicit_grades"
                save(a)
                saved(a, 0)
                expect(a.get_by_text("Choose a relevance grade before saving.", exact=True)).to_be_visible()
                a.get_by_role("textbox", name="Question note (optional)", exact=True).fill("Controlled fixture note")
                save(a, "0 · Unrelated")
                saved(a, 1)
                save(a, "3 · Direct evidence")
                saved(a, 2)
                passed(stage, "Blank saves do not grade; explicit zero and three save separate evidence judgments.")

                stage = "draft_download"
                alias = a.get_by_role("textbox", name="Reviewer alias", exact=True)
                def set_alias():
                    alias.fill("browser_fixture")
                    alias.press("Enter")
                act(a, set_alias)
                act(a, lambda: a.get_by_role("radio", name="Controlled fixture (testing only)", exact=True).check())
                draft_path, draft = download(a, "draft.json")
                grades = [grade for case in draft["cases"] for grade in case["relevance"].values() if grade is not None]
                assert sorted(grades) == [0, 3] and draft["reviewed_at"] is None
                assert draft["reviewer_role"] == "controlled_fixture"
                assert draft["cases"][0]["note"] == "Controlled fixture note"
                passed(stage, "A real download retains two explicit fixture ratings, notes schema, and draft provenance.")

                stage = "incomplete_completion_blocked"
                act(a, lambda: a.get_by_role("button", name="Prepare completed review", exact=True).click())
                expect(a.get_by_role("button", name="Download completed review", exact=True)).to_have_count(0)
                expect(a.get_by_text("Complete all ratings and choose a valid reviewer alias and role before finalizing.", exact=True)).to_be_visible()
                passed(stage, "An incomplete draft cannot be exported as a completed review.")

                stage = "resume_and_isolation"
                b = open_session()
                saved(b, 0)
                act(b, lambda: b.get_by_test_id("stFileUploaderDropzoneInput").set_input_files(draft_path))
                saved(b, 2)
                expect(b.get_by_role("textbox", name="Reviewer alias", exact=True)).to_have_value("browser_fixture")
                _, resumed = download(b, "resumed.json")
                assert resumed == draft
                saved(a, 2)
                passed(stage, "A separate session starts blank and restores the downloaded draft exactly.")

                stage = "wrong_packet_rejected"
                wrong = {**draft, "packet_hash": "0" * 64}
                wrong_path = Path(temporary) / "wrong-packet.json"
                wrong_path.write_text(json.dumps(wrong), encoding="utf-8")
                act(b, lambda: b.get_by_test_id("stFileUploaderDropzoneInput").set_input_files(wrong_path))
                expect(b.get_by_text("The draft could not be restored. Check its format and packet identity. Your saved ratings are unchanged.", exact=True)).to_be_visible()
                saved(b, 2)
                _, unchanged = download(b, "unchanged.json")
                assert unchanged == draft
                assert all(state["page_errors"] == 0 for state in report["sessions"])
                passed(stage, "A foreign packet hash is rejected without replacing saved ratings or producing page errors.")
                report["passed"] = True
            finally:
                report["sessions"] = [dict(state) for state in report["sessions"]]
                try:
                    for context in reversed(contexts): context.close()
                finally:
                    browser.close()
    except Exception as error:
        item = {"name": stage, "passed": False, "detail": "Reviewer browser check failed.", "error_type": type(error).__name__}
        frames = [frame for frame in traceback.extract_tb(error.__traceback__)
                  if Path(frame.filename).resolve() == Path(__file__).resolve()]
        if frames: item["failure_line"] = frames[-1].lineno
        report["checks"].append(item)
    report["seconds"] = round(time.monotonic() - started, 3)
    return report
