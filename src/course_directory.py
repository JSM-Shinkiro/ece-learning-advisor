"""Published ECE inventory, separate from the reviewed advisor/evaluation corpus."""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

from pydantic import Field, model_validator

from .ingest import description_text
from .models import Record, Source, StrictModel

DEFAULT_DIRECTORY = Path(__file__).resolve().parents[1] / "data/catalog/undergraduate_ece_2026_2027.json"
MAX_REQUESTED_COURSES = 3
COURSE_LIST_URL = "https://catalog.arizona.edu/courses"
SEARCH_URL = "https://app.coursedog.com/api/v1/cm/arizona_peoplesoft/courses/search/%24filters"


def json_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class DirectoryCourse(StrictModel):
    code: str = Field(pattern=r"^ECE[1-4]\d{2}[A-Z]{0,2}$")
    course_id: str = Field(pattern=r"^\d{7}$")
    title: str = Field(min_length=1, max_length=500)
    summary: str = Field(min_length=1, max_length=7000)
    credits_min: float = Field(ge=0, le=30, strict=True)
    credits_max: float = Field(ge=0, le=30, strict=True)
    requirement_reference: str | None = Field(default=None, pattern=r"^\d{1,12}$")
    effective_start: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    metadata_hash: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def credit_range(self):
        if self.credits_min > self.credits_max:
            raise ValueError("Reversed course credit range")
        return self

    @property
    def url(self):
        return "https://catalog.arizona.edu/courses/" + self.course_id

    @property
    def credits_label(self):
        if self.credits_min == self.credits_max:
            return f"{self.credits_min:g} credits"
        return f"{self.credits_min:g}–{self.credits_max:g} credits"


class InventoryPage(StrictModel):
    skip: int = Field(ge=0)
    received: int = Field(ge=1, le=100)
    response_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class CourseDirectory(StrictModel):
    version: str
    catalog_version: str = Field(pattern=r"^20\d{2}-20\d{2}$")
    catalog_id: str = Field(min_length=1, max_length=100)
    effective_dates: str = Field(pattern=r"^\d{4}-\d{2}-\d{2},\d{4}-\d{2}-\d{2}$")
    retrieved_at: datetime
    source_url: str = COURSE_LIST_URL
    search_url: str = SEARCH_URL
    filters_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    published_ece_total: int = Field(ge=1, le=1000)
    excluded_non_undergraduate: int = Field(ge=0)
    pages: list[InventoryPage] = Field(min_length=1, max_length=10)
    courses: list[DirectoryCourse] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def complete_inventory(self):
        if (self.source_url != COURSE_LIST_URL or self.search_url != SEARCH_URL
                or self.retrieved_at.tzinfo is None):
            raise ValueError("Directory source or retrieval time is invalid")
        count = 0
        for page in self.pages:
            if page.skip != count:
                raise ValueError("Missing or overlapping inventory page")
            count += page.received
        if count != self.published_ece_total or count != len(self.courses) + self.excluded_non_undergraduate:
            raise ValueError("Inventory is incomplete")
        for key in ("code", "course_id"):
            if len({getattr(c, key) for c in self.courses}) != len(self.courses):
                raise ValueError("Duplicate directory identity")
        return self


@lru_cache(maxsize=4)
def load_course_directory(path=DEFAULT_DIRECTORY):
    """Read the shipped snapshot once per process; no network or embeddings."""
    return CourseDirectory.model_validate_json(Path(path).read_text(encoding="utf-8"))


def build_directory(pages, *, catalog_version, catalog_id, effective_dates, retrieved_at, filters):
    """Reject partial, drifting, duplicate or out-of-subject search results."""
    courses, manifest, seen = [], [], set()
    total, offset, excluded = None, 0, 0
    for page in pages:
        if total is None:
            total = page["listLength"]
        data = page["data"]
        if (page["listLength"] != total or page["skip"] != offset or not data
                or len(data) > 100 or any(not isinstance(x, dict) for x in data)):
            raise ValueError("Unstable or incomplete course search")
        manifest.append(InventoryPage(skip=offset, received=len(data), response_hash=json_hash(page)))
        offset += len(data)
        for item in data:
            identity = item.get("courseGroupId")
            if (item.get("subjectCode") != "ECE" or item.get("status") != "Active"
                    or item.get("catalogPrint") is not True or item.get("courseApproved") != "Approved"
                    or not identity or identity in seen):
                raise ValueError("Unexpected or duplicate published course")
            seen.add(identity)
            if item.get("career") != "Undergraduate":
                if not re.fullmatch(r"ECE[5-9]\d{2}[A-Z]{0,2}", item.get("code", "")):
                    raise ValueError("Unexpected course career/number")
                excluded += 1
                continue
            credit = item["credits"]["creditHours"]
            courses.append(DirectoryCourse(code=item["code"], course_id=identity,
                title=item["longName"], summary=description_text(item["description"]),
                credits_min=credit["min"], credits_max=credit["max"],
                requirement_reference=item.get("requirementGroup") or None,
                effective_start=item["effectiveStartDate"], metadata_hash=json_hash({
                    k:item.get(k) for k in ("code", "courseGroupId", "longName", "description", "credits",
                                           "career", "requirementGroup", "effectiveStartDate")})))
    return CourseDirectory(version="ece-undergraduate-directory-v1", catalog_version=catalog_version,
        catalog_id=catalog_id, effective_dates=effective_dates, retrieved_at=retrieved_at,
        filters_hash=json_hash(filters), published_ece_total=total,
        excluded_non_undergraduate=excluded, pages=manifest, courses=sorted(courses, key=lambda c:c.code))


def filter_directory(directory, query="", level="all"):
    query = re.sub(r"\b(ECE)\s+(\d{3}[A-Z]{0,2})\b", r"\1\2", query, flags=re.I)
    if re.fullmatch(r"ECE[1-4]\d{2}[A-Z]{0,2}", query.strip(), flags=re.I):
        return [c for c in directory.courses if c.code == query.strip().upper()
                and (level == "all" or c.code[3] == level)]
    terms = query.casefold().split()
    return [c for c in directory.courses if (level == "all" or c.code[3] == level)
            and all(term in (c.code+" "+c.title+" "+c.summary).casefold() for term in terms)]


def add_requested_courses(catalog, directory, profile):
    """Promote only explicitly requested, unrecorded courses; leave baseline untouched."""
    text = profile.question.strip() or profile.interests
    requested = list(dict.fromkeys(re.sub(r"\s+", "", c).upper()
        for c in re.findall(r"\bECE\s*[1-4]\d{2}[A-Z]{0,2}\b", text, flags=re.I)))
    trace = {"limit": MAX_REQUESTED_COURSES, "requested": requested, "added": [], "omitted": []}
    if profile.catalog_version != directory.catalog_version or catalog.catalog_version != directory.catalog_version:
        trace["reason"] = "different_catalog_edition"
        return catalog, trace
    known = {r.code for r in catalog.records if r.kind == "course"}
    recorded = {c.course_code for c in profile.completed} | set(profile.current_enrollment)
    lookup = {c.code:c for c in directory.courses}
    selected = [lookup[code] for code in requested if code in lookup and code not in known | recorded]
    trace["omitted"] = [c.code for c in selected[MAX_REQUESTED_COURSES:]]
    if not selected:
        return catalog, trace
    active = catalog.model_copy(deep=True)
    for course in selected[:MAX_REQUESTED_COURSES]:
        sid = "catalog:" + course.code
        summary = course.summary
        variable = course.credits_min != course.credits_max
        if variable:
            summary = f"Published credit range: {course.credits_label}. " + summary
        active.sources.append(Source(source_id=sid, title=course.code+" official catalog", url=course.url,
            catalog_version=directory.catalog_version, retrieved_at=directory.retrieved_at,
            section="Published course description", content_hash=course.metadata_hash,
            review_note="Published catalog inventory snapshot. Enrollment conditions and career mapping are unreviewed."))
        active.records.append(Record(record_id=f"uofa:{course.code}:{directory.catalog_version}",
            kind="course", code=course.code, title=course.title, summary=summary, source_ids=[sid],
            credits=None if variable else course.credits_min, catalog_version=directory.catalog_version,
            requirement_reference=course.requirement_reference, review_status="source_fetched",
            study_stage="unreviewed", field_sources={k:sid for k in
                ("title", "summary", "credits", "requirement_reference")}))
        trace["added"].append(course.code)
    # Catalog validation checks unique IDs and field/source ownership.
    return type(catalog).model_validate(active.model_dump()), trace
