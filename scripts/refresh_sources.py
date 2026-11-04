"""Create a staging review report. Never overwrite approved academic rules."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.catalog import ROOT, load_catalog
from src.ingest import extract_course


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT/"data/staging/source_review.json")
    args = parser.parse_args()
    catalog = load_catalog()
    report = []
    for source in catalog.sources:
        if not source.source_id.startswith("catalog:"):
            continue
        if not urlparse(source.url).path.startswith("/courses/"):
            continue  # Program guidance is reviewed separately from the course-page extractor.
        if urlparse(source.url).hostname != "catalog.arizona.edu":
            raise ValueError("Only official catalog URLs are accepted")
        request = Request(source.url, headers={"User-Agent":"ECE-P07-Advisor/0.1"})
        with urlopen(request, timeout=25) as response:
            page = response.read().decode("utf-8")
        candidate = extract_course(page)
        candidate.update(source_id=source.source_id, url=source.url,
                         retrieved_at=datetime.now(timezone.utc).isoformat())
        report.append(candidate)
        print(candidate["code"], candidate["title"], candidate["credits"],
              "requirement reference:", candidate["requirement_reference"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Review candidates saved to", args.output)
    print("Approved catalog data was not modified.")


if __name__ == "__main__":
    main()
