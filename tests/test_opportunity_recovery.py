"""Public JSON recovery with fake time, transport failures, and no real requests."""

import gzip
import json

import httpx
import pytest

import src.source_http as transport
from src.opportunities import OpportunitySearchError, load_employer_boards, search_employer_jobs
from src.opportunity_details import fetch_posting_detail
from src.source_http import SourceBudgetError, SourcePageError, SourceRequest, read_public_json, read_public_page
from test_opportunities import NOW, post
from test_opportunity_details import selected
from test_source_http import clock

URL = "https://boards-api.greenhouse.io/v1/boards/samsara/jobs"
HEADERS = {"Accept": "application/json", "User-Agent": "ECE-Learning-Advisor/0.3"}


def read(handler, state=None):
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        return read_public_json(client, URL, HEADERS, request=state)


@pytest.mark.parametrize("error", transport.RETRY_EXCEPTIONS)
def test_public_json_retries_a_transient_get_once_and_exposes_only_safe_attempt_metadata(clock, error):
    seen, state = [], SourceRequest()
    def respond(request):
        seen.append(request)
        if len(seen) == 1: raise error("private transport diagnostic")
        return httpx.Response(200, json={"jobs": []})
    assert read(respond, state) == {"jobs": []}
    assert len(seen) == 2 and all(r.method == "GET" and str(r.url) == URL and not r.url.query for r in seen)
    assert all("authorization" not in r.headers and r.headers["accept"] == "application/json" for r in seen)
    info = state.diagnostics()
    assert info["retry_count"] == 1 and info["attempts"][-1]["outcome"] == "success" and info["http_status"] == 200
    assert clock.pauses == [.25] and "private" not in json.dumps(info)


@pytest.mark.parametrize("status", [502, 503, 504])
def test_transient_http_response_closes_before_retry(clock, status):
    responses, state = [], SourceRequest()
    def respond(request):
        if responses:
            assert responses[0].is_closed
            return httpx.Response(200, json={"jobs": []})
        response = httpx.Response(status, stream=httpx.ByteStream(b"private server body"))
        responses.append(response)
        return response
    assert read(respond, state) == {"jobs": []}
    assert [a.http_status for a in state.attempts] == [status, 200] and state.retries == 1


@pytest.mark.parametrize("status", [301, 302, 304, 400, 403, 404, 408, 410, 429, 500])
def test_nonretryable_http_statuses_do_not_redirect_or_become_empty_results(clock, status):
    seen, state = [], SourceRequest()
    def respond(request): seen.append(request); return httpx.Response(status, headers={"Location": "https://other.example"})
    with pytest.raises(SourcePageError): read(respond, state)
    assert len(seen) == 1 and state.retries == 0 and not clock.pauses
    assert state.attempts[0].outcome == ("redirect" if status in {301, 302} else "response")


@pytest.mark.parametrize("retry_after", ["0", "10", "invalid"])
def test_retry_after_header_prevents_an_early_repeat(clock, retry_after):
    seen = []
    def respond(request): seen.append(request); return httpx.Response(503, headers={"Retry-After": retry_after})
    with pytest.raises(SourcePageError): read(respond)
    assert len(seen) == 1 and not clock.pauses


@pytest.mark.parametrize("error", [httpx.PoolTimeout, httpx.ProxyError, httpx.LocalProtocolError])
def test_local_configuration_and_pool_failures_are_not_retried(clock, error):
    seen = []
    def respond(request): seen.append(request); raise error("private local diagnostic")
    with pytest.raises(error): read(respond)
    assert len(seen) == 1 and not clock.pauses


@pytest.mark.parametrize("body,media", [
    ('{"id":12,"id":13}', "application/json"), ('{"value":NaN}', "application/json"),
    ('{"value":Infinity}', "application/json"), ("not JSON", "application/json"),
    ('{"jobs":[]}', "application/jsonx"), ('{"jobs":[]}', "text/html"),
])
def test_ambiguous_malformed_or_wrong_media_json_fails_without_retry(clock, body, media):
    seen, state = [], SourceRequest()
    def respond(request): seen.append(request); return httpx.Response(200, content=body, headers={"Content-Type": media})
    with pytest.raises(ValueError): read(respond, state)
    assert len(seen) == 1 and state.retries == 0 and not clock.pauses


def test_partial_json_is_discarded_but_bytes_remain_in_the_shared_budget(clock):
    state, closed, seen = SourceRequest(), [], []
    class Broken(httpx.SyncByteStream):
        def __iter__(self): yield b'{"old":1'; raise httpx.ReadError("private partial read")
        def close(self): closed.append(True)
    def respond(request):
        seen.append(request)
        if len(seen) == 1: return httpx.Response(200, stream=Broken(), headers={"Content-Type": "application/json"})
        assert closed
        return httpx.Response(200, content=b'{"fresh":true}', headers={"Content-Type": "application/json; charset=utf-8"})
    assert read(respond, state) == {"fresh": True}
    assert state.received_bytes == len(b'{"old":1') + len(b'{"fresh":true}')
    assert [a.outcome for a in state.attempts] == ["network", "success"]


def test_partial_and_retry_bodies_share_one_download_cap(clock, monkeypatch):
    monkeypatch.setattr(transport, "MAX_PAGE_BYTES", 10)
    state, seen = SourceRequest(), []
    class Broken(httpx.SyncByteStream):
        def __iter__(self): yield b"123456"; raise httpx.ReadTimeout("private")
    def respond(request):
        seen.append(request)
        if len(seen) == 1: return httpx.Response(200, stream=Broken(), headers={"Content-Type": "application/json"})
        return httpx.Response(200, content=b"123456", headers={"Content-Type": "application/json"})
    with pytest.raises(SourcePageError): read(respond, state)
    assert len(seen) == 2 and [a.outcome for a in state.attempts] == ["timeout", "validation"]


def test_compressed_responses_are_bounded_by_decoded_bytes(clock, monkeypatch):
    monkeypatch.setattr(transport, "MAX_PAGE_BYTES", 80)
    state = SourceRequest()
    compressed = gzip.compress(b'{"text":"' + b"a" * 1000 + b'"}')
    assert len(compressed) < 80
    def respond(request):
        return httpx.Response(200, stream=httpx.ByteStream(compressed),
            headers={"Content-Type": "application/json", "Content-Encoding": "gzip", "Content-Length": str(len(compressed))})
    with pytest.raises(SourcePageError): read(respond, state)
    assert state.retries == 0 and state.received_bytes > 80


def test_retry_phase_timeouts_shrink_to_the_original_elapsed_guard(clock):
    limits, state = [], SourceRequest()
    def respond(request):
        limits.append(request.extensions["timeout"])
        if len(limits) == 1: clock.advance(10); raise httpx.ReadTimeout("private")
        return httpx.Response(200, json={"jobs": []})
    assert read(respond, state) == {"jobs": []}
    assert limits[0] == {"connect": 4, "read": 6, "write": 6, "pool": 4}
    assert all(v == pytest.approx(1.75) for v in limits[1].values())
    assert state.diagnostics()["transport_seconds"] == pytest.approx(10.25)


def test_success_after_elapsed_guard_is_still_a_failure(clock):
    state = SourceRequest()
    def respond(request): clock.advance(12.1); return httpx.Response(200, json={"jobs": []})
    with pytest.raises(SourceBudgetError): read(respond, state)
    assert state.retries == 0 and state.attempts[0].outcome == "timeout"


@pytest.mark.parametrize("reader,media", [(read_public_page, "text/html"), (read_public_json, "application/json")])
def test_elapsed_guard_also_checks_an_empty_stream_that_finishes_late(clock, reader, media):
    state = SourceRequest()
    class LateEmpty(httpx.SyncByteStream):
        def __iter__(self):
            clock.advance(12.1)
            return iter(())
    with httpx.Client(transport=httpx.MockTransport(lambda r:
            httpx.Response(200, stream=LateEmpty(), headers={"Content-Type": media}))) as client:
        with pytest.raises(SourceBudgetError): reader(client, URL, {}, request=state)
    assert len(state.attempts) == 1 and state.attempts[0].outcome == "timeout" and state.retries == 0


def test_exhausted_retries_leave_all_boards_unavailable_with_safe_history(clock):
    boards, seen = load_employer_boards(), []
    def respond(request): seen.append(request); raise httpx.ReadTimeout("private diagnostic")
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(OpportunitySearchError) as error:
            search_employer_jobs("embedded", client=client, now=NOW)
    assert len(seen) == 6 and len(error.value.checks) == 3
    assert all(c["status"] == "unavailable" and c["checked_at"] is None and c["retry_count"] == 1
               and len(c["attempts"]) == 2 for c in error.value.checks)
    assert "private" not in json.dumps(error.value.checks)


def test_recovered_board_still_needs_post_validation_before_it_can_be_verified(clock):
    board = load_employer_boards()[0]
    seen = []
    def respond(request):
        seen.append(request)
        if len(seen) == 1: return httpx.Response(503)
        return httpx.Response(200, json={"jobs": [{**post(board), "company_name": "Other employer"}]})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(OpportunitySearchError) as error:
            search_employer_jobs("ai_ml", boards=[board], client=client, now=NOW)
    check = error.value.checks[0]
    assert check["failure_kind"] == "validation" and check["checked_at"] is None and check["rejected_posts"] == 1
    assert [a["outcome"] for a in check["attempts"]] == ["response", "success"]


def test_posting_detail_recovery_retains_history_and_a_fresh_success_time(clock):
    seen = []
    def respond(request):
        seen.append(request)
        if len(seen) == 1: raise httpx.ReadTimeout("private diagnostic")
        return httpx.Response(200, json={**post(), "content": "Fresh requirements"})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        check = fetch_posting_detail(selected(), client=client, now=NOW)
    assert check.status == "verified" and check.checked_at == NOW and check.posting.description == "Fresh requirements"
    assert check.retry_count == 1 and [a.outcome for a in check.attempts] == ["timeout", "success"]
    assert "private" not in check.model_dump_json()
