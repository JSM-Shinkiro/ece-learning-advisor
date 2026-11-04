"""One explicit, on-demand job search provider."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

MAX_JOB_BYTES = 3_000_000


@dataclass
class JobSearchResult:
    listings: list[dict]
    retrieved_at: str
    query: str
    location: str
    provider: str = "adzuna"
    checks: list[dict] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    total_matches: int | None = None
    cache_state: str = "fresh"


def search_jobs(app_id: str, app_key: str, career: str, location: str,
                internship=False, opener=urlopen) -> JobSearchResult:
    if not app_id or not app_key:
        raise ValueError("The job provider is not configured")
    terms = {"ai_ml": "machine learning", "embedded": "embedded software", "exploring": "engineering"}
    if career not in terms or not isinstance(location, str) or len(location) > 120 or any(ord(c) < 32 for c in location) or type(internship) is not bool:
        raise ValueError("Invalid opportunity search filters")
    query = terms[career] + (" intern" if internship else "")
    params = {
        "app_id": app_id, "app_key": app_key, "what": query,
        "where": location, "results_per_page": 10, "sort_by": "date",
        "content-type": "application/json",
    }
    request = Request(
        "https://api.adzuna.com/v1/api/jobs/us/search/1?" + urlencode(params),
        headers={"Accept": "application/json", "User-Agent": "ECE-P07-Advisor/0.1"},
    )
    try:
        with opener(request, timeout=20) as response:
            body = response.read(MAX_JOB_BYTES + 1)
            if len(body) > MAX_JOB_BYTES:
                raise ValueError("Job response exceeds the download limit")
            payload = json.loads(body)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise RuntimeError("The job provider could not complete this search.") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list) or len(payload["results"]) > 1000:
        raise RuntimeError("The job provider returned an invalid response.")
    listings, seen = [], set()
    for item in payload["results"]:
        if not isinstance(item, dict):
            continue
        identity = str(item.get("id") or item.get("redirect_url", ""))
        url = str(item.get("redirect_url", ""))
        if not identity or identity in seen or not url.startswith("https://"):
            continue
        company = item.get("company")
        location_data = item.get("location")
        if not isinstance(company, dict) or not isinstance(location_data, dict):
            continue
        seen.add(identity)
        listings.append({
            "id": identity, "title": str(item.get("title", "")),
            "employer": str(company.get("display_name", "")),
            "location": str(location_data.get("display_name", "")),
            "url": url, "posted_at": item.get("created"),
            "description_snippet": str(item.get("description", "")),
        })
    return JobSearchResult(listings[:10], datetime.now(timezone.utc).isoformat(), query, location)
