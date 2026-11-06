"""Bounded public employer-board listings, independent of the language model."""

from __future__ import annotations

import html
import hashlib
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qs, urlparse

import httpx
from pydantic import Field, model_validator

from .ingest import description_text
from .jobs import JobSearchResult, MAX_SNAPSHOT_MATCHES, OPPORTUNITY_PAGE_SIZE
from .models import StrictModel

DEFAULT_BOARDS = Path(__file__).resolve().parents[1] / "data/connectors/employer_boards.json"
MAX_BOARDS, MAX_POSTS, MAX_RESULTS = 3, 4000, OPPORTUNITY_PAGE_SIZE
MAX_JSON_BYTES = 3_000_000
TIMEOUT = httpx.Timeout(6.0, connect=4.0, pool=4.0)
CACHE_SECONDS = 1200
OPPORTUNITY_POLICY_VERSION = "p07-opportunity-pages-v3"
CAREER_PATTERNS = {
    "ai_ml": r"\b(?:machine[ -]learning|deep[ -]learning|artificial intelligence|computer vision|perception|ML|AI|autonomy|autonomous)\b",
    "embedded": r"\b(?:embedded|firmware|microcontrollers?|FPGA|ASIC|RTL|hardware|electrical|controls?)\b",
}
ROLE_PATTERN = r"\b(?:engineer(?:ing)?|developer|scientist|research(?:er)?|technician|intern(?:ship)?|co[ -]?op)\b"
EXCLUDED_ROLES = r"\b(?:recruit(?:er|ing|ment)|sales|marketing|talent|account|executive assistant)\b"
INTERN_PATTERN = r"\b(?:intern(?:ship)?|co[ -]?op)\b"
EARLY_PATTERN = r"\b(?:new[ -]+grad(?:uate)?s?|recent[ -]+grad(?:uate)?s?|university[ -]+grad(?:uate)?s?|entry[ -]+level|early[ -]+career|junior)\b"
SENIOR_PATTERN = r"\b(?:senior|sr|staff|principal|lead|manager|director|head|distinguished|executive)\b"


class OpportunityResponseError(ValueError):
    def __init__(self, status):
        super().__init__("Employer board returned an unsupported response")
        self.http_status = status


class OpportunitySearchError(RuntimeError):
    def __init__(self, checks):
        super().__init__("The employer boards could not complete this search.")
        self.checks = checks


def validate_filters(career, location, internship, updated_within, early_career=False):
    if not isinstance(career, str) or career not in CAREER_PATTERNS:
        raise ValueError("Choose AI/ML or Embedded Systems before searching")
    if not isinstance(location, str) or len(location) > 120 or any(ord(c) < 32 for c in location):
        raise ValueError("Keep the location filter within 120 characters")
    if (type(internship) is not bool or type(early_career) is not bool or internship and early_career or updated_within is not None
            and (type(updated_within) is not int or updated_within not in {7, 30, 90})):
        raise ValueError("Invalid opportunity filters")


def normalized_title(title):
    return re.sub(r"[\u2010-\u2015]", "-", title)


def early_career_title(title):
    text = normalized_title(title)
    return bool(re.search(EARLY_PATTERN, text, re.I) and not re.search(SENIOR_PATTERN, text, re.I)
                and not re.search(INTERN_PATTERN, text, re.I))


def safe_https(value):
    if not isinstance(value, str) or len(value) > 2048 or any(c.isspace() or ord(c) < 32 for c in value):
        raise ValueError("Invalid posting URL")
    p = urlparse(value)
    if (p.scheme != "https" or not p.hostname or p.username or p.password
            or p.port not in {None, 443} or p.fragment):
        raise ValueError("Invalid posting URL")
    return p


class EmployerBoard(StrictModel):
    token: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,59}$")
    employer: str = Field(min_length=1, max_length=100)
    careers_url: str
    job_base_url: str
    url_style: Literal["id_path", "id_query"]

    @model_validator(mode="after")
    def match_employer_host(self):
        careers, jobs = safe_https(self.careers_url), safe_https(self.job_base_url)
        hosted = jobs.hostname in {"boards.greenhouse.io", "job-boards.greenhouse.io"}
        matching = (jobs.path == "/" + self.token + "/jobs/" and self.url_style == "id_path") if hosted else (
            careers.hostname.removeprefix("www.") == jobs.hostname.removeprefix("www."))
        if (not matching or careers.query or jobs.query or not jobs.path.startswith("/")
                or self.url_style == "id_path" and not jobs.path.endswith("/")):
            raise ValueError("Employer-board URL binding is invalid")
        return self

    @property
    def endpoint(self):
        return "https://boards-api.greenhouse.io/v1/boards/" + self.token + "/jobs"


def load_employer_boards(path=DEFAULT_BOARDS):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_BOARDS:
        raise ValueError("Choose one to three configured employer boards")
    boards = [EmployerBoard.model_validate(item) for item in raw]
    if len({b.token for b in boards}) != len(boards):
        raise ValueError("Duplicate employer board")
    return boards


def board_scope_hash(boards):
    payload = {"policy": OPPORTUNITY_POLICY_VERSION, "boards": [b.model_dump(mode="json") for b in boards]}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def valid_posting_url(value, board, identity):
    p = safe_https(value)
    query = parse_qs(p.query, keep_blank_values=True)
    if (not set(query) <= {"gh_jid", "gh_src"}
            or "gh_jid" in query and query["gh_jid"] != [identity]):
        raise ValueError("Posting link does not match its job identity")
    if p.hostname in {"boards.greenhouse.io", "job-boards.greenhouse.io"}:
        if p.path != "/" + board.token + "/jobs/" + identity:
            raise ValueError("Posting link does not match its employer board")
    else:
        base = urlparse(board.job_base_url)
        expected_path = base.path + identity if board.url_style == "id_path" else base.path
        if (p.hostname != base.hostname or p.path != expected_path
                or board.url_style == "id_query" and query.get("gh_jid") != [identity]):
            raise ValueError("Posting link is outside the configured employer")
    return value


def timestamp(value, now):
    if not isinstance(value, str) or len(value) > 80:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed > now + timedelta(minutes=5):
            return None
        return parsed.astimezone(timezone.utc).isoformat()
    except ValueError:
        return None


def plain(value, limit):
    if not isinstance(value, str) or len(value) > limit * 4:
        raise ValueError("Invalid posting field")
    text = description_text(html.unescape(value)).strip()
    if not text or len(text) > limit:
        raise ValueError("Invalid posting field")
    return text


def normalize_post(item, board, now):
    if not isinstance(item, dict) or type(item.get("id")) is not int or not 0 < item["id"] < 10**16:
        raise ValueError("Invalid posting identity")
    # Prospect/talent-network posts do not identify an actual job.
    if item.get("internal_job_id") is None:
        return None
    if type(item["internal_job_id"]) is not int or item["internal_job_id"] <= 0:
        raise ValueError("Invalid internal job identity")
    if item.get("company_name") not in {None, board.employer}:
        raise ValueError("Posting employer does not match its board")
    identity = str(item["id"])
    location = item.get("location")
    if not isinstance(location, dict):
        raise ValueError("Invalid posting location")
    title, place = plain(item.get("title"), 300), plain(location.get("name"), 500)
    url = valid_posting_url(item.get("absolute_url"), board, identity)
    return {"id": "greenhouse:" + board.token + ":" + identity, "title": title, "employer": board.employer,
        "location": place, "url": url, "posted_at": timestamp(item.get("first_published"), now),
        "updated_at": timestamp(item.get("updated_at"), now), "description_snippet": "",
        "source": "Greenhouse / " + board.employer, "source_url": board.endpoint}


def _read_json(client, url):
    started = time.monotonic()
    with client.stream("GET", url, headers={"Accept": "application/json", "User-Agent": "ECE-Learning-Advisor/0.3"},
                       timeout=TIMEOUT, follow_redirects=False) as response:
        if time.monotonic() - started > 12:
            raise ValueError("Employer response exceeds its request limit")
        if response.status_code != 200:
            raise OpportunityResponseError(response.status_code)
        if "application/json" not in response.headers.get("content-type", "").lower():
            raise ValueError("Employer board did not return JSON")
        length = int(response.headers.get("content-length", "0"))
        if not 0 <= length <= MAX_JSON_BYTES:
            raise ValueError("Employer response exceeds its size limit")
        body = bytearray()
        for chunk in response.iter_bytes(chunk_size=65536):
            body.extend(chunk)
            if len(body) > MAX_JSON_BYTES or time.monotonic() - started > 12:
                raise ValueError("Employer response exceeds its request limit")
        if time.monotonic() - started > 12:
            raise ValueError("Employer response exceeds its request limit")
        return json.loads(body)


def _fetch_board(client, board, now):
    check = {"board": board.token, "employer": board.employer, "url": board.endpoint,
             "status": "unavailable", "valid_posts": 0, "rejected_posts": 0, "checked_at": None, "http_status": None}
    try:
        payload = _read_json(client, board.endpoint)
        if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list) or len(payload["jobs"]) > MAX_POSTS:
            raise ValueError("Invalid employer-board response")
        posts, seen = [], set()
        for item in payload["jobs"]:
            try:
                post = normalize_post(item, board, now)
            except (ValueError, TypeError, AttributeError):
                check["rejected_posts"] += 1
                continue
            if post is not None and post["id"] not in seen:
                seen.add(post["id"])
                posts.append(post)
        if payload["jobs"] and not posts and check["rejected_posts"]:
            raise ValueError("No posting could be validated")
        check.update(status="verified", valid_posts=len(posts), checked_at=now.isoformat(), http_status=200)
        return posts, check
    except (httpx.HTTPError, ValueError, TypeError, RecursionError, OSError) as exc:
        check["http_status"] = getattr(exc, "http_status", None)
        check["failure_kind"] = ("timeout" if isinstance(exc, httpx.TimeoutException) else
            "network" if isinstance(exc, httpx.HTTPError) else "response" if isinstance(exc, OpportunityResponseError) else "validation")
        return [], check


def search_employer_jobs(career, location="", internship=False, *, updated_within=None, early_career=False, client=None, boards=None, now=None):
    validate_filters(career, location, internship, updated_within, early_career)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("The source-check time needs a timezone")
    boards = load_employer_boards() if boards is None else [EmployerBoard.model_validate(b.model_dump()) for b in boards]
    if not 1 <= len(boards) <= MAX_BOARDS or len({b.token for b in boards}) != len(boards):
        raise ValueError("Employer-board configuration exceeds its limits")
    context = nullcontext(client) if client is not None else httpx.Client(timeout=TIMEOUT, follow_redirects=False,
        limits=httpx.Limits(max_connections=3, max_keepalive_connections=3))
    with context as http, ThreadPoolExecutor(max_workers=min(3, len(boards))) as pool:
        results = list(pool.map(lambda board: _fetch_board(http, board, now), boards))
    checks = [check for _, check in results]
    if not any(check["status"] == "verified" for check in checks):
        raise OpportunitySearchError(checks)
    issues = [check["employer"] + ": this board could not be checked; its listings are omitted."
              for check in checks if check["status"] != "verified"]
    if any(check["rejected_posts"] for check in checks):
        issues.append("Some provider records could not be validated and were omitted.")
    found = []
    for posts, _ in results:
        for post in posts:
            title = normalized_title(post["title"])
            matches = re.findall(CAREER_PATTERNS[career], title, re.I)
            if not matches or not re.search(ROLE_PATTERN, title, re.I) or re.search(EXCLUDED_ROLES, title, re.I):
                continue
            if location.strip().casefold() not in post["location"].casefold():
                continue
            if internship and not re.search(INTERN_PATTERN, title, re.I):
                continue
            if early_career and not early_career_title(title):
                continue
            if updated_within is not None and (post["updated_at"] is None
                    or datetime.fromisoformat(post["updated_at"]) < now - timedelta(days=updated_within)):
                continue
            found.append({**post, "matched_terms": list(dict.fromkeys(m.casefold() for m in matches))})
    found.sort(key=lambda post: (post["updated_at"] or "", post["id"]), reverse=True)
    return JobSearchResult(found[:MAX_RESULTS], now.isoformat(), "AI / Machine Learning" if career == "ai_ml" else "Embedded Systems",
        location.strip() or "All listed locations", provider="greenhouse", checks=checks, issues=issues, total_matches=len(found),
        role_filter="internship" if internship else "early_career" if early_career else "all", source_scope_hash=board_scope_hash(boards),
        snapshot_listings=found[:MAX_SNAPSHOT_MATCHES])


def request_opportunities(state, career, location, internship, *, provider="greenhouse", updated_within=None,
                          early_career=False, reuse=False, now=None, public_search=None, adzuna_search=None, app_id="", app_key=""):
    """One explicit action, with optional recent-result reuse and no stale fallback."""
    from .jobs import search_jobs
    state.pop("job_result", None)
    state.pop("job_error", None)
    state.pop("job_detail", None)
    state.pop("job_detail_error", None)
    state.pop("job_page_error", None)
    validate_filters(career, location, internship, updated_within, early_career)
    now = now or datetime.now(timezone.utc)
    if (now.tzinfo is None or not isinstance(provider, str) or provider not in {"greenhouse", "adzuna"} or type(reuse) is not bool
            or provider == "adzuna" and (updated_within is not None or early_career)):
        raise ValueError("Unsupported opportunity source or filters")
    boards = load_employer_boards() if provider == "greenhouse" else None
    scope = board_scope_hash(boards) if boards else None
    key = (provider, career, location.strip().casefold(), internship, updated_within, early_career, scope)
    cached = state.get("jobs_cache")
    if not isinstance(cached, dict) or not isinstance(cached.get("result"), JobSearchResult):
        cached = None
    age = now.timestamp() - cached["created"] if cached and isinstance(cached.get("created"), (int, float)) else -1
    if reuse and cached and cached.get("key") == key and cached["result"].provider == provider and 0 <= age < CACHE_SECONDS:
        from dataclasses import replace
        result = replace(cached["result"], cache_state="reused")
    elif provider == "greenhouse":
        try:
            result = (public_search or search_employer_jobs)(career, location, internship, updated_within=updated_within,
                early_career=early_career, boards=boards)
        except OpportunitySearchError as exc:
            state["job_error"] = {"provider": provider, "checks": exc.checks}
            raise
    elif provider == "adzuna":
        result = (adzuna_search or search_jobs)(app_id, app_key, career, location, internship)
    else:
        raise ValueError("Unsupported opportunity source")
    if not isinstance(result, JobSearchResult) or result.provider != provider:
        raise ValueError("Opportunity response does not match its selected source")
    if provider == "greenhouse" and result.source_scope_hash not in {None, scope}:
        raise ValueError("Opportunity response does not match its configured boards")
    if result.snapshot_listings is not None:
        from dataclasses import replace
        from .opportunity_pages import page_info
        page_info(result)
        result = replace(result, listings=result.snapshot_listings[:MAX_RESULTS], page=0)
    if result.cache_state != "reused":
        state["jobs_cache"] = {"key": key, "created": now.timestamp(), "result": result}
    state["job_result"] = result
    return result
