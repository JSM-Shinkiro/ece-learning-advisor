"""Repeated offline production-browser timings; never a live-AI benchmark."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import platform
import re
import statistics
import subprocess
import tempfile
import time
from urllib.parse import urlsplit

from .browser_checks import browser_url
from .catalog import ROOT
from .progress import PHASE_LABELS


METRICS = ("navigation_to_interactive_ms", "request_feedback_dom_ms",
           "roadmap_controls_ready_ms", "submit_to_script_finished_ms", "inspector_plot_ready_ms")
SERVER_TIMINGS = ("source_refresh", "embedding", "retrieval", "rules", "generation", "total")


def duration(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError("Expected a finite nonnegative duration")
    return float(value)


def preview_metadata(trace):
    """Whitelist numeric/provenance fields, rejecting a different experiment scope."""
    if (trace.get("generation_complete") is not False or trace.get("generation_status") != "not_requested"
            or trace.get("embedding_model") is not None or trace.get("generation_model") is not None
            or trace.get("retrieval_mode") != "keyword" or trace.get("cache_state") != "not_used"
            or trace.get("source_refresh", {}).get("enabled") is not False):
        raise ValueError("This measurement requires offline keyword preview")
    version, fingerprint = trace.get("data_version"), trace.get("corpus_hash")
    if (not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9_.+-]{1,100}", version)
            or not isinstance(fingerprint, str) or not re.fullmatch(r"[a-f0-9]{64}", fingerprint)):
        raise ValueError("Missing collection provenance")
    timings = trace.get("timings_seconds", {})
    if "total" not in timings:
        raise ValueError("Missing server timing")
    return {"data_version": version, "corpus_hash": fingerprint,
            "retrieval_mode": "keyword", "cache_state": "not_used", "source_refresh_enabled": False,
            "embedding_model": None, "generation_model": None, "generation_status": "not_requested",
            "timings_seconds": {key: duration(timings[key]) for key in SERVER_TIMINGS if key in timings}}


def summarize(samples):
    """Keep failures in the report; never silently count partial samples as successes."""
    successful = [sample for sample in samples if sample.get("passed") is True]
    summary = {}
    for metric in METRICS:
        values = [duration(sample["metrics_ms"][metric]) for sample in successful]
        if values:
            summary[metric] = {"n": len(values), "min": round(min(values), 3),
                               "median": round(statistics.median(values), 3), "max": round(max(values), 3)}
    return summary


def measurement_environment(root=ROOT):
    """Record the actual checkout and machine without identity or environment secrets."""
    result = {"os": platform.system(), "os_release": platform.release(),
              "machine": platform.machine(), "python": platform.python_version(), "logical_cpus": os.cpu_count(),
              "revision": None, "working_tree_dirty": None}
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                                  text=True, check=True, timeout=5).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True,
                               text=True, check=True, timeout=5).stdout.strip()
        if re.fullmatch(r"[a-f0-9]{40}", revision):
            result.update(revision=revision, working_tree_dirty=bool(dirty))
    except (OSError, subprocess.SubprocessError):
        pass
    return result


# Times use the page's single monotonic clock. Observation runs on animation frames;
# this measures laid-out DOM availability, not GPU paint, FCP, LCP or field INP.
OBSERVER = r"""labels => {
    const visible = element => element && element.getClientRects().length > 0
        && getComputedStyle(element).visibility !== 'hidden';
    const state = {clicks: 0, submit: null, feedback: null, plan: null,
                   feedback_kind: null, inspector_click: null, inspector_ready: null};
    window.__eceTiming = state;
    let scheduled = false;
    const observe = () => {
        scheduled = false;
        const now = performance.now();
        if (state.submit !== null) {
            const summaries = [...document.querySelectorAll('details > summary')].filter(visible);
            if (state.feedback === null) {
                const status = summaries.find(el => labels.some(label => el.textContent.includes(label)));
                if (status) {
                    state.feedback = now;
                    state.feedback_kind = status.textContent.includes('Learning plan ready') ? 'complete' : 'progress';
                }
            }
            if (state.plan === null && [...document.querySelectorAll('button')].some(
                el => el.textContent.trim() === 'Mark completed' && !el.disabled && visible(el))) state.plan = now;
        }
        if (state.inspector_click !== null && state.inspector_ready === null) {
            const plot = document.querySelector('[data-testid="stPlotlyChart"] .js-plotly-plot');
            if (visible(plot) && plot.data?.length) state.inspector_ready = now;
        }
    };
    const schedule = () => { if (!scheduled) { scheduled = true; requestAnimationFrame(observe); } };
    new MutationObserver(schedule).observe(document.documentElement,
        {childList: true, subtree: true, attributes: true, characterData: true});
    document.addEventListener('click', event => {
        const button = event.target.closest('button');
        if (button?.textContent.trim() === 'Update my roadmap') {
            state.clicks++; state.submit = performance.now();
        }
        const summary = event.target.closest('summary');
        if (summary?.textContent.includes('How this plan was made')) state.inspector_click = performance.now();
        schedule();
    }, true);
}"""


def run_browser_measurements(url, *, samples=5, executable_path=None, timeout_ms=30000):
    """One browser/server, fresh session per sample; failures remain explicit rows."""
    if type(samples) is not int or not 2 <= samples <= 20:
        raise ValueError("Choose 2–20 sessions")
    target = browser_url(url)
    origin = urlsplit(target)
    if origin.scheme != "http" or origin.hostname != "127.0.0.1":
        raise ValueError("Only the isolated loopback experiment is supported")
    report = {"version": "p07-browser-performance-v1", "passed": False, "requested_samples": samples,
              "mode": "local_offline_production_preview", "environment": measurement_environment(), "browser": None,
              "samples": [], "summary_ms": {},
              "method": {"viewport": {"width": 1500, "height": 1100}, "fresh_context_per_sample": True,
                         "shared_server_and_browser_process": True, "http_cache_disabled_by_request_routing": True,
                         "profile": "unchanged_default_incoming_ai_ml", "inspector_initially_closed": True,
                         "clock": "page performance.now for DOM; Python monotonic for driver/protocol intervals"},
              "limits": ["Offline preview only: no source downloads, embeddings or AI generation.",
                         "DOM timings observe layout availability, including offscreen controls, not physical paint or field INP.",
                         "Driver timings include automation/protocol overhead; clocks are never subtracted across processes.",
                         "Fresh contexts share processes; this is not a cold/warm-cache or hosted/mobile comparison.",
                         "Small-sample min/median/max only; no p95, latency pass threshold or user-quality inference."]}
    stage = "browser_startup"
    try:
        from playwright.sync_api import expect, sync_playwright
        from google.protobuf.message import DecodeError
        from streamlit.proto.ForwardMsg_pb2 import ForwardMsg

        with sync_playwright() as driver, tempfile.TemporaryDirectory(prefix="ece-timing-traces-") as temporary:
            browser = driver.chromium.launch(executable_path=executable_path)
            report["browser"] = {"engine": "chromium", "version": browser.version}
            cohort = None
            try:
                for ordinal in range(1, samples + 1):
                    row = {"ordinal": ordinal, "passed": False, "metrics_ms": {},
                           "external_browser_requests_blocked": 0, "page_errors": 0}
                    report["samples"].append(row)
                    context = None
                    try:
                        stage = "session_startup"
                        context = browser.new_context(accept_downloads=True, viewport=report["method"]["viewport"])
                        def route_request(route):
                            requested = urlsplit(route.request.url)
                            if (requested.scheme, requested.netloc) == (origin.scheme, origin.netloc):
                                route.continue_()
                            else:
                                row["external_browser_requests_blocked"] += 1
                                route.abort()
                        context.route("**/*", route_request)
                        page = context.new_page()
                        page.set_default_timeout(timeout_ms)
                        counts = {"full": 0, "fragment": 0, "streams": 0}
                        def websocket(stream):
                            if urlsplit(stream.url).path != origin.path + "_stcore/stream":
                                return
                            counts["streams"] += 1
                            def received(payload):
                                if not isinstance(payload, bytes):
                                    return
                                message = ForwardMsg()
                                try:
                                    message.ParseFromString(payload)
                                except DecodeError:
                                    return
                                if message.WhichOneof("type") == "script_finished":
                                    if message.script_finished == 0:
                                        counts["full"] += 1
                                    elif message.script_finished == 3:
                                        counts["fragment"] += 1
                            stream.on("framereceived", received)
                        page.on("websocket", websocket)
                        def page_error(_):
                            row["page_errors"] += 1
                        page.on("pageerror", page_error)
                        def settled(kind, after):
                            deadline = time.monotonic() + timeout_ms / 1000
                            while counts[kind] <= after and time.monotonic() < deadline:
                                page.wait_for_timeout(25)
                            if counts[kind] <= after:
                                raise TimeoutError("No successful script completion")

                        stage = "navigation"
                        start = time.monotonic()
                        page.goto(target, wait_until="domcontentloaded", timeout=timeout_ms)
                        button = page.get_by_role("button", name="Update my roadmap", exact=True)
                        expect(button).to_be_visible()
                        expect(button).to_be_enabled()
                        settled("full", 0)
                        row["metrics_ms"]["navigation_to_interactive_ms"] = duration((time.monotonic() - start) * 1000)
                        expect(page.get_by_role("button", name="Mark completed", exact=True)).to_have_count(0)
                        expect(page.get_by_test_id("stPlotlyChart")).to_have_count(0)
                        page.evaluate(OBSERVER, ["Updating your learning plan...", "Learning plan ready", *PHASE_LABELS.values()])
                        button.scroll_into_view_if_needed()
                        button.focus()
                        before = counts["full"]
                        stage = "roadmap"
                        start = time.monotonic()
                        button.click()
                        page.wait_for_function("window.__eceTiming.plan !== null && window.__eceTiming.feedback !== null")
                        settled("full", before)
                        row["metrics_ms"]["submit_to_script_finished_ms"] = duration((time.monotonic() - start) * 1000)
                        expect(page.get_by_text("Saved profile: Incoming · AI / Machine Learning · 0 completed courses · 0 currently taking",
                                                exact=True)).to_be_visible()
                        marks = page.evaluate("({clicks: __eceTiming.clicks, feedback: __eceTiming.feedback - __eceTiming.submit, "
                                              "plan: __eceTiming.plan - __eceTiming.submit, kind: __eceTiming.feedback_kind})")
                        if marks["clicks"] != 1:
                            raise ValueError("The sample must contain one submission")
                        row["metrics_ms"].update(request_feedback_dom_ms=duration(marks["feedback"]),
                                                 roadmap_controls_ready_ms=duration(marks["plan"]))
                        row["feedback_kind"] = marks["kind"]
                        expect(page.get_by_test_id("stPlotlyChart")).to_have_count(0)

                        stage = "inspector"
                        summary = page.locator("summary").filter(has=page.get_by_text("How this plan was made", exact=True))
                        summary.scroll_into_view_if_needed()
                        before = counts["fragment"]
                        summary.click()
                        page.wait_for_function("window.__eceTiming.inspector_ready !== null")
                        settled("fragment", before)
                        row["metrics_ms"]["inspector_plot_ready_ms"] = duration(page.evaluate(
                            "__eceTiming.inspector_ready - __eceTiming.inspector_click"))

                        stage = "trace_validation"
                        with page.expect_download() as pending:
                            page.get_by_role("button", name="Download request trace", exact=True).click()
                        path = Path(temporary) / f"trace-{ordinal}.json"
                        pending.value.save_as(path)
                        metadata = preview_metadata(json.loads(path.read_text(encoding="utf-8")))
                        path.unlink()
                        identity = metadata["data_version"], metadata["corpus_hash"]
                        if cohort is not None and cohort != identity:
                            raise ValueError("Collection changed between samples")
                        cohort = identity
                        row["trace"] = metadata
                        row["protocol"] = dict(counts)
                        if row["page_errors"] or row["external_browser_requests_blocked"] or counts["streams"] != 1:
                            raise ValueError("Unexpected browser error, external request or reconnection")
                        row["passed"] = True
                    except Exception as exc:
                        row["failure"] = {"stage": stage, "error_type": type(exc).__name__}
                    finally:
                        if context is not None:
                            context.close()
            finally:
                browser.close()
    except Exception as exc:
        report["failure"] = {"stage": stage, "error_type": type(exc).__name__}
    report["successful_samples"] = sum(sample["passed"] for sample in report["samples"])
    report["summary_ms"] = summarize(report["samples"])
    report["passed"] = (len(report["samples"]) == samples and report["successful_samples"] == samples
                        and "failure" not in report)
    return report
