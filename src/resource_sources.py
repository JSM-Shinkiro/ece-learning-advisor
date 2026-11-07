"""Identity-checked introductions from configured official learning resources."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Literal
from urllib.parse import urljoin, urlparse

import httpx
from pydantic import AwareDatetime, Field, model_validator

from .models import Source, SourceCheck, StrictModel
from .planning import requested_resource_ids
from .source_http import SourcePageError, SourceRequest, failure_kind, read_public_page
from .source_reuse import VERIFIED_CHECKS, recent_sources

MAX_RESOURCE_SOURCES = 2
MAX_RESOURCE_CACHE_BYTES = 30_000
RESOURCE_URLS = {
    "resource:pytorch": "https://docs.pytorch.org/tutorials/beginner/basics/quickstart_tutorial.html",
    "resource:cs50": "https://cs50.harvard.edu/x/",
    "resource:python": "https://docs.python.org/3/tutorial/index.html",
    "resource:numpy": "https://numpy.org/doc/stable/user/quickstart.html",
    "resource:sklearn": "https://scikit-learn.org/stable/getting_started.html",
    "resource:pico": "https://www.raspberrypi.com/documentation/microcontrollers/c_sdk.html",
    "resource:mit_algorithms": "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/pages/syllabus/",
    "resource:mit_structures": "https://ocw.mit.edu/courses/6-004-computation-structures-spring-2017/pages/syllabus/",
}


@dataclass(frozen=True)
class OpenCourseSpec:
    number: str
    title: str
    term: str


OPEN_COURSES = {
    "resource:mit_algorithms": OpenCourseSpec("6.006", "Introduction to Algorithms", "Spring 2020"),
    "resource:mit_structures": OpenCourseSpec("6.004", "Computation Structures", "Spring 2017"),
}


@dataclass(frozen=True)
class ResourceSpec:
    title: str
    heading: str
    document_pattern: str
    version_pattern: str
    introduction_section: str | None = None


RESOURCE_SPECS = {
    "resource:python": ResourceSpec("The Python Tutorial", "The Python Tutorial",
        r"The Python Tutorial\s*[—–-]\s*Python (\d+\.\d+\.\d+[A-Za-z0-9.+-]*) documentation", r"\d+\.\d+\.\d+[A-Za-z0-9.+-]*"),
    "resource:numpy": ResourceSpec("NumPy quickstart", "NumPy quickstart",
        r"NumPy quickstart\s*[—–-]\s*NumPy v(\d+\.\d+(?:\.\d+)?[A-Za-z0-9.+-]*) Manual", r"\d+\.\d+(?:\.\d+)?[A-Za-z0-9.+-]*", "Prerequisites"),
    "resource:sklearn": ResourceSpec("scikit-learn Getting Started", "Getting Started",
        r"Getting Started\s*[—–-]\s*scikit-learn (\d+\.\d+\.\d+[A-Za-z0-9.+-]*) documentation", r"\d+\.\d+\.\d+[A-Za-z0-9.+-]*"),
    "resource:pico": ResourceSpec("Raspberry Pi Pico C/C++ SDK", "The C/C++ SDK",
        r"The C/C\+\+ SDK - Raspberry Pi Documentation", r"unversioned documentation", "Raspberry Pi Pico C/C++ SDK"),
}


def resource_url_matches(resource_id, url):
    try:
        parsed = urlparse(url)
        if (parsed.scheme != "https" or parsed.port not in {None, 443}
                or parsed.username or parsed.password or parsed.query or parsed.fragment):
            return False
        return url == RESOURCE_URLS.get(resource_id) or (resource_id == "resource:cs50"
            and parsed.hostname == "cs50.harvard.edu" and re.fullmatch(r"/x/20\d{2}/", parsed.path) is not None)
    except ValueError:
        return False


class ResourceSnapshot(StrictModel):
    resource_id: Literal["resource:pytorch", "resource:cs50", "resource:python", "resource:numpy", "resource:sklearn", "resource:pico",
                         "resource:mit_algorithms", "resource:mit_structures"]
    resolved_url: str
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=40, max_length=1500)
    resource_version: str = Field(min_length=1, max_length=80)

    @model_validator(mode="after")
    def bound_identity(self):
        if not resource_url_matches(self.resource_id, self.resolved_url):
            raise ValueError("The resource snapshot has an unsupported URL")
        if self.resource_id == "resource:pytorch":
            valid = self.title == "PyTorch Quickstart" and re.fullmatch(r"\d+\.\d+\.\d+[A-Za-z0-9.+-]*", self.resource_version)
        elif self.resource_id == "resource:cs50":
            path_year = re.fullmatch(r"/x/(20\d{2})/", urlparse(self.resolved_url).path)
            valid = (self.title.replace("’", "'") == "CS50's Introduction to Computer Science"
                and re.fullmatch(r"20\d{2}", self.resource_version)
                and (path_year is None or path_year[1] == self.resource_version))
        elif self.resource_id in OPEN_COURSES:
            spec = OPEN_COURSES[self.resource_id]
            valid = self.title == "MIT " + spec.number + " — " + spec.title and self.resource_version == spec.term
        else:
            spec = RESOURCE_SPECS[self.resource_id]
            valid = self.title == spec.title and re.fullmatch(spec.version_pattern, self.resource_version)
        if not valid or not self.summary.strip():
            raise ValueError("The resource snapshot identity or version is invalid")
        return self


def resource_hash(data):
    return hashlib.sha256(data.model_dump_json().encode()).hexdigest()


class CachedResource(StrictModel):
    schema_version: Literal[1] = 1
    requested_url: str
    data: ResourceSnapshot
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    retrieved_at: AwareDatetime
    last_checked_at: AwareDatetime
    etag: str | None = Field(default=None, max_length=512)
    last_modified: str | None = Field(default=None, max_length=100)


class _ResourcePage(HTMLParser):
    """Capture visible headings and introductory paragraphs, without scripts/code."""
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, resource_id):
        super().__init__(convert_charrefs=True)
        self.resource_id = resource_id
        self.stack, self.blocks, self.canonicals = [], [], []
        self.capture = None
        self.roots = 0
        self.capture_banner = False
        self.banner_headings, self.banner_terms = [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "br" and self.capture is not None:
            self.capture[1].append(" ")
        parent = self.stack[-1] if self.stack else {"hidden": False, "blocked": False, "root": False}
        style = "".join(attrs.get("style", "").lower().split())
        hidden = (parent["hidden"] or tag in {"script", "style", "noscript", "nav", "footer"}
            or "hidden" in attrs or attrs.get("aria-hidden", "").lower() == "true"
            or "display:none" in style or "visibility:hidden" in style)
        classes = attrs.get("class", "").split()
        blocked = parent["blocked"] or tag in {"aside", "pre"} or any(c in classes for c in ("admonition", "edit-link"))
        banner = parent.get("banner", False) or tag == "div" and attrs.get("id") == "course-banner"
        if self.resource_id in OPEN_COURSES:
            root = tag == "main" and attrs.get("id") == "course-content-section"
        elif self.resource_id == "resource:python":
            root = tag == "div" and "body" in classes and attrs.get("role") == "main"
        elif self.resource_id == "resource:pico":
            root = tag == "section" and attrs.get("id") == "content" and attrs.get("role") == "main"
        elif self.resource_id == "resource:cs50":
            root = tag == "main"
        else:
            root = tag == "article" and "bd-article" in classes
        if root and not hidden:
            self.roots += 1
        context = {"tag": tag, "hidden": hidden, "blocked": blocked, "root": parent["root"] or root, "banner": banner}
        if tag == "link" and not hidden and attrs.get("rel") == "canonical":
            self.canonicals.append(attrs.get("href", ""))
        if tag not in self.VOID:
            self.stack.append(context)
        document_title = tag == "title" and any(node["tag"] == "head" for node in self.stack)
        course_term = (self.resource_id in OPEN_COURSES and banner and tag == "span" and "course-number-term-detail" in classes)
        if (document_title or course_term or tag in {"h1", "h2", "h3", "h4", "p"}) and not hidden:
            if self.capture is not None:
                raise ValueError("The resource content structure is ambiguous")
            if tag != "p" or context["root"] and not blocked:
                self.capture = (tag, [], context["root"] and not blocked)
                self.capture_banner = banner and not blocked
        if len(self.stack) > 100 or len(self.blocks) > 2000 or self.roots > 1:
            raise ValueError("The resource page exceeds the parser limits")

    def handle_data(self, data):
        if self.capture is not None and not (self.stack and self.stack[-1]["hidden"]):
            self.capture[1].append(data)
            if sum(map(len, self.capture[1])) > 10000:
                raise ValueError("The resource content block is oversized")

    def handle_endtag(self, tag):
        if self.capture is not None and self.capture[0] == tag:
            kind, parts, in_body = self.capture
            text = " ".join("".join(parts).split()).rstrip("#¶").strip()
            self.blocks.append((kind, text, in_body))
            if self.capture_banner and kind == "h1":
                self.banner_headings.append(text)
            if self.capture_banner and kind == "span":
                self.banner_terms.append(text)
            self.capture = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                break


def extract_resource(page, resource_id, resolved_url):
    if not resource_url_matches(resource_id, resolved_url):
        raise ValueError("The resource URL is unsupported")
    parser = _ResourcePage(resource_id)
    parser.feed(page)
    parser.close()
    titles = [text for tag, text, _ in parser.blocks if tag == "title"]
    if parser.roots != 1 or len(titles) != 1:
        raise ValueError("The resource main content or document identity is missing")
    for canonical in parser.canonicals:
        if urljoin(resolved_url, canonical) != resolved_url:
            raise ValueError("The resource canonical identity does not match")
    open_course = OPEN_COURSES.get(resource_id)
    heading_tag = "h1"
    if open_course:
        expected_title = "Syllabus | " + open_course.title + " | Electrical Engineering and Computer Science | MIT OpenCourseWare"
        if (titles[0] != expected_title or parser.banner_headings != [open_course.title]
                or parser.banner_terms != [open_course.number + " | " + open_course.term + " | Undergraduate"]):
            raise ValueError("The open course title, number, or teaching term does not match")
        match, heading_tag, heading = True, "h3", "Course Description"
        title = "MIT " + open_course.number + " — " + open_course.title
    elif resource_id == "resource:pytorch":
        match = re.fullmatch(r"Quickstart\s*[—–-]\s*PyTorch Tutorials (\d+\.\d+\.\d+[A-Za-z0-9.+-]*) documentation", titles[0])
        heading, title = "Quickstart", "PyTorch Quickstart"
    elif resource_id == "resource:cs50":
        match = re.fullmatch(r"CS50x (20\d{2})", titles[0])
        heading = "Welcome"
        titles2 = [text for tag, text, _ in parser.blocks if tag == "h2"
                   and text.replace("’", "'") == "CS50's Introduction to Computer Science"]
        if len(titles2) != 1:
            raise ValueError("The CS50 course identity does not match")
        title = titles2[0]
    else:
        spec = RESOURCE_SPECS[resource_id]
        match = re.fullmatch(spec.document_pattern, titles[0])
        heading, title = spec.heading, spec.title
    if not match:
        raise ValueError("The resource document identity or edition is unsupported")
    starts = [index for index, (tag, text, body) in enumerate(parser.blocks) if body and tag == heading_tag and text == heading]
    if len(starts) != 1:
        raise ValueError("The resource introduction is missing or ambiguous")
    start = starts[0]
    spec = RESOURCE_SPECS.get(resource_id)
    if spec and spec.introduction_section:
        sections = [index for index, (tag, text, body) in enumerate(parser.blocks)
                    if index > start and body and tag == "h2" and text == spec.introduction_section]
        if len(sections) != 1:
            raise ValueError("The resource introductory section is missing or ambiguous")
        start = sections[0]
    paragraphs = []
    for tag, text, body in parser.blocks[start + 1:]:
        if body and tag in {"h1", "h2", "h3", "h4"}:
            break
        if body and tag == "p" and len(text) >= 40 and not text.startswith(("Created On:", "Last Updated:", "Last Verified:")):
            if len(" ".join(paragraphs + [text])) > 1500:
                break
            paragraphs.append(text)
            if len(paragraphs) == 2:
                break
    version = open_course.term if open_course else "unversioned documentation" if resource_id == "resource:pico" else match[1]
    return ResourceSnapshot(resource_id=resource_id, resolved_url=resolved_url, title=title,
        summary=" ".join(paragraphs), resource_version=version)


@dataclass
class ResourceJob:
    record_id: str
    source: Source


def prepare_resource_jobs(catalog, profile, now=None):
    sources = {s.source_id: s for s in catalog.sources}
    jobs, checks = [], []
    records = [record for record in catalog.records if record.kind == "resource"
        and (not record.career_ids or profile.career_id == "exploring" or profile.career_id in record.career_ids)]
    # Whole phrases in the explicit question (or interests when no question)
    # select checks before the stable default order. The cap remains two.
    preferred = {rid: index for index, rid in enumerate(requested_resource_ids(catalog, profile))}
    records.sort(key=lambda record: preferred.get(record.record_id, len(preferred)))
    for record in records:
        source = sources[record.source_ids[0]]
        unsupported = (record.record_id not in RESOURCE_URLS or source.source_id != record.record_id
                       or not resource_url_matches(record.record_id, source.url))
        if unsupported or len(jobs) >= MAX_RESOURCE_SOURCES:
            checks.append(SourceCheck(source_id=source.source_id, code=record.record_id, url=source.url,
                kind="resource", status="skipped", attempted_at=now or datetime.now(timezone.utc),
                retrieved_at=source.retrieved_at, message=("The resource identity is unsupported; retaining dated evidence." if unsupported else
                    "The resource-check limit was reached; remaining resources retain dated snapshots.")))
            continue
        jobs.append(ResourceJob(record.record_id, source.model_copy(deep=True)))
    return jobs, checks


def _cache_path(directory, job):
    identity = json.dumps([job.record_id, RESOURCE_URLS[job.record_id], 1])
    return Path(directory) / "resources" / (hashlib.sha256(identity.encode()).hexdigest() + ".json")


def _read(path, job):
    try:
        if path.stat().st_size > MAX_RESOURCE_CACHE_BYTES:
            return None
        saved = CachedResource.model_validate_json(path.read_bytes())
        if (saved.requested_url != RESOURCE_URLS[job.record_id] or saved.data.resource_id != job.record_id
                or saved.content_hash != resource_hash(saved.data) or saved.last_checked_at < saved.retrieved_at):
            return None
        return saved
    except (OSError, ValueError):
        return None


def _write(path, saved):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix="resource-source-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(saved.model_dump_json())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _download(client, job, cached, request):
    requested = RESOURCE_URLS[job.record_id]
    def headers(url):
        result = {"User-Agent": "ECE-Learning-Advisor/0.2", "Accept": "text/html"}
        if cached and cached.data.resolved_url == url:
            if cached.etag:
                result["If-None-Match"] = cached.etag
            if cached.last_modified:
                result["If-Modified-Since"] = cached.last_modified
        return result
    try:
        return read_public_page(client, requested, headers(requested), request=request), requested
    except SourcePageError as exc:
        target = urljoin(requested, exc.location or "")
        if (job.record_id != "resource:cs50" or exc.http_status not in {301, 302, 307, 308}
                or target == requested or not resource_url_matches(job.record_id, target)):
            raise
        return read_public_page(client, target, headers(target), request=request), target


def fetch_resource_source(job, directory, client, now=None, reuse_seconds=0):
    request = SourceRequest()
    requested = RESOURCE_URLS[job.record_id]
    check = SourceCheck(source_id=job.source.source_id, code=job.record_id, url=requested, kind="resource",
        status="bundled_fallback", attempted_at=now or datetime.now(timezone.utc),
        retrieved_at=job.source.retrieved_at, last_checked_at=job.source.last_checked_at)
    cached = None
    path = _cache_path(directory, job)
    try:
        if job.source.source_id != job.record_id or not resource_url_matches(job.record_id, job.source.url):
            raise ValueError("The resource source binding is unsupported")
        cached = _read(path, job)
        if recent_sources.reuse(path, cached, check, reuse_seconds):
            check.resolved_url = cached.data.resolved_url
            return cached, check
        page, resolved = _download(client, job, cached, request)
        check.http_status, check.resolved_url = page.status, resolved
        checked = now or datetime.now(timezone.utc)
        if page.status == 304:
            if cached is None or cached.data.resolved_url != resolved:
                raise ValueError("A not-modified resource response needs a matching cache")
            saved = cached.model_copy(update={"last_checked_at": checked})
            check.status = "not_modified"
        else:
            data = extract_resource(page.text, job.record_id, resolved)
            saved = CachedResource(requested_url=requested, data=data, content_hash=resource_hash(data),
                retrieved_at=checked, last_checked_at=checked, etag=page.etag, last_modified=page.last_modified)
            check.content_changed = cached is None or saved.content_hash != cached.content_hash
            check.status = "updated" if check.content_changed else "unchanged"
        try:
            _write(path, saved)
            check.cache_saved = True
            recent_sources.remember(path, saved)
        except OSError:
            check.message = "Fresh resource evidence was fetched, but its cache could not be saved."
        check.retrieved_at, check.last_checked_at = saved.retrieved_at, saved.last_checked_at
        check.content_hash = saved.content_hash
        return saved, check
    except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
        recent_sources.forget(path)
        check.http_status = getattr(exc, "http_status", check.http_status)
        check.failure_kind = failure_kind(exc, check.http_status)
        check.status = "stale_cache" if cached else "bundled_fallback"
        check.message = f"{job.record_id}: resource check failed; showing dated saved evidence."
        if cached:
            check.retrieved_at, check.last_checked_at = cached.retrieved_at, cached.last_checked_at
            check.content_hash, check.resolved_url = cached.content_hash, cached.data.resolved_url
        return cached, check
    finally:
        request.apply(check)


def apply_resource_source(catalog, job, saved, check):
    source = next(s for s in catalog.sources if s.source_id == job.source.source_id)
    source.verification_status = "verified" if check.status in VERIFIED_CHECKS else "stale"
    if saved is None:
        return
    record = next(r for r in catalog.records if r.record_id == job.record_id)
    record.title, record.summary, record.resource_version = saved.data.title, saved.data.summary, saved.data.resource_version
    record.field_sources = {key: source.source_id for key in ("title", "summary", "resource_version")}
    record.review_status = "source_fetched"
    source.url, source.title = saved.data.resolved_url, saved.data.title
    source.retrieved_at, source.last_checked_at = saved.retrieved_at, saved.last_checked_at
    source.content_hash = saved.content_hash
    source.review_note = "Introductory resource excerpt fetched and identity checked. Version: " + saved.data.resource_version + ". Complementary study, not university credit."
