"""Opt-in real provider checks. Requires local credentials and may use provider quota."""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from src.catalog import ROOT, load_catalog
from src.jobs import search_jobs
from src.models import StudentProfile
from src.providers import GeminiProvider
from src.service import recommend


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--career", choices=["ai_ml", "embedded"], default="ai_ml")
    parser.add_argument("--jobs", action="store_true", help="Also request real Adzuna listings")
    parser.add_argument("--output", type=Path, default=ROOT/"output/live_verification.json")
    args = parser.parse_args()
    load_dotenv(ROOT/".env")
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise SystemExit("Set GEMINI_API_KEY locally first. No model requests were made.")
    provider = GeminiProvider(key, embedding_model=os.getenv("EMBEDDING_MODEL", "gemini-embedding-2"),
        generation_model=os.getenv("GENERATION_MODEL", "gemini-3.5-flash-lite"),
        dimensions=int(os.getenv("EMBEDDING_DIMENSION", "768")))
    catalog, checks = load_catalog(), []
    profile = StudentProfile(career_id=args.career, interests="AI and hardware integration")
    try:
        for mode in ["keyword", "semantic", "hybrid"]:
            result = recommend(catalog, profile, provider=provider, method=mode, cache_dir=ROOT/".cache/embeddings")
            checks.append({"requested_retrieval":mode, "trace":result.trace, "issues":result.issues,
                           "answer":result.answer.model_dump() if result.answer else None,
                           "live_request_passed":result.generation_complete and result.retrieval_mode==mode})
    finally:
        provider.close()
    output = {"checks":checks, "manual_source_review_required":True}
    if args.jobs:
        try:
            jobs = search_jobs(os.getenv("ADZUNA_APP_ID", ""),os.getenv("ADZUNA_APP_KEY", ""),args.career,"Tucson, AZ")
            output["jobs"] = {"retrieved_at":jobs.retrieved_at,"query":jobs.query,"listings":jobs.listings}
        except (ValueError, RuntimeError):
            output["jobs"] = {"error":"The credentialed job check did not complete."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print("Saved live response evidence to",args.output)
    print("Inspect each answer against its cited sources. Reference checks do not establish factual support.")
    if not all(c["live_request_passed"] for c in checks) or (args.jobs and "error" in output["jobs"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
