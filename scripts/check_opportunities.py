"""Check configured public employer boards without credentials or model calls."""

import argparse
import hashlib
import json
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.catalog import ROOT
from src.opportunities import search_employer_jobs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--career", choices=["ai_ml", "embedded"], default="ai_ml")
    parser.add_argument("--location", default="")
    roles = parser.add_mutually_exclusive_group()
    roles.add_argument("--internship", action="store_true")
    roles.add_argument("--early-career", action="store_true")
    parser.add_argument("--updated-within", type=int, choices=[7, 30, 90])
    parser.add_argument("--output", type=Path, default=ROOT / ".cache/opportunity_checks.json")
    args = parser.parse_args()
    paths = ["src/opportunities.py", "src/jobs.py", "data/connectors/employer_boards.json"]
    report = {"scope": "Configured public employer boards and literal title/location filters; not an eligibility decision.",
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "model_calls": 0, "credentials_used": False,
        "filters": {"career": args.career, "location": args.location, "internship": args.internship,
                    "early_career": args.early_career,
                    "updated_within": args.updated_within},
        "implementation": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}}
    started = time.perf_counter()
    try:
        result = search_employer_jobs(args.career, args.location, args.internship, updated_within=args.updated_within,
            early_career=args.early_career)
        report["result"] = asdict(result)
        report["passed"] = not result.issues and all(c["status"] == "verified" for c in result.checks)
        print("Listings:", len(result.listings), "Matching posts:", result.total_matches)
        for check in result.checks:
            print(check["employer"], check["status"], "valid posts:", check["valid_posts"])
    except (ValueError, RuntimeError) as exc:
        report.update(passed=False, error_type=type(exc).__name__, error="The employer search could not complete.")
        report["checks"] = getattr(exc, "checks", [])
        print("The employer search could not complete.")
    report["seconds"] = time.perf_counter() - started
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Saved", args.output)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
