"""Measure repeated fresh preview sessions using the isolated production launcher."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New JSON report; existing reports are never replaced")
    parser.add_argument("--samples", type=int, default=5, help="2–20 fresh browser sessions (default: 5)")
    parser.add_argument("--app-root", type=Path, default=ROOT, help="Local app checkout to measure; default is this repository")
    parser.add_argument("--executable-path", help="Optional system Chromium; default uses Playwright's installed browser")
    args = parser.parse_args()
    if not 2 <= args.samples <= 20:
        parser.error("--samples must be between 2 and 20")
    app_root = args.app_root.resolve()
    if not all((app_root / entry).is_file() for entry in ("app.py", "scripts/serve.py")):
        parser.error("--app-root must contain app.py and scripts/serve.py")
    from src.browser_checks import local_browser_server
    from src.browser_performance import run_browser_measurements
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as handle:
            try:
                with local_browser_server(root=app_root) as target:
                    report = run_browser_measurements(target, samples=args.samples, executable_path=args.executable_path,
                                                      app_root=app_root)
            except Exception as exc:
                report = {"passed": False, "requested_samples": args.samples, "successful_samples": 0,
                          "samples": [], "summary_ms": {},
                          "failure": {"stage": "server_startup_or_cleanup", "error_type": type(exc).__name__}}
            report["checked_at"] = datetime.now(timezone.utc).isoformat()
            handle.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    except FileExistsError:
        print("The report already exists. Choose a new --output path.", file=sys.stderr)
        return 1
    except OSError:
        print("The measurement report could not be saved. Choose a writable new path.", file=sys.stderr)
        return 1
    print(f"Completed {report['successful_samples']}/{args.samples} preview sessions.")
    if not report["passed"]:
        from scripts.summarize_browser_ci import failure_stages
        stages = failure_stages(report)
        if stages:
            print("Failed stage:", stages)
    for metric, values in report["summary_ms"].items():
        print(metric, "·", json.dumps(values))
    print("Saved", args.output)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
