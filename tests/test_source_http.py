"""Bounded public GET recovery, budgets, and safe attempt diagnostics."""

from datetime import timedelta

import httpx
import pytest

import src.source_http as transport
from src.models import SourceCheck, StudentProfile
from src.source_http import SourceBudgetError, SourcePageError, SourceRequest, read_public_page
from src.sources import refresh_catalog
from test_sources import NOW, course_page

URL = "https://catalog.arizona.edu/courses/0432351"
HEADERS = {"User-Agent": "ECE-Learning-Advisor/0.2", "If-None-Match": '"fixture"'}


@pytest.fixture
def clock(monkeypatch):
    class Clock:
        value = 0.0
        pauses = []
        def now(self): return self.value
        def advance(self, seconds): self.value += seconds
        def pause(self, seconds): self.pauses.append(seconds); self.advance(seconds)
    clock = Clock()
    monkeypatch.setattr(transport, "_now", clock.now)
    monkeypatch.setattr(transport, "_pause", clock.pause)
    return clock


def html(text="fresh page", **headers):
    return httpx.Response(200, text=text, headers={"Content-Type": "text/html", **headers})


def outcomes(state):
    return [attempt.outcome for attempt in state.attempts]


@pytest.mark.parametrize("error_type", transport.RETRY_EXCEPTIONS)
def test_transient_transport_failure_gets_one_fresh_get(clock, error_type):
    seen, state = [], SourceRequest()
    def respond(request):
        seen.append(request)
        if len(seen) == 1:
            raise error_type("private-transport-diagnostic", request=request)
        return html(ETag='"new"')
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        page = read_public_page(client, URL, HEADERS, request=state)
    assert page.text == "fresh page" and page.etag == '"new"'
    assert len(seen) == 2 and all(r.method == "GET" for r in seen)
    assert all(r.headers["if-none-match"] == '"fixture"' for r in seen)
    assert all(str(r.url) == URL for r in seen)
    assert state.retries == 1 and state.attempts[-1].retry
    assert outcomes(state) == ["timeout" if issubclass(error_type, httpx.TimeoutException) else "network", "success"]
    assert clock.pauses == [.25]
    assert "private-transport-diagnostic" not in str([a.model_dump() for a in state.attempts])


@pytest.mark.parametrize("status", [502, 503, 504])
def test_selected_server_failures_close_before_retry_and_keep_history(clock, status):
    responses, state = [], SourceRequest()
    def respond(request):
        if responses:
            assert responses[0].is_closed
            return html()
        response = httpx.Response(status, stream=httpx.ByteStream(b"server error"))
        responses.append(response)
        return response
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        assert read_public_page(client, URL, {}, request=state).status == 200
    assert outcomes(state) == ["response", "success"]
    assert [a.http_status for a in state.attempts] == [status, 200]


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308, 400, 401, 403, 404, 408, 429, 500, 501])
def test_redirects_rate_limits_and_other_responses_are_not_retried(clock, status):
    seen, state = [], SourceRequest()
    def respond(request): seen.append(request); return httpx.Response(status)
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(SourcePageError): read_public_page(client, URL, {}, request=state)
    assert len(seen) == 1 and state.retries == 0 and not clock.pauses


@pytest.mark.parametrize("retry_after", ["0", "20", "Thu, 05 Nov 2026 23:59:59 GMT", "invalid"])
def test_retry_after_never_triggers_an_early_repeat(clock, retry_after):
    seen, state = [], SourceRequest()
    def respond(request): seen.append(request); return httpx.Response(503, headers={"Retry-After": retry_after})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(SourcePageError): read_public_page(client, URL, {}, request=state)
    assert len(seen) == 1 and state.retries == 0 and not clock.pauses


@pytest.mark.parametrize("response", [
    httpx.Response(200, content=b"bad", headers={"Content-Type": "image/png"}),
    httpx.Response(200, content=b"\xff", headers={"Content-Type": "text/html"}),
    httpx.Response(200, headers={"Content-Type": "text/html", "Content-Length": "invalid"}),
    httpx.Response(200, headers={"Content-Type": "text/html", "Content-Length": "-1"}),
    httpx.Response(200, headers={"Content-Type": "text/html", "Content-Length": "3000001"}),
])
def test_content_and_size_validation_fail_without_retry(clock, response):
    state, seen = SourceRequest(), []
    def respond(request): seen.append(request); return response
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(ValueError): read_public_page(client, URL, {}, request=state)
    assert len(seen) == 1 and outcomes(state) == ["validation"] and not clock.pauses


@pytest.mark.parametrize("error", [httpx.ConnectTimeout, httpx.ConnectError])
def test_repeated_failures_cannot_create_a_third_attempt(clock, error):
    state, seen = SourceRequest(), []
    def respond(request): seen.append(request); raise error("private", request=request)
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(error): read_public_page(client, URL, {}, request=state)
    assert len(seen) == 2 and state.retries == 1


def test_partial_response_is_discarded_before_retry(clock):
    closed, seen, state = [], [], SourceRequest()
    class Broken(httpx.SyncByteStream):
        def __iter__(self): yield b"old partial page"; raise httpx.ReadError("private partial read")
        def close(self): closed.append(True)
    def respond(request):
        seen.append(request)
        if len(seen) == 1: return httpx.Response(200, stream=Broken(), headers={"Content-Type": "text/html"})
        assert closed
        return html("new complete page")
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        page = read_public_page(client, URL, {}, request=state)
    assert page.text == "new complete page" and outcomes(state) == ["network", "success"]
    assert state.received_bytes == len(b"old partial page") + len(b"new complete page")


def test_decoded_byte_budget_is_shared_across_both_attempts(clock, monkeypatch):
    monkeypatch.setattr(transport, "MAX_PAGE_BYTES", 10)
    state, seen = SourceRequest(), []
    class Broken(httpx.SyncByteStream):
        def __iter__(self): yield b"123456"; raise httpx.ReadTimeout("private")
    def respond(request):
        seen.append(request)
        if len(seen) == 1: return httpx.Response(200, stream=Broken(), headers={"Content-Type": "text/html"})
        return httpx.Response(200, stream=httpx.ByteStream(b"123456"), headers={"Content-Type": "text/html"})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(SourcePageError): read_public_page(client, URL, {}, request=state)
    assert len(seen) == 2 and outcomes(state) == ["timeout", "validation"]


def test_exhausted_elapsed_guard_stops_a_successful_late_response(clock):
    state = SourceRequest()
    def respond(request): clock.advance(12.1); return html()
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(SourceBudgetError): read_public_page(client, URL, {}, request=state)
    assert outcomes(state) == ["timeout"] and state.retries == 0


def test_retry_eligibility_requires_time_for_the_backoff(clock):
    state, seen = SourceRequest(), []
    def respond(request): seen.append(request); clock.advance(11.9); raise httpx.ConnectTimeout("private")
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(httpx.ConnectTimeout): read_public_page(client, URL, {}, request=state)
    assert len(seen) == 1 and not clock.pauses


def test_expiry_during_backoff_stops_without_counting_a_retry(clock, monkeypatch):
    state, seen = SourceRequest(), []
    monkeypatch.setattr(transport, "_pause", lambda delay: clock.advance(1))
    def respond(request): seen.append(request); clock.advance(11.6); raise httpx.ConnectTimeout("private")
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(httpx.ConnectTimeout): read_public_page(client, URL, {}, request=state)
    check = SourceCheck(source_id="fixture", code="ECE101", url=URL, status="bundled_fallback", attempted_at=NOW)
    state.apply(check)
    assert len(seen) == 1 and check.retry_count == 0 and check.transport_seconds == pytest.approx(12.6)


def test_retry_phase_timeouts_shrink_to_the_remaining_guard(clock):
    limits, state = [], SourceRequest()
    def respond(request):
        limits.append(request.extensions["timeout"])
        if len(limits) == 1: clock.advance(10); raise httpx.ReadTimeout("private")
        return html()
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        assert read_public_page(client, URL, {}, request=state).text
    assert limits[0] == {"connect": 4, "read": 6, "write": 6, "pool": 4}
    assert all(value == pytest.approx(1.75) for value in limits[1].values())


def test_course_recovery_after_503_304_preserves_the_content_download_date(clock, catalog, tmp_path):
    record = catalog.records[0]
    seen = []
    def respond(request):
        seen.append(request)
        if len(seen) == 1: return html(course_page(record), ETag='"fixture"')
        if len(seen) == 2: return httpx.Response(503)
        assert request.headers["if-none-match"] == '"fixture"'
        return httpx.Response(304)
    only = catalog.model_copy(deep=True)
    only.records = [record.model_copy(deep=True)]
    only.sources = [s for s in only.sources if s.source_id in record.source_ids]
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        first = refresh_catalog(only, StudentProfile(), client=client, cache_dir=tmp_path, now=NOW)
        second = refresh_catalog(only, StudentProfile(), client=client, cache_dir=tmp_path, now=NOW + timedelta(hours=1))
    check = second.checks[0]
    assert check.status == "not_modified" and check.retry_count == 1
    assert [a.outcome for a in check.attempts] == ["response", "not_modified"]
    assert check.retrieved_at == first.checks[0].retrieved_at == NOW
    assert check.last_checked_at == NOW + timedelta(hours=1)
    assert second.catalog.sources[0].verification_status == "verified"


def test_parser_or_course_identity_failure_is_not_retried(clock, catalog, tmp_path):
    seen = []
    def respond(request): seen.append(request); return html("<html>Unsupported parser layout</html>")
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = refresh_catalog(catalog, StudentProfile(career_id="embedded"), client=client, cache_dir=tmp_path)
    assert all(check.retry_count == 0 and len(check.attempts) == 1 for check in result.checks)
    assert all(check.failure_kind == "validation" for check in result.checks)
    assert all(check.status == "bundled_fallback" for check in result.checks)


@pytest.mark.parametrize("mode,expected", [("recover", "satisfied"), ("changed", "unknown"), ("exhausted", "unknown")])
def test_program_recovery_still_requires_exact_condition_evidence(clock, catalog, tmp_path, mode, expected):
    from src.models import Completion
    from src.rules import evaluate_course
    from test_rule_sources import program_page
    active = catalog.model_copy(deep=True)
    course = next(r for r in active.records if r.code == "CSC120")
    active.records = [course]
    active.sources = [s for s in active.sources if s.source_id in course.source_ids]
    program_calls = []
    def respond(request):
        if "/courses/" in str(request.url): return html(course_page(course))
        program_calls.append(request)
        if len(program_calls) == 1 or mode == "exhausted": raise httpx.ReadTimeout("private-program-transport")
        return html(program_page(course, text="Changed source statement" if mode == "changed" else None))
    profile = StudentProfile(completed=[Completion(course_code="ECE101", grade="B")])
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = refresh_catalog(active, profile, client=client, cache_dir=tmp_path, now=NOW)
    actual = next(r for r in result.catalog.records if r.code == "CSC120")
    assert evaluate_course(actual, profile).status == expected
    check = next(c for c in result.checks if c.kind == "rule")
    assert len(program_calls) == 2 and check.retry_count == 1
    assert check.status == ("bundled_fallback" if mode == "exhausted" else "updated")
    assert check.rule_status == ("verified" if mode == "recover" else "changed" if mode == "changed" else "unavailable")
    assert "private-program-transport" not in check.model_dump_json() + str(result.issues)


@pytest.mark.parametrize("retry_before_redirect", [False, True])
def test_cs50_redirect_shares_one_retry_allowance(clock, catalog, tmp_path, retry_before_redirect):
    from src.resource_sources import RESOURCE_URLS, apply_resource_source, fetch_resource_source, prepare_resource_jobs
    from test_resource_sources import resource_page
    jobs, _ = prepare_resource_jobs(catalog, StudentProfile(career_id="exploring"), NOW)
    job = next(j for j in jobs if j.record_id == "resource:cs50")
    target = "https://cs50.harvard.edu/x/2026/"
    seen = []
    def respond(request):
        seen.append(str(request.url))
        if str(request.url) == RESOURCE_URLS[job.record_id]:
            if retry_before_redirect and len(seen) == 1: raise httpx.ConnectTimeout("private-cs50-proxy")
            return httpx.Response(302, headers={"Location": "/x/2026/"})
        assert str(request.url) == target
        if retry_before_redirect or len(seen) == 2: raise httpx.ReadTimeout("private-cs50-read")
        return html(resource_page(job.record_id, canonical=target))
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        saved, check = fetch_resource_source(job, tmp_path, client, NOW)
    apply_resource_source(catalog, job, saved, check)
    assert len(seen) == 3 and len(check.attempts) == 3 and check.retry_count == 1
    assert check.status == ("bundled_fallback" if retry_before_redirect else "updated")
    source = next(s for s in catalog.sources if s.source_id == job.source.source_id)
    assert source.verification_status == ("stale" if retry_before_redirect else "verified")
    assert "private-cs50" not in check.model_dump_json()


def test_retry_does_not_bypass_resource_redirect_allowlist(clock, catalog, tmp_path):
    from src.resource_sources import fetch_resource_source, prepare_resource_jobs
    jobs, _ = prepare_resource_jobs(catalog, StudentProfile(career_id="exploring"), NOW)
    job = next(j for j in jobs if j.record_id == "resource:cs50")
    seen = []
    def respond(request):
        seen.append(str(request.url))
        return httpx.Response(503) if len(seen) == 1 else httpx.Response(302, headers={"Location": "https://unapproved.example/x/2026/"})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        saved, check = fetch_resource_source(job, tmp_path, client, NOW)
    assert len(seen) == 2 and not saved and check.status == "bundled_fallback"
    assert all("unapproved" not in url for url in seen) and check.retry_count == 1


def test_resource_redirect_keeps_the_original_elapsed_guard(clock, catalog, tmp_path):
    from src.resource_sources import RESOURCE_URLS, fetch_resource_source, prepare_resource_jobs
    from test_resource_sources import resource_page
    jobs, _ = prepare_resource_jobs(catalog, StudentProfile(career_id="exploring"), NOW)
    job = next(j for j in jobs if j.record_id == "resource:cs50")
    target = "https://cs50.harvard.edu/x/2026/"
    def respond(request):
        if str(request.url) == RESOURCE_URLS[job.record_id]:
            clock.advance(11.9)
            return httpx.Response(302, headers={"Location": "/x/2026/"})
        assert all(t <= .101 for t in request.extensions["timeout"].values())
        clock.advance(.2)
        return html(resource_page(job.record_id, canonical=target))
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        saved, check = fetch_resource_source(job, tmp_path, client, NOW)
    assert not saved and check.failure_kind == "timeout" and check.retry_count == 0
    assert [a.outcome for a in check.attempts] == ["redirect", "timeout"]


@pytest.mark.parametrize("error", [httpx.PoolTimeout, httpx.ProxyError, httpx.LocalProtocolError])
def test_pool_proxy_and_local_protocol_failures_are_not_retried(clock, error):
    seen, state = [], SourceRequest()
    def respond(request): seen.append(request); raise error("private local configuration")
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(error): read_public_page(client, URL, {}, request=state)
    assert len(seen) == 1 and state.retries == 0 and not clock.pauses
