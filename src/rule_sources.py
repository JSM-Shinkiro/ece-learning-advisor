"""Revalidate bounded, explicitly reviewed prerequisite-source statements."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

import httpx
from pydantic import AwareDatetime, Field, model_validator

from .ingest import extract_program_courses, extract_visible_program_statements
from .models import (Source, SourceCheck, StrictModel, program_source_url_matches, rule_binding_matches, statement_hash)
from .source_http import failure_kind, read_public_page

MAX_RULE_SOURCES = 2
MAX_RULE_CACHE_BYTES = 200_000
Statement = Annotated[str, Field(min_length=1, max_length=3000)]


class ProgramSnapshot(StrictModel):
    program_code: str = Field(pattern=r"^[A-Z][A-Z0-9]{1,20}$")
    catalog_version: str = Field(pattern=r"^20\d{2}-20\d{2}$")
    statements: dict[str, Statement] = Field(default_factory=dict, max_length=16)
    course_ids: dict[str, list[Annotated[str, Field(pattern=r"^\d{7}$")]]] = Field(default_factory=dict, max_length=16)
    discovery_statements: dict[str, Statement] = Field(default_factory=dict, max_length=16)

    @model_validator(mode="after")
    def bounded_sections(self):
        if not self.statements and not self.course_ids:
            raise ValueError("A program snapshot needs selected evidence")
        if any(not 1 <= len(ids) <= 40 or len(set(ids)) != len(ids) for ids in self.course_ids.values()):
            raise ValueError("A program course list is invalid")
        if not set(self.discovery_statements) <= set(self.course_ids):
            raise ValueError("Discovery statements need matching course-list sections")
        return self


def program_hash(data: ProgramSnapshot):
    payload = json.dumps(data.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


class CachedProgram(StrictModel):
    schema_version: Literal[3] = 3
    url: str
    data: ProgramSnapshot
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    retrieved_at: AwareDatetime
    last_checked_at: AwareDatetime
    etag: str | None = Field(default=None, max_length=512)
    last_modified: str | None = Field(default=None, max_length=100)


@dataclass
class RuleJob:
    source: Source
    program_code: str
    edition: str
    sections: set[str] = field(default_factory=set)
    record_ids: list[str] = field(default_factory=list)
    discovery_sections: set[str] = field(default_factory=set)


def _program_url(job):
    if not program_source_url_matches(job.source.url, job.program_code):
        raise ValueError("Unsupported program prerequisite URL")


def _path(directory, job):
    identity = json.dumps([job.source.url, job.program_code, job.edition, sorted(job.sections), sorted(job.discovery_sections)])
    return Path(directory) / "rules" / (hashlib.sha256(identity.encode()).hexdigest() + ".json")


def _read(path, job):
    try:
        if path.stat().st_size > MAX_RULE_CACHE_BYTES:
            return None
        saved = CachedProgram.model_validate_json(path.read_bytes())
        if (saved.url != job.source.url or saved.data.program_code != job.program_code
                or saved.data.catalog_version != job.edition or set(saved.data.statements) != job.sections
                or set(saved.data.course_ids) != job.discovery_sections
                or not set(saved.data.discovery_statements) <= job.discovery_sections
                or saved.content_hash != program_hash(saved.data) or saved.last_checked_at < saved.retrieved_at):
            return None
        return saved
    except (OSError, ValueError):
        return None


def _write(path, saved):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix="rule-source-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(saved.model_dump_json())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def prepare_rule_jobs(catalog, courses, profile, now=None):
    sources = {s.source_id: s for s in catalog.sources}
    groups, checks, issues = {}, [], []
    for record in courses:
        if not record.rule_reviewed:
            continue
        record.rule_verification = "unavailable"
        if not record.rule_evidence:
            issues.append(f"{record.code}: the reviewed condition has no configured revalidation evidence.")
            continue
        for proof in record.rule_evidence:
            proof.verification_status = "unavailable"
            source = sources[proof.source_id]
            binding = rule_binding_matches(record)
            edition = profile.catalog_version == record.catalog_version == proof.catalog_version == source.catalog_version
            if not binding or not edition:
                proof.verification_status = "changed" if not binding else "unsupported"
                checks.append(SourceCheck(source_id=source.source_id, code=record.code, url=source.url,
                    kind="rule", status="skipped" if not binding else "unsupported_edition",
                    attempted_at=now or datetime.now(timezone.utc), retrieved_at=source.retrieved_at,
                    last_checked_at=source.last_checked_at, rule_status="changed" if not binding else "unsupported",
                    message=f"{record.code}: prerequisite provenance or edition needs review."))
                continue
            job = groups.setdefault(source.source_id, RuleJob(source.model_copy(deep=True), proof.program_code, proof.catalog_version))
            if job.program_code != proof.program_code:
                proof.verification_status = "changed"
                issues.append(f"{record.code}: conflicting program provenance needs review.")
                continue
            job.sections.add(proof.section_id)
            if record.record_id not in job.record_ids:
                job.record_ids.append(record.record_id)
    jobs = list(groups.values())
    for job in jobs[MAX_RULE_SOURCES:]:
        checks.append(SourceCheck(source_id=job.source.source_id, code=job.program_code, url=job.source.url,
            kind="rule", status="skipped", attempted_at=now or datetime.now(timezone.utc),
            retrieved_at=job.source.retrieved_at, rule_status="unavailable",
            message="The prerequisite-source check limit was reached; conditions remain unverified."))
    return jobs[:MAX_RULE_SOURCES], checks, issues


def fetch_rule_source(job, directory, client, now=None):
    source = job.source
    check = SourceCheck(source_id=source.source_id, code=job.program_code, url=source.url, kind="rule",
        status="bundled_fallback", attempted_at=now or datetime.now(timezone.utc),
        retrieved_at=source.retrieved_at, last_checked_at=source.last_checked_at)
    if not job.record_ids:
        check.kind = "discovery"
    if job.discovery_sections:
        check.discovery_status = "unavailable"
    cached = None
    try:
        _program_url(job)
        if not 1 <= len(job.sections | job.discovery_sections) <= 16:
            raise ValueError("The prerequisite source-section limit was exceeded")
        path = _path(directory, job)
        cached = _read(path, job)
        headers = {"User-Agent": "ECE-Learning-Advisor/0.2", "Accept": "text/html"}
        if cached and cached.etag:
            headers["If-None-Match"] = cached.etag
        if cached and cached.last_modified:
            headers["If-Modified-Since"] = cached.last_modified
        page = read_public_page(client, source.url, headers)
        check.http_status = page.status
        if page.status == 304:
            if cached is None:
                raise ValueError("A not-modified response needs a validated program cache")
            saved = cached.model_copy(update={"last_checked_at": now or datetime.now(timezone.utc)})
            check.status = "not_modified"
        else:
            fields = (extract_visible_program_statements(page.text, job.program_code, sorted(job.sections)) if job.sections else {})
            if job.discovery_sections:
                try:
                    discovered = extract_program_courses(page.text, job.program_code, sorted(job.discovery_sections))
                    discovered["discovery_statements"] = {}
                    for section in sorted(job.discovery_sections):
                        try:
                            statement = extract_visible_program_statements(page.text, job.program_code, [section])
                            discovered["discovery_statements"].update(statement["statements"])
                        except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
                            # A missing condition must not erase validated course links.
                            continue
                    fields.update(discovered)
                except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
                    if not job.sections:
                        raise
                    check.message = "Course discovery is unavailable for the selected program section; prerequisite checks are separate."
            data = ProgramSnapshot.model_validate(fields)
            if data.catalog_version != job.edition:
                raise ValueError("The prerequisite catalog edition does not match")
            checked = now or datetime.now(timezone.utc)
            saved = CachedProgram(url=source.url, data=data, content_hash=program_hash(data),
                                  retrieved_at=checked, last_checked_at=checked,
                                  etag=page.etag, last_modified=page.last_modified)
            check.content_changed = cached is None or saved.content_hash != cached.content_hash
            check.status = "updated" if check.content_changed else "unchanged"
        if set(saved.data.course_ids) == job.discovery_sections:
            if job.discovery_sections:
                check.discovery_status = "verified"
            try:
                _write(path, saved)
                check.cache_saved = True
            except OSError:
                check.message = "Fresh program evidence was fetched, but its cache could not be saved."
        check.retrieved_at, check.last_checked_at = saved.retrieved_at, saved.last_checked_at
        check.content_hash = saved.content_hash
        return saved, check
    except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
        check.http_status = getattr(exc, "http_status", check.http_status)
        check.failure_kind = failure_kind(exc, check.http_status)
        check.status = "stale_cache" if cached else "bundled_fallback"
        check.message = "Prerequisite evidence could not be revalidated; affected academic conditions remain unknown."
        if cached:
            check.retrieved_at, check.last_checked_at = cached.retrieved_at, cached.last_checked_at
            check.content_hash = cached.content_hash
            if job.discovery_sections:
                check.discovery_status = "stale"
        return cached, check


def apply_rule_source(catalog, job, saved, check):
    source = next(s for s in catalog.sources if s.source_id == job.source.source_id)
    fresh = check.status in {"updated", "unchanged", "not_modified"}
    source.verification_status = "verified" if fresh else "stale"
    if saved:
        source.retrieved_at, source.last_checked_at = saved.retrieved_at, saved.last_checked_at
        source.content_hash = saved.content_hash
        source.review_note = ("Selected program sections fetched from the matching catalog edition. "
                              "Only unchanged, explicitly reviewed conditions can be evaluated automatically.")
    for record in catalog.records:
        if record.record_id not in job.record_ids:
            continue
        for proof in record.rule_evidence:
            if proof.source_id != source.source_id or proof.program_code != job.program_code:
                continue
            if saved and proof.section_id in saved.data.statements:
                proof.observed_text = saved.data.statements[proof.section_id]
                same = statement_hash(proof.observed_text) == proof.statement_hash
                proof.verification_status = "changed" if not same else "verified" if fresh else "stale"
            else:
                proof.verification_status = "unavailable"


def finalize_rule_checks(catalog, courses, checks):
    sources = {s.source_id: s for s in catalog.sources}
    priority = ["changed", "unsupported", "unavailable", "stale", "snapshot", "verified"]
    for record in courses:
        if not record.rule_reviewed:
            if record.rule_evidence and record.rule_verification != "changed":
                record.rule_verification = "unavailable"
            continue
        if not record.rule_evidence:
            continue
        if not rule_binding_matches(record):
            record.rule_verification = "changed"
            continue
        statuses = [p.verification_status for p in record.rule_evidence]
        course_sources = [sources[sid] for sid in record.source_ids if "/courses/" in sources[sid].url]
        if not course_sources or any(s.verification_status != "verified" for s in course_sources):
            statuses.append("stale")
        record.rule_verification = min(statuses, key=priority.index)
    for check in checks:
        if check.kind == "course":
            record = next((r for r in courses if r.code == check.code and r.rule_reviewed and r.rule_evidence), None)
            if record is not None:
                check.rule_status = record.rule_verification
            continue
        if check.kind != "rule":
            continue
        affected = [r for r in courses if any(p.source_id == check.source_id and p.verification_status != "snapshot"
                                             for p in r.rule_evidence)]
        if affected:
            check.rule_status = min((r.rule_verification for r in affected), key=priority.index)
            if check.rule_status != "verified":
                check.message = (check.message + " " if check.message else "") + "The affected prerequisite conditions remain unknown until their evidence and interpretation are verified."
