"""Bounded, on-use checks of configured official course pages.

Public course fields and selected prerequisite statements are cached. Academic
interpretations remain reviewed application data; fetching a page never
interprets an opaque requirement ID or approves a changed condition.
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
from .models import Catalog, Record, Rule, Source, SourceCheck, StrictModel, StudentProfile, normalize_code, rule_hash
from .rules import dependency_codes
from .rule_sources import prepare_rule_jobs, fetch_rule_source, apply_rule_source, finalize_rule_checks
from .discovery import prepare_discovery_jobs, select_candidates, add_discovered_course, apply_discovered_rule
from .resource_sources import prepare_resource_jobs, fetch_resource_source, apply_resource_source
from .source_http import MAX_PAGE_BYTES, REQUEST_TIMEOUT, SourceRequest, failure_kind, read_public_page

MAX_CACHE_BYTES = 100_000
MAX_SOURCES = 8


class CourseSnapshot(StrictModel):
    code: str = Field(pattern=r"^[A-Z]{2,8}\d{3}[A-Z]{0,2}$")
    course_id: str | None = Field(default=None, pattern=r"^\d{7}$")
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
    schema_version: Literal[2] = 2
    url: str
    data: CourseSnapshot
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    retrieved_at: AwareDatetime
    last_checked_at: AwareDatetime
    etag: str | None = Field(default=None, max_length=512)
    last_modified: str | None = Field(default=None, max_length=100)


@dataclass
class CatalogRefresh:
    catalog: Catalog
    checks: list[SourceCheck] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    elapsed: float = 0.0
    discovery_selection: dict = field(default_factory=dict)

    def trace(self):
        return {"enabled": True, "catalog_version": self.catalog.catalog_version,
                "discovery_selection": self.discovery_selection,
                "discovered_courses": {r.record_id: {"origin": r.discovery.model_dump(mode="json"),
                    "field_sources": r.field_sources, "study_stage": r.study_stage,
                    "stage_origin": "team_learning_annotation", "rule_verification": r.rule_verification,
                    "rule_evidence_ids": [p.evidence_id for p in r.rule_evidence],
                    "rule_hash": rule_hash(r.rule) if r.rule_reviewed else None,
                    "reviewed_statement_hashes": {p.evidence_id: p.statement_hash for p in r.rule_evidence}}
                    for r in self.catalog.records if r.discovery},
                "checks": [check.model_dump(mode="json") for check in self.checks]}


def _official_course_url(url: str):
    parsed = urlparse(url)
    if (parsed.scheme != "https" or parsed.hostname != "catalog.arizona.edu"
            or parsed.port not in {None, 443} or parsed.username or parsed.password
            or parsed.query or parsed.fragment or not re.fullmatch(r"/courses/\d+", parsed.path)):
        raise ValueError("Unsupported official course URL")


def _cache_path(directory: Path, source: Source, record: Record):
    identity = "|".join([source.url, record.code or "discovered", record.catalog_version])
    return directory / (hashlib.sha256(identity.encode()).hexdigest() + ".json")


def _read_cache(path: Path, source: Source, record: Record):
    try:
        if path.stat().st_size > MAX_CACHE_BYTES:
            return None
        saved = CachedCourse.model_validate_json(path.read_bytes())
        if (saved.url != source.url or (saved.data.code != record.code if record.code else
                not _discovery_code(saved.data.code) or saved.data.course_id != source.url.rsplit('/', 1)[-1])
                or saved.data.course_id is not None and saved.data.course_id != source.url.rsplit('/', 1)[-1]
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


def _discovery_code(code):
    return bool(re.fullmatch(r"(?:ECE|CSC)[1-4]\d{2}[A-Z]{0,2}", code))


def _snapshot(page: str, record: Record, edition: str):
    candidate = extract_course(page)
    credits = candidate["credits"]
    if (not isinstance(credits, dict)
            or any(isinstance(credits.get(bound), bool) or not isinstance(credits.get(bound), (int, float))
                   for bound in ("min", "max"))
            or credits.get("min") != credits.get("max")):
        raise ValueError("Variable or missing course credits require review")
    code = normalize_code(candidate["code"])
    if ((code != record.code if record.code else not _discovery_code(code)) or candidate["catalog_version"] != edition):
        raise ValueError("The course identity or active catalog edition does not match")
    return CourseSnapshot(code=code, course_id=candidate["course_id"], title=candidate["title"], summary=candidate["summary"],
                          credits=credits["min"], catalog_version=edition,
                          requirement_reference=candidate["requirement_reference"])


def _fetch_one(source, record, directory, client, now):
    attempted = now or datetime.now(timezone.utc)
    path = _cache_path(directory, source, record)
    cached = None
    request = SourceRequest()
    check = SourceCheck(source_id=source.source_id, code=record.code or source.source_id, url=source.url,
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
        page = read_public_page(client, source.url, headers, request=request)
        check.http_status = page.status
        if page.status == 304:
            if cached is None:
                raise ValueError("A not-modified response needs a validated cache")
            saved = cached.model_copy(update={"last_checked_at": now or datetime.now(timezone.utc)})
            check.status = "not_modified"
        else:
            data = _snapshot(page.text, record, record.catalog_version)
            if (record.code is None or data.course_id is not None) and data.course_id != source.url.rsplit('/', 1)[-1]:
                raise ValueError("The course's internal identity does not match its link")
            fingerprint = snapshot_hash(data)
            checked = now or datetime.now(timezone.utc)
            saved = CachedCourse(url=source.url, data=data, content_hash=fingerprint,
                                 retrieved_at=checked, last_checked_at=checked,
                                 etag=page.etag, last_modified=page.last_modified)
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
        check.http_status = getattr(exc, "http_status", check.http_status)
        check.failure_kind = failure_kind(exc, check.http_status)
        check.status = "stale_cache" if cached else "bundled_fallback"
        check.message = (f"{record.code}: source check failed. Using dated cached evidence."
                         if cached else f"{record.code}: source check failed. Using the dated bundled snapshot.")
        if cached:
            check.retrieved_at = cached.retrieved_at
            check.last_checked_at = cached.last_checked_at
            check.content_hash = cached.content_hash
        return cached, check
    finally:
        request.apply(check)


def _apply(record, source, saved, check):
    fresh = check.status in {"updated", "unchanged", "not_modified"}
    source.verification_status = "verified" if fresh else "stale"
    if saved is None:
        return
    data = saved.data
    if record.requirement_reference != data.requirement_reference:
        record.rule_reviewed = False
        record.rule_verification = "changed"
        record.rule = Rule(type="unknown", note="The source enrollment reference changed and needs review.")
    record.title, record.summary, record.credits = data.title, data.summary, data.credits
    record.requirement_reference = data.requirement_reference
    record.review_status = "source_fetched"
    record.field_sources = {key: source.source_id for key in ("title", "summary", "credits", "requirement_reference")}
    source.title = record.code + " — " + data.title
    source.retrieved_at, source.last_checked_at = saved.retrieved_at, saved.last_checked_at
    source.content_hash = saved.content_hash
    source.review_note = ("Description and units parsed from the official course page. "
                          "Enrollment conditions are not automatically interpreted or reviewed.")


def refresh_catalog(catalog: Catalog, profile: StudentProfile, *, cache_dir=Path(".cache/sources"),
                    client=None, now=None, discovery_plans=(), resource_checks=False) -> CatalogRefresh:
    """Check relevant configured course pages once per explicit submitted request."""
    started = time.perf_counter()
    active = catalog.model_copy(deep=True)
    for source in active.sources:
        source.verification_status = "snapshot"
    result = CatalogRefresh(active)
    resource_jobs, resource_skips = prepare_resource_jobs(active, profile, now) if resource_checks else ([], [])
    result.checks.extend(resource_skips)
    resource_futures = []
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
        for record in courses:
            if record.rule_evidence:
                record.rule_verification = "unsupported"
                for proof in record.rule_evidence:
                    proof.verification_status = "unsupported"
        result.issues.append("Academic source checks do not support your catalog edition yet. "
                             f"Showing dated {active.catalog_version} references; enrollment remains unverified.")
        for source, record in targets:
            result.checks.append(SourceCheck(source_id=source.source_id, code=record.code,
                url=source.url, status="unsupported_edition", attempted_at=now or datetime.now(timezone.utc),
                retrieved_at=source.retrieved_at, last_checked_at=source.last_checked_at))
    elif courses or resource_jobs:
        selected, omitted = targets[:MAX_SOURCES], targets[MAX_SOURCES:]
        jobs, rule_checks, rule_issues = prepare_rule_jobs(active, courses, profile, now)
        result.checks.extend(rule_checks)
        result.issues.extend(rule_issues)
        plans, discovery_checks, discovery_issues = prepare_discovery_jobs(active, profile, jobs, discovery_plans, now)
        result.checks.extend(discovery_checks)
        result.issues.extend(discovery_issues)
        if selected or jobs or resource_jobs:
            context = nullcontext(client) if client is not None else httpx.Client(
                timeout=REQUEST_TIMEOUT, follow_redirects=False,
                limits=httpx.Limits(max_connections=3, max_keepalive_connections=3))
            with context as http, ThreadPoolExecutor(max_workers=min(3, len(selected) + len(jobs) + len(resource_jobs))) as pool:
                rule_futures = [pool.submit(fetch_rule_source, job, Path(cache_dir), http, now) for job in jobs]
                futures = [pool.submit(_fetch_one, source, record, Path(cache_dir), http, now)
                           for source, record in selected]
                resource_futures = [(job, pool.submit(fetch_resource_source, job, Path(cache_dir), http, now))
                                    for job in resource_jobs]
                program_results = {}
                for job, future in zip(jobs, rule_futures):
                    saved, check = future.result()
                    apply_rule_source(active, job, saved, check)
                    program_results[job.source.source_id] = saved, check
                    result.checks.append(check)
                selection = select_candidates(active, plans, program_results, MAX_SOURCES - len(selected), profile=profile)
                result.discovery_selection = selection.trace
                candidate_futures = []
                for candidate in selection.candidates:
                    program = next(s for s in active.sources if s.source_id == candidate.plan.source.source_id)
                    source, placeholder = candidate.placeholder(program.retrieved_at)
                    candidate_futures.append((candidate, source,
                        pool.submit(_fetch_one, source, placeholder, Path(cache_dir), http, now)))
                if selection.remaining:
                    result.issues.append(f"Course discovery is limited to this request's download budget; {selection.remaining} additional links were not fetched.")
                for (source, record), future in zip(selected, futures):
                    saved, check = future.result()
                    _apply(record, source, saved, check)
                    result.checks.append(check)
                    if check.message:
                        result.issues.append(check.message)
                for candidate, source, future in candidate_futures:
                    saved, check = future.result()
                    record = add_discovered_course(active, candidate, source, saved, check, now)
                    if record is not None:
                        program_saved, program_check = program_results[candidate.plan.source.source_id]
                        apply_discovered_rule(record, candidate, program_saved, program_check)
                        courses.append(record)
                    selection.record_result(candidate, record, check)
                    result.checks.append(check)
                    if check.message:
                        result.issues.append(check.message)
        for source, record in omitted:
            result.checks.append(SourceCheck(source_id=source.source_id, code=record.code, url=source.url,
                status="skipped", attempted_at=now or datetime.now(timezone.utc), retrieved_at=source.retrieved_at))
        if omitted:
            result.issues.append("The source-check limit was reached; remaining records retain dated snapshots.")
        finalize_rule_checks(active, courses, result.checks)
        result.issues.extend(check.message for check in result.checks if check.kind in {"rule", "discovery"}
                             and check.message and check.message not in result.issues)
    # Learning resources do not depend on the student's academic catalog edition.
    if resource_jobs and not resource_futures:
        context = nullcontext(client) if client is not None else httpx.Client(
            timeout=REQUEST_TIMEOUT, follow_redirects=False,
            limits=httpx.Limits(max_connections=3, max_keepalive_connections=3))
        with context as http, ThreadPoolExecutor(max_workers=min(3, len(resource_jobs))) as pool:
            resource_futures = [(job, pool.submit(fetch_resource_source, job, Path(cache_dir), http, now))
                                for job in resource_jobs]
    for job, future in resource_futures:
        saved, check = future.result()
        apply_resource_source(active, job, saved, check)
        result.checks.append(check)
    result.issues.extend(check.message for check in result.checks if check.kind == "resource" and check.message)
    result.elapsed = time.perf_counter() - started
    return result
