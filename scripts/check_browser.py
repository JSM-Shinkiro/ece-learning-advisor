"""Run real-browser preview workflows locally, or against an explicitly supplied app URL."""

import argparse
from contextlib import nullcontext
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New JSON report path; existing files are never replaced")
    parser.add_argument("--url", help="Optional running app URL; default starts an isolated offline production server")
    parser.add_argument("--executable-path", help="Optional system Chromium executable; default uses Playwright's installed browser")
    args = parser.parse_args()
    try:
        from src.browser_checks import browser_url, local_browser_server, run_browser_checks
        url = browser_url(args.url) if args.url else None
    except (ImportError, ValueError):
        print("Install requirements-browser.txt and use a plain http(s) app URL without credentials, query, or fragment.", file=sys.stderr)
        return 1
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # Reserve before any server/browser work; a failure report is still written to this file.
        with args.output.open("x", encoding="utf-8") as handle:
            try:
                with (nullcontext(url) if url else local_browser_server()) as target:
                    report = run_browser_checks(target, local=url is None, executable_path=args.executable_path,
                                                diagnostics_dir=args.output.parent if url is None else None)
            except Exception as exc:
                report = {"passed": False, "checks": [{"name": "server_startup", "passed": False,
                          "detail": "The production server could not start or stop cleanly.", "error_type": type(exc).__name__}]}
            report["checked_at"] = datetime.now(timezone.utc).isoformat()
            handle.write(json.dumps(report, indent=2) + "\n")
    except FileExistsError:
        print("The report already exists. Choose a new --output path.", file=sys.stderr)
        return 1
    except OSError:
        print("The browser report could not be saved. Choose a writable new --output path.", file=sys.stderr)
        return 1
    for check in report["checks"]:
        print(check["name"], "passed" if check["passed"] else "failed", "·", check["detail"])
        if not check["passed"]:
            print("Failure type:", check.get("error_type", "unknown"), "· checker line:", check.get("failure_line", "n/a"))
    print("Saved", args.output)
    if "local_ui_diagnostics" in report:
        print("Local fixture diagnostics:", json.dumps(report["local_ui_diagnostics"]))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
