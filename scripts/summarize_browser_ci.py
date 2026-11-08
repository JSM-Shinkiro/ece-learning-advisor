"""Summarize browser acceptance and offline timing reports without raw user/error text."""

import argparse
from collections import Counter
import json
import math
import os
from pathlib import Path
import re
import sys


REPORTS = (
    ("Student app browser flow", "browser.json", "checks"),
    ("Reviewer workspace", "reviewer-browser.json", "checks"),
    ("Controlled AI and browsing", "progressive-browser.json", "checks"),
    ("Current app preview timing", "browser-performance.json", "timing"),
    ("Fixed baseline preview timing", "baseline-browser-performance.json", "timing"),
)
STAGES = {
    "browser_startup": "Browser startup", "session_startup": "Session startup",
    "navigation": "Page loading", "roadmap": "Roadmap",
    "inspector": "Inspector first opening", "inspector_reopen": "Inspector reopening",
    "trace_validation": "Trace validation", "server_startup_or_cleanup": "Server startup or cleanup",
}


def failure_stages(report):
    """Only fixed stage names and counts; never exception messages or class names."""
    failures = [report.get("failure")]
    samples = report.get("samples", [])
    if isinstance(samples, list):
        failures.extend(row.get("failure") for row in samples if isinstance(row, dict))
    counts = Counter(STAGES.get(failure.get("stage"), "Other stage")
                     for failure in failures if isinstance(failure, dict))
    return ", ".join(f"{name} ({count})" for name, count in sorted(counts.items()))


def report_status(report, kind):
    """Derive status from actual rows; a top-level success cannot hide bad/missing rows."""
    if not isinstance(report, dict) or type(report.get("passed")) is not bool:
        return "INVALID", "Report format is invalid"
    if kind == "checks":
        rows = report.get("checks")
        if not isinstance(rows, list) or not rows or any(
                not isinstance(row, dict) or type(row.get("passed")) is not bool for row in rows):
            return "INVALID", "Check rows are missing or invalid"
        count = sum(row["passed"] for row in rows)
        if report["passed"] and count != len(rows):
            return "INVALID", "Success flag disagrees with check results"
        passed = report["passed"] and count == len(rows) and not report.get("failure")
        return ("PASS" if passed else "FAIL"), f"{count}/{len(rows)} checks passed"

    requested, count, rows = (report.get(key) for key in ("requested_samples", "successful_samples", "samples"))
    if (type(requested) is not int or not 2 <= requested <= 20 or type(count) is not int
            or not isinstance(rows, list) or len(rows) > requested or any(
                not isinstance(row, dict) or type(row.get("passed")) is not bool for row in rows)):
        return "INVALID", "Timing rows are missing or invalid"
    if count != sum(row["passed"] for row in rows):
        return "INVALID", "Sample count disagrees with sample results"
    if report["passed"] and (count != requested or len(rows) != requested or report.get("failure")):
        return "INVALID", "Success flag disagrees with timing results"
    passed = report["passed"] and count == requested
    detail = f"{count}/{requested} sessions complete"
    if passed:
        if report.get("version") != "p07-browser-performance-v2":
            return "INVALID", "Timing boundary version is unsupported"
        for metric, label in (("inspector_first_ready_ms", "first inspector"),
                              ("inspector_reopen_ready_ms", "reopening")):
            values = report.get("summary_ms", {}).get(metric, {})
            number = values.get("median")
            if (type(values.get("n")) is not int or values["n"] != count
                    or isinstance(number, bool) or not isinstance(number, (int, float))
                    or not math.isfinite(number) or number < 0):
                return "INVALID", "Timing summary is incomplete or invalid"
            detail += f"; {label} {number:.1f} ms median"
    else:
        stages = failure_stages(report)
        if stages:
            detail += "; failed stage: " + stages
    return ("PASS" if passed else "FAIL"), detail


def build_summary(directory, *, revision="", run_id=""):
    lines = ["## Browser checks", ""]
    if re.fullmatch(r"[a-f0-9]{40}", revision):
        lines += [f"Commit: [{revision[:7]}](https://github.com/JSM-Shinkiro/ece-learning-advisor/commit/{revision})", ""]
    if re.fullmatch(r"[1-9][0-9]{0,19}", run_id):
        lines += [f"[This workflow run](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/{run_id})", ""]
    lines += ["| Check | Status | Result |", "| --- | --- | --- |"]
    complete = True
    for label, filename, kind in REPORTS:
        try:
            report = json.loads((Path(directory) / filename).read_text(encoding="utf-8"))
            status, detail = report_status(report, kind)
        except FileNotFoundError:
            status, detail = "MISSING", "No report produced; check the preceding step"
        except (OSError, UnicodeError, ValueError, TypeError, AttributeError):
            status, detail = "INVALID", "The saved report could not be validated"
        complete = complete and status == "PASS"
        lines.append(f"| {label} | **{status}** | {detail} |")
    lines += ["", "Preview timings are offline. Controlled AI/employer checks use fixtures. "
              "These checks do not supply live-AI measurements or independent reviewer grades.", "",
              "Earlier failed runs retain their original results. Check the commit and conclusion of the current run.", ""]
    return "\n".join(lines), complete


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New Markdown summary path")
    parser.add_argument("--github-summary", action="store_true", help="Also append to GITHUB_STEP_SUMMARY")
    args = parser.parse_args()
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as handle:
            markdown, passed = build_summary(args.reports_dir, revision=os.environ.get("GITHUB_SHA", ""),
                                              run_id=os.environ.get("GITHUB_RUN_ID", ""))
            handle.write(markdown)
        if args.github_summary:
            target = os.environ.get("GITHUB_STEP_SUMMARY")
            if not target:
                raise OSError("No summary destination")
            with Path(target).open("a", encoding="utf-8") as handle:
                handle.write(markdown)
    except FileExistsError:
        print("Choose a new summary path; existing reports are never replaced.", file=sys.stderr)
        return 1
    except OSError:
        print("The CI summary could not be saved or attached.", file=sys.stderr)
        return 1
    print(markdown)
    if not passed:
        print("::error title=Browser reports incomplete::See the Browser checks summary for the failed, missing or invalid report.")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
