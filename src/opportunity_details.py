"""Explicit, source-bound checks of one displayed employer posting.

Descriptions are public source text, never model input or qualification rules.
Only one checked posting is kept in the session; each action requests it again.
"""

from __future__ import annotations

import hashlib
import html
import re
from contextlib import nullcontext
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Literal

import httpx
from pydantic import AwareDatetime, Field, model_validator

from .jobs import JobSearchResult
from .models import SourceAttempt, StrictModel
from .opportunities import (TIMEOUT, EmployerBoard, _read_json, opportunity_failure_kind,
    board_scope_hash, load_employer_boards, normalize_post, valid_posting_url)
from .source_http import SourceRequest

MAX_CONTENT_CHARS = 200_000
MAX_DESCRIPTION_CHARS = 50_000
CHANGED_FIELDS = ("title", "location", "url", "posted_at", "updated_at")


class _PostingText(HTMLParser):
    """Keep paragraph/list boundaries without rendering employer HTML."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "template"}:
            self.hidden += 1
        elif not self.hidden:
            if tag == "li": self.parts.append("\n• ")
            elif tag == "br": self.parts.append("\n")
            elif tag in {"p", "div", "h1", "h2", "h3", "h4", "ul", "ol"}: self.parts.append("\n\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "template"}:
            self.hidden = max(0, self.hidden - 1)
        elif not self.hidden and tag in {"p", "div", "h1", "h2", "h3", "h4", "ul", "ol"}:
            self.parts.append("\n\n")

    def handle_data(self, value):
        if not self.hidden: self.parts.append(value)


def posting_text(raw):
    parser = _PostingText()
    parser.feed(html.unescape(raw))
    parser.close()
    text = "\n".join(" ".join(line.split()) for line in "".join(parser.parts).splitlines())
    return re.sub(r"\n{3,}", "\n\n", text).strip()


class PostingContent(StrictModel):
    title: str
    employer: str
    location: str
    url: str
    posted_at: str | None
    updated_at: str | None
    description: str = Field(min_length=1, max_length=MAX_DESCRIPTION_CHARS)
    description_chars: int = Field(gt=0)
    description_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    truncated: bool


class PostingDetailCheck(StrictModel):
    posting_id: str
    source_url: str
    requested_at: AwareDatetime
    checked_at: AwareDatetime | None = None
    status: Literal["verified", "not_listed", "unavailable", "invalid_response"]
    http_status: int | None = None
    failure_kind: Literal["timeout", "network", "response", "validation"] | None = None
    changed_fields: list[str] = Field(default_factory=list)
    posting: PostingContent | None = None
    attempts: list[SourceAttempt] = Field(default_factory=list, max_length=2)
    retry_count: int = Field(default=0, ge=0, le=1)
    transport_seconds: float = Field(default=0, ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def consistent_outcome(self):
        if self.status == "verified":
            if (self.posting is None or self.checked_at is None or self.checked_at < self.requested_at
                    or self.http_status != 200 or self.failure_kind is not None):
                raise ValueError("Verified posting checks need validated content and a successful check time")
        elif self.posting is not None or self.checked_at is not None or self.changed_fields:
            raise ValueError("Failed posting checks cannot retain content or a successful check time")
        return self


def posting_binding(job, boards):
    """Derive the API URL from configured identities, never from a supplied URL."""
    if not isinstance(job, dict) or not isinstance(job.get("id"), str):
        raise ValueError("Choose a posting from the current employer-board results")
    match = re.fullmatch(r"greenhouse:([a-z][a-z0-9_-]{0,59}):([1-9][0-9]{0,15})", job["id"])
    if not match or int(match[2]) >= 10**16:
        raise ValueError("Invalid employer posting identity")
    matches = [EmployerBoard.model_validate(b.model_dump()) for b in boards if b.token == match[1]]
    if len(matches) != 1 or job.get("employer") != matches[0].employer:
        raise ValueError("The selected posting does not match a configured employer")
    board = matches[0]
    valid_posting_url(job.get("url"), board, match[2])
    return board, match[2], board.endpoint + "/" + match[2]


def fetch_posting_detail(job, *, boards=None, client=None, now=None):
    """One bounded public check, with one transient retry and no old description."""
    boards = load_employer_boards() if boards is None else boards
    board, identity, endpoint = posting_binding(job, boards)
    requested_at = now or datetime.now(timezone.utc)
    if requested_at.tzinfo is None:
        raise ValueError("The posting-check time needs a timezone")
    base = dict(posting_id=job["id"], source_url=endpoint, requested_at=requested_at)
    request = SourceRequest()
    context = nullcontext(client) if client is not None else httpx.Client(timeout=TIMEOUT, follow_redirects=False)
    try:
        with context as http:
            payload = _read_json(http, endpoint, request=request)
        # Bind both public posting identity and its returned source link.
        post = normalize_post(payload, board, requested_at)
        if post is None or post["id"] != job["id"]:
            raise ValueError("The returned posting does not match the selection")
        raw = payload.get("content")
        if not isinstance(raw, str) or not raw.strip() or len(raw) > MAX_CONTENT_CHARS:
            raise ValueError("The posting description is missing or exceeds its limit")
        # The API returns HTML (often entity-escaped); render only extracted text.
        text = posting_text(raw)
        if not text:
            raise ValueError("The posting description contains no visible text")
        content = PostingContent(**{key: post[key] for key in ("title", "employer", "location", "url", "posted_at", "updated_at")},
            description=text[:MAX_DESCRIPTION_CHARS], description_chars=len(text),
            description_sha256=hashlib.sha256(text.encode()).hexdigest(), truncated=len(text) > MAX_DESCRIPTION_CHARS)
        return PostingDetailCheck(**base, status="verified", **request.diagnostics(),
            checked_at=now or datetime.now(timezone.utc), posting=content,
            changed_fields=[key for key in CHANGED_FIELDS if job.get(key) != post[key]])
    except (httpx.HTTPError, ValueError, TypeError, RecursionError, OSError) as exc:
        status_code = request.diagnostics()["http_status"]
        kind = opportunity_failure_kind(exc, status_code)
        status = "not_listed" if status_code in {404, 410} else "invalid_response" if kind == "validation" else "unavailable"
        return PostingDetailCheck(**base, status=status, **request.diagnostics(), failure_kind=kind)


def request_posting_detail(state, posting_id, *, fetcher=None, now=None):
    """Validate the current search/scope before any detail request or display."""
    state.pop("job_detail", None)
    state.pop("job_detail_error", None)
    jobs = state.get("job_result")
    if not isinstance(jobs, JobSearchResult) or jobs.provider != "greenhouse":
        raise ValueError("Run an employer-board search before checking a posting")
    boards = load_employer_boards()
    if jobs.source_scope_hash not in {None, board_scope_hash(boards)}:
        raise ValueError("Employer-board settings changed; run a new search")
    matches = [job for job in jobs.listings if job.get("id") == posting_id]
    if len(matches) != 1:
        raise ValueError("Choose a posting displayed in the current search")
    job = matches[0]
    _, _, endpoint = posting_binding(job, boards)
    selected_page = jobs.page
    result = (fetcher or fetch_posting_detail)(job, boards=boards, now=now)
    if (state.get("job_result") is not jobs or jobs.page != selected_page
            or sum(item.get("id") == posting_id for item in jobs.listings) != 1):
        return None  # A new search, page or profile superseded the selection.
    if isinstance(result, PostingDetailCheck):
        result = PostingDetailCheck.model_validate(result.model_dump(warnings=False))
    if (not isinstance(result, PostingDetailCheck) or result.posting_id != posting_id
            or result.source_url != endpoint):
        raise ValueError("Posting details do not match the selected source")
    if result.posting:
        posting_binding({"id": result.posting_id, "employer": result.posting.employer, "url": result.posting.url}, boards)
    state["job_detail"] = result
    return result
