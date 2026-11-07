"""Opt-in, bounded real-model checks for the saved runtime collection."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.catalog import load_runtime_catalog
from src.runtime_checks import verify_runtime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live-models", action="store_true", help="Allow configured Gemini requests and quota use")
    parser.add_argument("--with-sources", action="store_true", help="Add one bounded source-refresh scenario")
    parser.add_argument("--output", type=Path, required=True, help="New JSON report; existing files are never overwritten")
    args = parser.parse_args()
    if not args.live_models:
        parser.error("Runtime verification requires explicit --live-models opt-in.")
    try:
        if args.output.exists():
            raise ValueError("Choose a new report path")
        from dotenv import load_dotenv
        from src.settings import load_settings
        load_dotenv(ROOT / ".env")
        settings = load_settings()
        if not settings.ai_configured:
            raise ValueError("A provider credential is required")
        catalog = load_runtime_catalog()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # Reserve writable output before spending provider quota.
        with args.output.open("x", encoding="utf-8") as handle:
            report = verify_runtime(catalog, settings.gemini_key.get_secret_value(),
                embedding_model=settings.embedding_model, generation_model=settings.generation_model,
                dimensions=settings.embedding_dimensions, cache_dir=settings.cache_root / "embeddings",
                source_cache_dir=settings.cache_root / "sources", with_sources=args.with_sources,
                progress=lambda row: print(row["case_id"] + ": " + row["status"], flush=True))
            json.dump(report, handle, indent=2)
            handle.write("\n")
        print("Saved runtime integration checks. Independent quality review remains separate.")
        return 0 if report["all_checks_passed"] else 1
    except (OSError, ValueError, TypeError, RuntimeError):
        print("Runtime verification could not start or save its report. Check configuration, credentials, and a new writable output path.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
