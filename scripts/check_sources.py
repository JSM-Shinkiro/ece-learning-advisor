"""Exercise official-source checks without embedding or generation calls."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.catalog import ROOT, load_catalog, load_runtime_catalog
from src.controller import run_advisor
from src.models import StudentProfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--career", choices=["ai_ml", "embedded", "exploring"], default="ai_ml")
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
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result.trace, indent=2), encoding="utf-8")
    checks = result.trace["source_refresh"].get("checks", [])
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
    print("Source-check trace:", args.output)
    print("No embedding or generation requests were made.")
    return 0 if checks and all(c["status"] in {"updated", "unchanged", "not_modified"}
                              and c.get("rule_status") in {None, "verified"}
                              and c.get("discovery_status") in {None, "verified"} for c in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
