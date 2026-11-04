"""Data contracts shared by the UI, retrieval, and providers."""

from __future__ import annotations

import re
import hashlib
import json
from datetime import datetime
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def normalize_code(value: str) -> str:
    return re.sub(r"\s+", "", value).upper()


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Rule(StrictModel):
    type: Literal[
        "all_of", "any_of", "completed", "completed_or_concurrent",
        "standing", "consent", "unknown", "none"
    ]
    children: list[Rule] = Field(default_factory=list)
    course_code: str | None = None
    minimum_grade: str | None = None
    value: str | None = None
    note: str = ""
    evidence_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def valid_node(self):
        if self.type in {"all_of", "any_of"} and not self.children:
            raise ValueError("Logical rules require children")
        if self.type not in {"all_of", "any_of"} and self.children:
            raise ValueError("Leaf rules cannot contain children")
        if self.type in {"completed", "completed_or_concurrent"} and not self.course_code:
            raise ValueError("Course condition needs a course code")
        if self.type == "standing" and not self.value:
            raise ValueError("Standing condition needs a value")
        if self.course_code:
            self.course_code = normalize_code(self.course_code)
        return self


def rule_hash(rule: Rule) -> str:
    payload = json.dumps(rule.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def rule_citation_ids(rule: Rule) -> set[str]:
    return set(rule.evidence_ids).union(*(rule_citation_ids(child) for child in rule.children))


def statement_hash(text: str) -> str:
    return hashlib.sha256(" ".join(text.split()).encode()).hexdigest()


def program_source_url_matches(url: str, program_code: str) -> bool:
    try:
        p = urlparse(url)
        return bool(p.scheme == "https" and p.hostname == "catalog.arizona.edu" and p.port in {None, 443}
            and not (p.username or p.password or p.query or p.fragment)
            and re.fullmatch(r"/programs/" + re.escape(program_code) + r"/program-requirements-[A-Za-z0-9]+", p.path))
    except ValueError:
        return False


class RuleEvidence(StrictModel):
    evidence_id: str
    source_id: str
    course_code: str
    program_code: str = Field(pattern=r"^[A-Z][A-Z0-9]{1,20}$")
    section_id: str = Field(pattern=r"^R\d+/L?\d+$")
    catalog_version: str
    reviewed_text: str = Field(min_length=1, max_length=3000)
    statement_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    rule_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    reviewed_at: datetime
    observed_text: str | None = Field(default=None, min_length=1, max_length=3000)
    verification_status: Literal["snapshot", "verified", "stale", "changed", "unavailable", "unsupported"] = "snapshot"

    @model_validator(mode="after")
    def reviewed_statement_matches(self):
        if statement_hash(self.reviewed_text) != self.statement_hash:
            raise ValueError("Reviewed rule statement does not match its fingerprint")
        return self


class Completion(StrictModel):
    course_code: str
    grade: str | None = None

    @field_validator("course_code")
    @classmethod
    def valid_code(cls, value):
        value = normalize_code(value)
        if not re.fullmatch(r"[A-Z]{2,8}\d{3}[A-Z]{0,2}", value):
            raise ValueError("Use a course code such as ECE101")
        return value

    @field_validator("grade")
    @classmethod
    def valid_grade(cls, value):
        if value is None or not value.strip():
            return None
        value = value.strip().upper()
        if value in {"E", "F"}:
            raise ValueError("Failed attempts cannot be listed as completed coursework. Remove the course or enter a passing grade.")
        if value not in {"A", "B", "C", "D", "E", "F", "P", "S", "CR", "A+", "A-", "B+", "B-", "C+", "C-", "D+", "D-"}:
            raise ValueError("Unsupported grade")
        return value


class StudentProfile(StrictModel):
    schema_version: Literal[1] = 1
    standing: Literal["Incoming", "Freshman", "Sophomore", "Junior", "Senior", "Other"] = "Incoming"
    catalog_version: str = Field(default="2026-2027", max_length=40)
    career_id: Literal["ai_ml", "embedded", "exploring"] = "ai_ml"
    interests: str = Field(default="", max_length=1500)
    experience: str = Field(default="", max_length=2000)
    question: str = Field(default="", max_length=1200)
    completed: list[Completion] = Field(default_factory=list, max_length=200)
    history_complete: bool = False
    programming_background: Literal["new", "some", "experienced"] = "new"
    current_enrollment: list[str] = Field(default_factory=list, max_length=100)
    consents: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def unique_courses(self):
        codes = [x.course_code for x in self.completed]
        if len(codes) != len(set(codes)):
            raise ValueError("List each completed course once")
        self.current_enrollment = [normalize_code(x) for x in self.current_enrollment]
        return self


class SourceFreshness(StrictModel):
    verification_status: Literal["snapshot", "verified", "stale"] = "snapshot"
    retrieved_at: datetime
    last_checked_at: datetime | None = None


class Source(SourceFreshness):
    source_id: str
    title: str
    url: str
    catalog_version: str | None = None
    section: str = ""
    review_note: str = ""
    content_hash: str | None = None

    @field_validator("url")
    @classmethod
    def safe_url(cls, value):
        if not value.startswith("https://"):
            raise ValueError("Source URLs must use HTTPS")
        return value


class SourceCheck(StrictModel):
    source_id: str
    code: str
    url: str
    kind: Literal["course", "rule"] = "course"
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
    rule_status: Literal["verified", "stale", "changed", "unavailable", "unsupported", "unreviewed"] | None = None
    message: str = ""


class Record(StrictModel):
    record_id: str
    kind: Literal["course", "resource", "career"]
    title: str
    summary: str = Field(min_length=1, max_length=7000)
    source_ids: list[str] = Field(min_length=1)
    code: str | None = None
    credits: float | None = Field(default=None, ge=0, le=30)
    catalog_version: str | None = None
    rule: Rule = Field(default_factory=lambda: Rule(type="unknown"))
    rule_reviewed: bool = False
    rule_evidence: list[RuleEvidence] = Field(default_factory=list, max_length=8)
    rule_verification: Literal["snapshot", "verified", "stale", "changed", "unavailable", "unsupported"] = "snapshot"
    topics: list[str] = Field(default_factory=list)
    review_status: Literal["source_summary_reviewed", "source_fetched", "team_mapping", "synthetic_fixture"] = "source_summary_reviewed"
    requirement_reference: str | None = None
    study_stage: Literal["foundation", "intermediate", "advanced"] = "intermediate"
    career_ids: list[Literal["ai_ml", "embedded"]] = Field(default_factory=list)
    learning_note: str = Field(default="", max_length=1200)
    first_activity: str = Field(default="", max_length=600)

    @field_validator("code")
    @classmethod
    def canonical_code(cls, value):
        return normalize_code(value) if value else None


def rule_binding_matches(record: Record) -> bool:
    return rule_citation_ids(record.rule) <= {p.evidence_id for p in record.rule_evidence} and all(
               proof.course_code == record.code and proof.catalog_version == record.catalog_version
               and proof.source_id in record.source_ids and proof.rule_hash == rule_hash(record.rule)
               and proof.statement_hash == statement_hash(proof.reviewed_text)
               for proof in record.rule_evidence)


class Catalog(StrictModel):
    version: str
    catalog_version: str
    sources: list[Source]
    records: list[Record]

    @model_validator(mode="after")
    def references_exist(self):
        sources = {s.source_id for s in self.sources}
        ids = [r.record_id for r in self.records]
        if len(ids) != len(set(ids)) or len(sources) != len(self.sources):
            raise ValueError("Duplicate catalog identity")
        for record in self.records:
            if not set(record.source_ids) <= sources:
                raise ValueError("Record has an unknown source")
            for proof in record.rule_evidence:
                reference_source = next((s for s in self.sources if s.source_id == proof.source_id), None)
                if (proof.source_id not in record.source_ids or proof.course_code != record.code
                        or proof.catalog_version != record.catalog_version
                        or not proof.evidence_id.startswith(record.record_id + ":rule:")
                        or reference_source is None or reference_source.catalog_version != proof.catalog_version
                        or not program_source_url_matches(reference_source.url, proof.program_code)):
                    raise ValueError("Rule provenance does not match its course and source")
                if record.rule_reviewed and proof.rule_hash != rule_hash(record.rule):
                    raise ValueError("Reviewed rule interpretation does not match its provenance")
            if record.rule_evidence and record.rule_reviewed and not rule_binding_matches(record):
                raise ValueError("Reviewed rule interpretation and citations do not match their provenance")
        evidence_ids = [p.evidence_id for r in self.records for p in r.rule_evidence]
        if len(evidence_ids) != len(set(evidence_ids)) or set(evidence_ids) & {r.record_id + ":overview" for r in self.records}:
            raise ValueError("Duplicate rule evidence identity")
        return self


class Evidence(StrictModel):
    chunk_id: str
    record_id: str
    source_ids: list[str]
    text: str


class RuleEvaluation(StrictModel):
    status: Literal["satisfied", "unsatisfied", "unknown"]
    reasons: list[str]
    evidence_ids: list[str] = Field(default_factory=list)
    verification_status: Literal["snapshot", "verified", "stale", "changed", "unavailable", "unsupported", "unreviewed"] | None = None
    source_ids: list[str] = Field(default_factory=list)


class Reason(StrictModel):
    text: str = Field(min_length=1, max_length=1400)
    claim_type: Literal["source_fact", "recommendation"]
    evidence_ids: list[str] = Field(min_length=1, max_length=8)


class Recommendation(StrictModel):
    record_id: str
    reasons: list[Reason] = Field(min_length=1, max_length=4)


class GeneratedAnswer(StrictModel):
    status: Literal["answered", "insufficient_evidence"]
    recommendations: list[Recommendation] = Field(default_factory=list, max_length=5)
    clarification: str | None = Field(default=None, max_length=1500)

    @model_validator(mode="after")
    def coherent_answer(self):
        if self.status == "answered" and not self.recommendations:
            raise ValueError("An answered response needs recommendations")
        if self.status == "insufficient_evidence" and (self.recommendations or not self.clarification):
            raise ValueError("Insufficient evidence needs a clarification and no recommendations")
        return self


class GenerationContext(StrictModel):
    profile: StudentProfile
    question: str
    query: str
    allowed_record_ids: list[str]
    evidence: list[Evidence]
    rule_results: dict[str, RuleEvaluation]
    source_freshness: dict[str, SourceFreshness] = Field(default_factory=dict)
    suggested_phases: dict[str, Literal["next", "build", "later"]] = Field(default_factory=dict)
    prompt_version: str = "p07-v4-rule-provenance"

    def to_prompt(self) -> str:
        return self.model_dump_json(indent=2)
