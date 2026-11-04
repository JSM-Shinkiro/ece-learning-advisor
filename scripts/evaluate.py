"""Offline retrieval smoke evaluation. Does not call or simulate an LLM."""

import argparse
import json
import sys
import time
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.catalog import load_catalog
from src.models import Completion, StudentProfile
from src.service import recommend


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.runs < 1:
        raise SystemExit("--runs must be positive")
    catalog = load_catalog()
    cases = [
        ("ai_beginner", StudentProfile(career_id="ai_ml"), "uofa:ECE101:2026-2027"),
        ("embedded_beginner", StudentProfile(career_id="embedded"), "uofa:ECE101:2026-2027"),
        ("ai_experienced", StudentProfile(career_id="ai_ml",programming_background="experienced"), "uofa:ECE425:2026-2027"),
        ("embedded_experienced", StudentProfile(career_id="embedded",programming_background="experienced"), "uofa:ECE372A:2026-2027"),
        ("embedded_completed", StudentProfile(career_id="embedded",completed=[Completion(course_code="ECE372A")]), None),
    ]
    output = {"mode":"keyword-only, no model calls", "cases":[], "data_version":catalog.version}
    for name, profile, expected in cases:
        times, result = [], None
        for _ in range(args.runs):
            result = recommend(catalog, profile)
            times.append(result.timings["total"])
        courses = [r for r in result.context.allowed_record_ids if r.startswith("uofa:")]
        output["cases"].append({
            "case":name,"course_ids":courses,"expected_first":expected,
            "expected_first_passed":bool(courses) and courses[0]==expected if expected else "uofa:ECE372A:2026-2027" not in courses,
            "runs":len(times),"median_seconds":median(times),"min_seconds":min(times),"max_seconds":max(times),
        })
    rendered = json.dumps(output,indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(rendered,encoding="utf-8")


if __name__ == "__main__":
    main()
