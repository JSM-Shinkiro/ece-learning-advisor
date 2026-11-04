"""HTTP fixtures exercise live-source orchestration without public network calls."""

import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from src.catalog import build_evidence, corpus_hash
from src.controller import run_advisor
from src.models import Catalog, Rule, StudentProfile
from src.providers import EmbeddingCache
from src.sources import MAX_PAGE_BYTES, refresh_catalog

NOW = datetime(2026, 11, 4, 3, tzinfo=timezone.utc)


def course_page(record, *, edition="2026-2027", code=None, summary=None, reference=None,
                variable_credits=False, unit_range=None, course_id=None):
    table = []

    def ref(value):
        table.append(value)
        return len(table) - 1

    minimum, maximum = unit_range if unit_range is not None else (
        record.credits, record.credits + 1 if variable_credits else record.credits)
    hours = ref({"min": ref(minimum), "max": ref(maximum)})
    identity_fields = {"courseGroupId": ref(course_id)} if course_id is not None else {}
    table.append({"code": ref(code or record.code), "longName": ref(record.title + " (HTTP fixture)"),
                  **identity_fields,
                  "description": ref(summary or f"<p>Fixture source text for {record.code}: programming and hardware.</p>"),
                  "credits": ref({"creditHours": hours}),
                  "requirementGroup": ref(reference or record.requirement_reference)})
    if edition:
        table.append({"activeCatalog": ref("fixture-catalog-id"),
                      "catalogDisplayName": ref(edition + " University of Arizona Catalog")})
    return '<script id="__NUXT_DATA__" type="application/json">' + json.dumps(table).replace("<", r"\u003c") + "</script>"


@pytest.fixture
def one_course(catalog):
    course = next(r for r in catalog.records if r.code == "ECE101")
    source = next(s for s in catalog.sources if s.source_id == "catalog:ECE101")
    return Catalog(version=catalog.version, catalog_version=catalog.catalog_version,
                   records=[course.model_copy(deep=True)], sources=[source.model_copy(deep=True)])


def fixture_client(catalog, seen=None, overrides=None, headers=None):
    pages = {next(s.url for s in catalog.sources if s.source_id == r.source_ids[0]): r
             for r in catalog.records if r.kind == "course"}

    def respond(request):
        record = pages[str(request.url)]
        if seen is not None:
            seen.append(record.code)
        content = (overrides or {}).get(record.code, course_page(record))
        return httpx.Response(200, text=content,
                              headers={"Content-Type": "text/html", **(headers or {})})

    return httpx.Client(transport=httpx.MockTransport(respond))


def test_fetched_fields_are_used_without_mutating_reviewed_input(one_course, tmp_path):
    before = one_course.model_dump_json()
    with fixture_client(one_course) as client:
        result = refresh_catalog(one_course, StudentProfile(), client=client, cache_dir=tmp_path, now=NOW)
    assert result.checks[0].status == "updated"
    assert result.checks[0].cache_saved
    assert "HTTP fixture" in result.catalog.records[0].title
    assert result.catalog.sources[0].verification_status == "verified"
    assert result.catalog.sources[0].last_checked_at == NOW
    assert result.catalog.sources[0].retrieved_at == NOW
    assert result.catalog.records[0].rule_reviewed is False
    assert one_course.model_dump_json() == before
    saved = next(tmp_path.glob("*.json")).read_text()
    assert "__NUXT_DATA__" not in saved and "Fixture source text" in saved


def test_controller_sends_fetched_evidence_and_freshness_to_generator(one_course, fake_provider, tmp_path):
    fake_provider.close = lambda: None
    with fixture_client(one_course) as client:
        def refresh(catalog, profile, **kwargs):
            return refresh_catalog(catalog, profile, client=client, now=NOW, **kwargs)

        result = run_advisor(one_course, StudentProfile(), use_ai=True, api_key="fixture",
                             provider_factory=lambda *a, **k: fake_provider,
                             source_refresher=refresh, cache_dir=tmp_path / "vectors",
                             source_cache_dir=tmp_path / "sources")
    assert result.generation_complete
    assert "Fixture source text" in fake_provider.context.evidence[0].text
    status = fake_provider.context.source_freshness["catalog:ECE101"]
    assert status.verification_status == "verified" and status.last_checked_at == NOW
    assert result.catalog.records[0].title.endswith("(HTTP fixture)")
    assert result.trace["source_refresh"]["checks"][0]["status"] == "updated"
    assert result.timings["total"] >= result.timings["source_refresh"]


def test_conditional_request_advances_check_time_without_download_or_reembedding(one_course, fake_provider, tmp_path):
    with fixture_client(one_course, headers={"ETag": '"fixture-v1"', "Last-Modified": "Tue, 03 Nov 2026 20:00:00 GMT"}) as client:
        first = refresh_catalog(one_course, StudentProfile(), client=client, cache_dir=tmp_path / "sources", now=NOW)
    cache = EmbeddingCache(tmp_path / "vectors")
    cache.get(first.catalog, build_evidence(first.catalog), fake_provider)
    calls = fake_provider.document_calls

    def unchanged(request):
        assert request.headers["if-none-match"] == '"fixture-v1"'
        assert "if-modified-since" in request.headers
        return httpx.Response(304)

    with httpx.Client(transport=httpx.MockTransport(unchanged)) as client:
        second = refresh_catalog(one_course, StudentProfile(), client=client,
                                 cache_dir=tmp_path / "sources", now=NOW + timedelta(hours=1))
    assert second.checks[0].status == "not_modified"
    assert second.catalog.sources[0].retrieved_at == NOW
    assert second.catalog.sources[0].last_checked_at == NOW + timedelta(hours=1)
    assert corpus_hash(first.catalog) == corpus_hash(second.catalog)
    assert cache.get(second.catalog, build_evidence(second.catalog), fake_provider)[1] == "hit"
    assert fake_provider.document_calls == calls


def test_unchanged_200_updates_download_time_but_keeps_index_identity(one_course, tmp_path):
    with fixture_client(one_course) as client:
        first = refresh_catalog(one_course, StudentProfile(), client=client, cache_dir=tmp_path, now=NOW)
        second = refresh_catalog(one_course, StudentProfile(), client=client, cache_dir=tmp_path,
                                 now=NOW + timedelta(hours=1))
    assert second.checks[0].status == "unchanged"
    assert second.catalog.sources[0].retrieved_at > first.catalog.sources[0].retrieved_at
    assert corpus_hash(first.catalog) == corpus_hash(second.catalog)


def test_one_changed_course_reuses_every_other_document_vector(catalog, fake_provider, tmp_path):
    profile = StudentProfile(career_id="exploring")
    with fixture_client(catalog) as client:
        first = refresh_catalog(catalog, profile, client=client, cache_dir=tmp_path / "sources", now=NOW)
    cache = EmbeddingCache(tmp_path / "vectors")
    cache.get(first.catalog, build_evidence(first.catalog), fake_provider)
    calls = fake_provider.document_calls
    record = next(r for r in catalog.records if r.code == "ECE101")
    override = {"ECE101": course_page(record, summary="Fixture source revision: embedded systems practice.")}
    with fixture_client(catalog, overrides=override) as client:
        second = refresh_catalog(catalog, profile, client=client, cache_dir=tmp_path / "sources", now=NOW)
    assert sum(c.content_changed for c in second.checks) == 1
    assert cache.get(second.catalog, build_evidence(second.catalog), fake_provider)[1] == "miss"
    assert fake_provider.document_calls == calls + 1


@pytest.mark.parametrize("failure", [404, 429, 503, "timeout", "format", "redirect", "type", "large", "stream_large", "unexpected_304"])
def test_failed_check_uses_dated_bundle_and_sanitized_issue(one_course, tmp_path, failure):
    def fail(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("private transport detail", request=request)
        if failure == "format":
            return httpx.Response(200, text="<html>changed layout</html>", headers={"Content-Type": "text/html"})
        if failure == "redirect":
            return httpx.Response(302, headers={"Location": "https://unapproved.example/course"})
        if failure == "type":
            return httpx.Response(200, content=b"not html", headers={"Content-Type": "image/png"})
        if failure == "large":
            return httpx.Response(200, headers={"Content-Type": "text/html", "Content-Length": str(MAX_PAGE_BYTES + 1)})
        if failure == "stream_large":
            return httpx.Response(200, stream=httpx.ByteStream(b"x" * (MAX_PAGE_BYTES + 1)), headers={"Content-Type": "text/html"})
        return httpx.Response(304 if failure == "unexpected_304" else failure)

    with httpx.Client(transport=httpx.MockTransport(fail)) as client:
        result = refresh_catalog(one_course, StudentProfile(), client=client, cache_dir=tmp_path, now=NOW)
    assert result.checks[0].status == "bundled_fallback"
    assert result.catalog.records[0].summary == one_course.records[0].summary
    assert result.catalog.sources[0].retrieved_at == one_course.sources[0].retrieved_at
    assert result.catalog.sources[0].last_checked_at is None
    assert result.catalog.sources[0].verification_status == "stale"
    assert result.issues and "private transport detail" not in str(result.issues)
    expected = "timeout" if failure == "timeout" else "response" if isinstance(failure, int) or failure == "redirect" else "validation"
    assert result.checks[0].failure_kind == expected


def test_failed_refresh_keeps_last_successful_check_not_attempt_time(one_course, tmp_path):
    with fixture_client(one_course) as client:
        first = refresh_catalog(one_course, StudentProfile(), client=client, cache_dir=tmp_path, now=NOW)
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(503))) as client:
        result = refresh_catalog(one_course, StudentProfile(), client=client, cache_dir=tmp_path,
                                 now=NOW + timedelta(days=1))
    assert result.checks[0].status == "stale_cache"
    assert result.checks[0].attempted_at > result.checks[0].last_checked_at
    assert result.catalog.sources[0].last_checked_at == NOW
    assert result.catalog.sources[0].verification_status == "stale"
    assert "HTTP fixture" in result.catalog.records[0].title
    assert corpus_hash(first.catalog) == corpus_hash(result.catalog)


def test_cleared_source_cache_rebuilds_from_the_official_response(one_course, tmp_path):
    with fixture_client(one_course) as client:
        refresh_catalog(one_course, StudentProfile(), client=client, cache_dir=tmp_path, now=NOW)
        next(tmp_path.glob("*.json")).unlink()
        rebuilt = refresh_catalog(one_course, StudentProfile(), client=client, cache_dir=tmp_path, now=NOW)
    assert rebuilt.checks[0].status == "updated" and rebuilt.checks[0].cache_saved
    assert rebuilt.catalog.sources[0].last_checked_at == NOW


@pytest.mark.parametrize("change", [{"edition": "2025-2026"}, {"edition": None}, {"code": "ECE999"},
    {"variable_credits": True}, {"unit_range": (1, True)}, {"unit_range": (False, 0)}, {"unit_range": ("4", "4")}])
def test_identity_edition_and_credit_changes_cannot_replace_approved_data(one_course, tmp_path, change):
    page = course_page(one_course.records[0], **change)
    with fixture_client(one_course, overrides={"ECE101": page}) as client:
        result = refresh_catalog(one_course, StudentProfile(), client=client, cache_dir=tmp_path, now=NOW)
    assert result.checks[0].status == "bundled_fallback"
    assert result.catalog.records[0].title == one_course.records[0].title


def test_different_student_edition_makes_no_request(one_course, tmp_path):
    def forbidden(_):
        pytest.fail("A different student edition must not fetch the current catalog")

    with httpx.Client(transport=httpx.MockTransport(forbidden)) as client:
        result = refresh_catalog(one_course, StudentProfile(catalog_version="2025-2026"),
                                 client=client, cache_dir=tmp_path, now=NOW)
    assert result.checks[0].status == "unsupported_edition"
    assert result.issues and result.catalog.records[0].catalog_version == "2026-2027"


def test_conflicting_configured_source_edition_is_not_checked(one_course, tmp_path):
    one_course.sources[0].catalog_version = "2025-2026"
    with httpx.Client(transport=httpx.MockTransport(lambda _: pytest.fail("Conflicting edition contacted"))) as client:
        result = refresh_catalog(one_course, StudentProfile(), client=client, cache_dir=tmp_path, now=NOW)
    assert result.checks[0].status == "unsupported_edition" and result.issues


def test_description_html_is_text_not_executable_evidence(one_course, tmp_path):
    page = course_page(one_course.records[0], summary="<p>Fixture programming &amp; hardware.</p><script>untrusted_instruction()</script><p>Practice safely.</p>")
    with fixture_client(one_course, overrides={"ECE101": page}) as client:
        result = refresh_catalog(one_course, StudentProfile(), client=client, cache_dir=tmp_path, now=NOW)
    assert result.catalog.records[0].summary == "Fixture programming & hardware. Practice safely."


def test_changed_requirement_identifier_revokes_reviewed_rule(one_course, tmp_path):
    one_course.records[0].rule_reviewed = True
    one_course.records[0].rule = Rule(type="none")
    page = course_page(one_course.records[0], reference="new-unreviewed-reference")
    with fixture_client(one_course, overrides={"ECE101": page}) as client:
        result = refresh_catalog(one_course, StudentProfile(), client=client, cache_dir=tmp_path, now=NOW)
    assert result.catalog.records[0].requirement_reference == "new-unreviewed-reference"
    assert not result.catalog.records[0].rule_reviewed
    assert result.catalog.records[0].rule.type == "unknown"


@pytest.mark.parametrize("corruption", ["json", "hash", "edition", "url", "time", "schema"])
def test_invalid_cache_is_not_used_during_outage(one_course, tmp_path, corruption):
    with fixture_client(one_course) as client:
        refresh_catalog(one_course, StudentProfile(), client=client, cache_dir=tmp_path, now=NOW)
    path = next(tmp_path.glob("*.json"))
    data = json.loads(path.read_text())
    if corruption == "json":
        path.write_text("not JSON")
    else:
        if corruption == "hash":
            data["data"]["summary"] = "A poisoned cache value"
        elif corruption == "edition":
            data["data"]["catalog_version"] = "2025-2026"
        elif corruption == "url":
            data["url"] = "https://unapproved.example/course"
        elif corruption == "time":
            data["last_checked_at"] = "2026-01-01T00:00:00Z"
        else:
            data["schema_version"] = 999
        path.write_text(json.dumps(data))
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(503))) as client:
        result = refresh_catalog(one_course, StudentProfile(), client=client, cache_dir=tmp_path, now=NOW)
    assert result.checks[0].status == "bundled_fallback"
    assert result.catalog.records[0].summary == one_course.records[0].summary


def test_unapproved_host_is_not_contacted(one_course, tmp_path, monkeypatch):
    one_course.sources[0].url = "https://catalog.arizona.edu.unapproved.example/courses/0432351"
    monkeypatch.setattr("src.sources._read_cache", lambda *a: pytest.fail("Unapproved cache must not be trusted"))
    with httpx.Client(transport=httpx.MockTransport(lambda _: pytest.fail("Unapproved host contacted"))) as client:
        result = refresh_catalog(one_course, StudentProfile(), client=client, cache_dir=tmp_path, now=NOW)
    assert result.checks[0].status == "bundled_fallback"


def test_source_cache_write_failure_keeps_fetched_data(one_course, tmp_path, monkeypatch):
    def fail(*args):
        raise OSError("private filesystem detail")

    monkeypatch.setattr("src.sources._save_cache", fail)
    with fixture_client(one_course) as client:
        result = refresh_catalog(one_course, StudentProfile(), client=client, cache_dir=tmp_path, now=NOW)
    assert result.checks[0].status == "updated" and not result.checks[0].cache_saved
    assert result.catalog.sources[0].verification_status == "verified"
    assert "private filesystem detail" not in str(result.issues)


@pytest.mark.parametrize("career,expected", [("ai_ml", {"ECE101", "CSC120", "ECE425"}),
    ("embedded", {"ECE101", "ECE369A", "ECE372A"}),
    ("exploring", {"ECE101", "ECE369A", "ECE372A", "ECE425", "CSC120"})])
def test_only_relevant_configured_courses_are_checked(catalog, tmp_path, career, expected):
    seen = []
    with fixture_client(catalog, seen=seen) as client:
        refresh_catalog(catalog, StudentProfile(career_id=career), client=client, cache_dir=tmp_path, now=NOW)
    assert set(seen) == expected and len(seen) == len(expected)


def test_request_limit_retains_dated_references_for_omitted_sources(catalog, tmp_path, monkeypatch):
    monkeypatch.setattr("src.sources.MAX_SOURCES", 1)
    seen = []
    with fixture_client(catalog, seen=seen) as client:
        result = refresh_catalog(catalog, StudentProfile(), client=client, cache_dir=tmp_path, now=NOW)
    assert len(seen) == 1
    assert sum(c.status == "skipped" for c in result.checks) == 2
    assert result.issues


def test_unsupported_question_skips_all_source_requests(catalog):
    def forbidden(*args, **kwargs):
        pytest.fail("Unsupported coverage should not contact official sources")

    result = run_advisor(catalog, StudentProfile(question="Marine biology degree and ocean fieldwork"),
                         source_refresher=forbidden)
    assert result.coverage_notice
    assert result.trace["source_refresh"]["reason"] == "outside_supported_collection"


def test_missing_source_runtime_still_returns_a_current_profile_plan(one_course):
    def fail(*args, **kwargs):
        raise ValueError("private client configuration detail")

    result = run_advisor(one_course, StudentProfile(), source_refresher=fail)
    assert result.context.allowed_record_ids
    assert result.trace["source_refresh"]["error"] == "unavailable"
    assert result.context.source_freshness["catalog:ECE101"].verification_status == "stale"
    assert "private client configuration detail" not in str(result.issues)


def test_readonly_vector_cache_does_not_prevent_semantic_retrieval(one_course, fake_provider, tmp_path, monkeypatch):
    def fail(*args):
        raise OSError("read-only cache")

    monkeypatch.setattr(EmbeddingCache, "_write", staticmethod(fail))
    vectors, state, _ = EmbeddingCache(tmp_path).get(one_course, build_evidence(one_course), fake_provider)
    assert vectors.shape == (1, fake_provider.dimensions)
    assert state == "miss_uncached"
