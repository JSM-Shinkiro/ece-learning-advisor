"""Exercise official-source checks without embedding or generation calls."""

import argparse
from collections import Counter
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.career_paths import CAREER_NAMES
from src.catalog import ROOT, load_catalog, load_runtime_catalog
from src.controller import run_advisor
from src.models import StudentProfile
from src.source_reuse import VERIFIED_CHECKS


def summarize_checks(checks):
    attempted = [check for check in checks if check["status"] != "skipped"]
    rules = Counter(check["rule_status"] for check in attempted if check.get("rule_status"))
    discovery = Counter(check["discovery_status"] for check in attempted if check.get("discovery_status"))
    failed_sources = sum(check["status"] not in VERIFIED_CHECKS for check in attempted)
    return {
        "attempted": len(attempted),
        "skipped": len(checks) - len(attempted),
        "failed_sources": failed_sources,
        "rules": dict(rules),
        "discovery": dict(discovery),
        "passed": bool(attempted) and failed_sources == 0
                  and set(rules) <= {"verified"} and set(discovery) <= {"verified"},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--career", choices=CAREER_NAMES, default="ai_ml")
    parser.add_argument("--catalog-year", default="2026-2027")
    parser.add_argument("--collection", choices=["baseline", "runtime"], default="baseline",
                        help="Baseline preserves historical checks; runtime checks the expanded app collection")
    parser.add_argument("--question", default="", help="Optional course question for discovery-priority checks (up to 1200 characters)")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / ".cache" / "sources")
    parser.add_argument("--output", type=Path, default=ROOT / ".cache" / "source_check_trace.json")
    args = parser.parse_args()
    if len(args.question) > 1200:
        parser.error("Keep the question within 1200 characters")
    catalog = load_runtime_catalog() if args.collection == "runtime" else load_catalog()
    result = run_advisor(catalog, StudentProfile(career_id=args.career, catalog_version=args.catalog_year, question=args.question),
                         refresh_sources=True, source_cache_dir=args.cache_dir)
    checks = result.trace["source_refresh"].get("checks", [])
    summary = summarize_checks(checks)
    result.trace["source_refresh"]["summary"] = summary
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result.trace, indent=2), encoding="utf-8")
    for check in checks:
        print(check.get("kind", "course"), check["code"], check["status"],
              "rule status:", check.get("rule_status") or "not applicable",
              "discovery:", check.get("discovery_status") or "not applicable",
              "attempts:", len(check.get("attempts", [])), "retries:", check.get("retry_count", 0),
              "last checked:", check["last_checked_at"] or "not verified")
    for request in result.trace["source_refresh"].get("discovery_selection", {}).get("requests", []):
        print("requested course:", request["code"], request["status"])
    for issue in result.issues:
        print(issue)
    print("Attempted", summary["attempted"], "· skipped", summary["skipped"], "· failed sources", summary["failed_sources"])
    print("Prerequisite verification", summary["rules"], "· course discovery", summary["discovery"])
    print("Source-check trace:", args.output)
    print("No embedding or generation requests were made.")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
