"""Bounded course candidates from configured, edition-specific program sections."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from .models import CourseOrigin, Record, Source, SourceCheck, StrictModel, program_source_url_matches
from .rule_sources import MAX_RULE_SOURCES, RuleJob

DEFAULT_PLANS = Path(__file__).resolve().parents[1] / "data" / "connectors" / "course_discovery.json"
MAX_DISCOVERED_COURSES = 3


class DiscoveryPlan(StrictModel):
    source: Source
    program_code: str = Field(pattern=r"^[A-Z][A-Z0-9]{1,20}$")
    section_ids: list[str] = Field(min_length=1, max_length=16)
    career_ids: list[Literal["ai_ml", "embedded"]] = Field(min_length=1, max_length=2)
    study_stage: Literal["foundation", "intermediate", "advanced"]

    @model_validator(mode="after")
    def matching_program(self):
        if (not program_source_url_matches(self.source.url, self.program_code)
                or not self.source.catalog_version
                or any(not re.fullmatch(r"R\d+/L?\d+", section) for section in self.section_ids)
                or len(set(self.section_ids)) != len(self.section_ids)):
            raise ValueError("Course-discovery configuration does not match its program source")
        return self


def load_discovery_plans(path=DEFAULT_PLANS):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list) or len(data) > MAX_RULE_SOURCES:
        raise ValueError("The course-discovery configuration exceeds its program-source budget")
    plans = [DiscoveryPlan.model_validate(item) for item in data]
    ids = [p.source.source_id for p in plans]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate course-discovery program source")
    return plans


def prepare_discovery_jobs(catalog, profile, jobs, plans, now=None):
    """Merge discovery with prerequisite jobs so a program is downloaded once."""
    sources = {s.source_id: s for s in catalog.sources}
    selected, checks, issues = [], [], []
    for plan in plans:
        if profile.career_id != "exploring" and profile.career_id not in plan.career_ids:
            continue
        if plan.source.catalog_version != profile.catalog_version:
            continue
        source = sources.get(plan.source.source_id, plan.source.model_copy(deep=True))
        existing = next((job for job in jobs if job.source.source_id == source.source_id), None)
        conflict = (source.url != plan.source.url or source.catalog_version != plan.source.catalog_version
                    or existing is not None and (existing.program_code != plan.program_code
                                                or existing.edition != profile.catalog_version))
        if (conflict or existing is None and len(jobs) >= MAX_RULE_SOURCES
                or len(set(plan.section_ids) | (existing.sections | existing.discovery_sections if existing else set())) > 16):
            checks.append(SourceCheck(source_id=source.source_id, code=plan.program_code, url=source.url,
                kind="discovery", status="skipped", discovery_status="unavailable",
                attempted_at=now or datetime.now(timezone.utc), retrieved_at=source.retrieved_at,
                message="Course discovery was skipped because its source binding or request budget is unsupported."))
            issues.append(checks[-1].message)
            continue
        if source.source_id not in sources:
            source.verification_status = "snapshot"
            catalog.sources.append(source)
            sources[source.source_id] = source
        if existing is None:
            existing = RuleJob(source.model_copy(deep=True), plan.program_code, profile.catalog_version)
            jobs.append(existing)
        existing.discovery_sections.update(plan.section_ids)
        selected.append(plan)
    return selected, checks, issues


@dataclass
class CourseCandidate:
    course_id: str
    plan: DiscoveryPlan
    sections: list[str]

    @property
    def url(self):
        return "https://catalog.arizona.edu/courses/" + self.course_id

    def placeholder(self, checked_at):
        source = Source(source_id="discovery:" + self.course_id, title="Linked official course",
            url=self.url, retrieved_at=checked_at, catalog_version=self.plan.source.catalog_version)
        record = Record(record_id="discovery:" + self.course_id, kind="course", title=source.title,
            summary="Waiting for validated official course content.", source_ids=[source.source_id],
            catalog_version=source.catalog_version)
        return source, record


def select_candidates(catalog, plans, program_results, limit):
    """Use only currently verified link lists; retain no personal query in caches."""
    known = {s.url for s in catalog.sources if "/courses/" in s.url}
    candidates, seen = [], set()
    for plan in plans:
        saved, check = program_results.get(plan.source.source_id, (None, None))
        if saved is None or check.discovery_status != "verified":
            continue
        sections_by_id = {}
        for section in plan.section_ids:
            for course_id in saved.data.course_ids.get(section, []):
                sections_by_id.setdefault(course_id, []).append(section)
        for course_id, sections in sections_by_id.items():
            candidate = CourseCandidate(course_id, plan, sections)
            if candidate.url in known or candidate.url in seen:
                continue
            seen.add(candidate.url)
            candidates.append(candidate)
    budget = max(0, min(MAX_DISCOVERED_COURSES, limit))
    return candidates[:budget], len(candidates) - min(budget, len(candidates))


def add_discovered_course(catalog, candidate, source, saved, check, now=None):
    if saved is None:
        check.status = "unavailable"
        check.retrieved_at = None
        check.message = "A discovered course could not be verified; no placeholder recommendation was added."
        return None
    data = saved.data
    check.code = data.code
    if check.status == "stale_cache":
        check.message = f"{data.code}: source check failed. Using dated cached evidence."
    if any(r.kind == "course" and r.code == data.code for r in catalog.records):
        check.status = "skipped"
        check.message = "A discovered link duplicates an existing course identity; the configured record was retained."
        return None
    source.source_id = check.source_id = "catalog:" + data.code
    if any(s.source_id == source.source_id for s in catalog.sources):
        check.status = "skipped"
        check.message = "A discovered source conflicts with an existing identity; no record was added."
        return None
    source.title = data.code + " — " + data.title
    source.retrieved_at, source.last_checked_at = saved.retrieved_at, saved.last_checked_at
    source.content_hash = saved.content_hash
    source.verification_status = "verified" if check.status in {"updated", "unchanged", "not_modified"} else "stale"
    source.review_note = "Course fields fetched from an official program link. Prerequisites and degree applicability remain unreviewed."
    fields = {key: source.source_id for key in ("title", "summary", "credits", "requirement_reference")}
    record = Record(record_id="uofa:" + data.code + ":" + data.catalog_version, kind="course", code=data.code,
        title=data.title, summary=data.summary, credits=data.credits, catalog_version=data.catalog_version,
        source_ids=[source.source_id, candidate.plan.source.source_id], requirement_reference=data.requirement_reference,
        review_status="source_fetched", study_stage=candidate.plan.study_stage, career_ids=candidate.plan.career_ids,
        field_sources=fields, discovery=CourseOrigin(source_id=candidate.plan.source.source_id,
            program_code=candidate.plan.program_code, section_ids=candidate.sections, course_id=candidate.course_id,
            discovered_at=now or datetime.now(timezone.utc)))
    catalog.sources.append(source)
    catalog.records.append(record)
    return record
