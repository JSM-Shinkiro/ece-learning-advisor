"""Bounded, on-use checks of configured official course pages.

Only public course descriptions are cached. Academic rules remain reviewed
application data; fetching a page never interprets an opaque requirement ID.
"""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import httpx
from pydantic import AwareDatetime, Field, field_validator

from .ingest import extract_course
from .models import Catalog, Record, Rule, Source, StrictModel, StudentProfile, normalize_code
from .rules import dependency_codes

MAX_PAGE_BYTES = 3_000_000
MAX_CACHE_BYTES = 100_000
MAX_SOURCES = 8
REQUEST_TIMEOUT = httpx.Timeout(6.0, connect=4.0, pool=4.0)


class CourseSnapshot(StrictModel):
    code: str = Field(pattern=r"^[A-Z]{2,8}\d{3}[A-Z]{0,2}$")
    title: str = Field(min_length=1, max_length=500)
    summary: str = Field(min_length=1, max_length=7000)
    credits: float = Field(ge=0, le=30, allow_inf_nan=False)
    catalog_version: str = Field(pattern=r"^20\d{2}-20\d{2}$")
    requirement_reference: str | None = Field(default=None, max_length=200)

    @field_validator("title", "summary")
    @classmethod
    def nonempty_text(cls, value):
        if not value.strip():
            raise ValueError("Course text is empty")
        return value


def snapshot_hash(data: CourseSnapshot) -> str:
    return hashlib.sha256(data.model_dump_json().encode()).hexdigest()


class CachedCourse(StrictModel):
    schema_version: Literal[1] = 1
    url: str
    data: CourseSnapshot
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    retrieved_at: AwareDatetime
    last_checked_at: AwareDatetime
    etag: str | None = Field(default=None, max_length=512)
    last_modified: str | None = Field(default=None, max_length=100)


class SourceCheck(StrictModel):
    source_id: str
    code: str
    url: str
    status: Literal["updated", "unchanged", "not_modified", "stale_cache",
                    "bundled_fallback", "unsupported_edition", "skipped"]
    attempted_at: datetime
    last_checked_at: datetime | None = None
    retrieved_at: datetime
    content_hash: str | None = None
    content_changed: bool = False
    cache_saved: bool = False
    http_status: int | None = None
    failure_kind: Literal["timeout", "network", "response", "validation"] | None = None
    message: str = ""


@dataclass
class CatalogRefresh:
    catalog: Catalog
    checks: list[SourceCheck] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    elapsed: float = 0.0

    def trace(self):
        return {"enabled": True, "catalog_version": self.catalog.catalog_version,
                "checks": [check.model_dump(mode="json") for check in self.checks]}


def _official_course_url(url: str):
    parsed = urlparse(url)
    if (parsed.scheme != "https" or parsed.hostname != "catalog.arizona.edu"
            or parsed.port not in {None, 443} or parsed.username or parsed.password
            or parsed.query or parsed.fragment or not re.fullmatch(r"/courses/\d+", parsed.path)):
        raise ValueError("Unsupported official course URL")


def _cache_path(directory: Path, source: Source, record: Record):
    identity = "|".join([source.url, record.code, record.catalog_version])
    return directory / (hashlib.sha256(identity.encode()).hexdigest() + ".json")


def _read_cache(path: Path, source: Source, record: Record):
    try:
        if path.stat().st_size > MAX_CACHE_BYTES:
            return None
        saved = CachedCourse.model_validate_json(path.read_bytes())
        if (saved.url != source.url or saved.data.code != record.code
                or saved.data.catalog_version != record.catalog_version
                or saved.content_hash != snapshot_hash(saved.data)
                or saved.last_checked_at < saved.retrieved_at):
            return None
        return saved
    except (OSError, ValueError):
        return None


def _save_cache(path: Path, saved: CachedCourse):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix="source-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(saved.model_dump_json())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _snapshot(page: str, record: Record, edition: str):
    candidate = extract_course(page)
    credits = candidate["credits"]
    if (not isinstance(credits, dict)
            or any(isinstance(credits.get(bound), bool) or not isinstance(credits.get(bound), (int, float))
                   for bound in ("min", "max"))
            or credits.get("min") != credits.get("max")):
        raise ValueError("Variable or missing course credits require review")
    if normalize_code(candidate["code"]) != record.code or candidate["catalog_version"] != edition:
        raise ValueError("The course identity or active catalog edition does not match")
    return CourseSnapshot(code=record.code, title=candidate["title"], summary=candidate["summary"],
                          credits=credits["min"], catalog_version=edition,
                          requirement_reference=candidate["requirement_reference"])


def _fetch_one(source, record, directory, client, now):
    attempted = now or datetime.now(timezone.utc)
    path = _cache_path(directory, source, record)
    cached = None
    check = SourceCheck(source_id=source.source_id, code=record.code, url=source.url,
                        status="bundled_fallback", attempted_at=attempted,
                        retrieved_at=source.retrieved_at, last_checked_at=source.last_checked_at)
    try:
        _official_course_url(source.url)
        cached = _read_cache(path, source, record)
        headers = {"User-Agent": "ECE-Learning-Advisor/0.2", "Accept": "text/html"}
        if cached and cached.etag:
            headers["If-None-Match"] = cached.etag
        if cached and cached.last_modified:
            headers["If-Modified-Since"] = cached.last_modified
        started = time.monotonic()
        with client.stream("GET", source.url, headers=headers, timeout=REQUEST_TIMEOUT,
                           follow_redirects=False) as response:
            check.http_status = response.status_code
            if response.status_code == 304:
                if cached is None:
                    raise ValueError("A not-modified response needs a validated cache")
                saved = cached.model_copy(update={"last_checked_at": now or datetime.now(timezone.utc)})
                check.status = "not_modified"
            else:
                # Redirects, removed pages, and unfamiliar formats retain dated evidence.
                if response.status_code != 200 or "text/html" not in response.headers.get("content-type", "").lower():
                    raise ValueError("The official course page is unavailable")
                if int(response.headers.get("content-length", "0")) > MAX_PAGE_BYTES:
                    raise ValueError("The official page exceeds the download limit")
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_PAGE_BYTES or time.monotonic() - started > 12:
                        raise ValueError("The official page exceeds the request budget")
                data = _snapshot(body.decode("utf-8"), record, record.catalog_version)
                fingerprint = snapshot_hash(data)
                checked = now or datetime.now(timezone.utc)
                etag, modified = response.headers.get("etag"), response.headers.get("last-modified")
                saved = CachedCourse(url=source.url, data=data, content_hash=fingerprint,
                                     retrieved_at=checked, last_checked_at=checked,
                                     etag=etag if etag and len(etag) <= 512 else None,
                                     last_modified=modified if modified and len(modified) <= 100 else None)
                check.content_changed = cached is None or fingerprint != cached.content_hash
                check.status = "updated" if check.content_changed else "unchanged"
        try:
            _save_cache(path, saved)
            check.cache_saved = True
        except OSError:
            check.message = "Fresh source information was fetched, but its cache could not be saved."
        check.retrieved_at = saved.retrieved_at
        check.last_checked_at = saved.last_checked_at
        check.content_hash = saved.content_hash
        return saved, check
    except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
        check.failure_kind = ("timeout" if isinstance(exc, httpx.TimeoutException) else
                              "network" if isinstance(exc, httpx.HTTPError) else
                              "response" if check.http_status not in {None, 200, 304} else "validation")
        check.status = "stale_cache" if cached else "bundled_fallback"
        check.message = (f"{record.code}: source check failed. Using dated cached evidence."
                         if cached else f"{record.code}: source check failed. Using the dated bundled snapshot.")
        if cached:
            check.retrieved_at = cached.retrieved_at
            check.last_checked_at = cached.last_checked_at
            check.content_hash = cached.content_hash
        return cached, check


def _apply(record, source, saved, check):
    fresh = check.status in {"updated", "unchanged", "not_modified"}
    source.verification_status = "verified" if fresh else "stale"
    if saved is None:
        return
    data = saved.data
    if record.requirement_reference != data.requirement_reference:
        record.rule_reviewed = False
        record.rule = Rule(type="unknown", note="The source enrollment reference changed and needs review.")
    record.title, record.summary, record.credits = data.title, data.summary, data.credits
    record.requirement_reference = data.requirement_reference
    record.review_status = "source_fetched"
    source.title = record.code + " — " + data.title
    source.retrieved_at, source.last_checked_at = saved.retrieved_at, saved.last_checked_at
    source.content_hash = saved.content_hash
    source.review_note = ("Description and units parsed from the official course page. "
                          "Enrollment conditions are not automatically interpreted or reviewed.")


def refresh_catalog(catalog: Catalog, profile: StudentProfile, *, cache_dir=Path(".cache/sources"),
                    client=None, now=None) -> CatalogRefresh:
    """Check relevant configured course pages once per explicit submitted request."""
    started = time.perf_counter()
    active = catalog.model_copy(deep=True)
    result = CatalogRefresh(active)
    sources = {s.source_id: s for s in active.sources}
    courses = [r for r in active.records if r.kind == "course" and (
        profile.career_id == "exploring" or not r.career_ids or profile.career_id in r.career_ids)]
    needed = {code for record in courses if record.rule_reviewed for code in dependency_codes(record.rule)}
    courses.extend(r for r in active.records if r.kind == "course" and r.code in needed and r not in courses)
    targets = []
    for record in courses:
        source = next((sources[sid] for sid in record.source_ids if sid.startswith("catalog:")
                       and urlparse(sources[sid].url).path.startswith("/courses/")), None)
        if source is not None:
            if (not record.code or record.catalog_version != active.catalog_version
                    or source.catalog_version not in {None, record.catalog_version}):
                result.checks.append(SourceCheck(source_id=source.source_id, code=record.code or record.record_id,
                    url=source.url, status="unsupported_edition", attempted_at=now or datetime.now(timezone.utc),
                    retrieved_at=source.retrieved_at, last_checked_at=source.last_checked_at))
                result.issues.append(f"{record.code or record.record_id}: source edition metadata needs review; retaining dated evidence.")
            else:
                targets.append((source, record))
    if profile.catalog_version != active.catalog_version:
        result.issues.append("Live source checks do not support your catalog edition yet. "
                             f"Showing dated {active.catalog_version} references; enrollment remains unverified.")
        for source, record in targets:
            result.checks.append(SourceCheck(source_id=source.source_id, code=record.code,
                url=source.url, status="unsupported_edition", attempted_at=now or datetime.now(timezone.utc),
                retrieved_at=source.retrieved_at, last_checked_at=source.last_checked_at))
    elif targets:
        selected, omitted = targets[:MAX_SOURCES], targets[MAX_SOURCES:]
        context = nullcontext(client) if client is not None else httpx.Client(
            timeout=REQUEST_TIMEOUT, follow_redirects=False,
            limits=httpx.Limits(max_connections=3, max_keepalive_connections=3))
        with context as http, ThreadPoolExecutor(max_workers=min(3, len(selected))) as pool:
            futures = [pool.submit(_fetch_one, source, record, Path(cache_dir), http, now)
                       for source, record in selected]
            for (source, record), future in zip(selected, futures):
                saved, check = future.result()
                _apply(record, source, saved, check)
                result.checks.append(check)
                if check.message:
                    result.issues.append(check.message)
        for source, record in omitted:
            result.checks.append(SourceCheck(source_id=source.source_id, code=record.code, url=source.url,
                status="skipped", attempted_at=now or datetime.now(timezone.utc), retrieved_at=source.retrieved_at))
        if omitted:
            result.issues.append("The source-check limit was reached; remaining records retain dated snapshots.")
    result.elapsed = time.perf_counter() - started
    return result
