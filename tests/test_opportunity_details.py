"""Controlled posting checks; no real network, model, or application requests."""

import hashlib
import json
from dataclasses import replace

import httpx
import pytest

from src.opportunities import load_employer_boards, normalize_post, request_opportunities
from src.opportunity_details import (MAX_CONTENT_CHARS, MAX_DESCRIPTION_CHARS,
    fetch_posting_detail, posting_text, request_posting_detail)
from src.session import apply_profile
from test_opportunities import NOW, cached_result, post


def selected(board=None, **changes):
    return normalize_post(post(board, **changes), board or load_employer_boards()[0], NOW)


def checked(payload=None, *, job=None, board=None, seen=None):
    board = board or load_employer_boards()[0]
    job = job or selected(board)
    payload = {**post(board), "content": "<h2>Requirements</h2><ul><li>C programming</li><li>Review degree requirements</li></ul>"} if payload is None else payload
    def respond(request):
        if seen is not None: seen.append(request)
        if isinstance(payload, Exception): raise payload
        return payload if isinstance(payload, httpx.Response) else httpx.Response(200, json=payload)
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = fetch_posting_detail(job, boards=[board], client=client, now=NOW)
        assert not client.is_closed  # Injected clients retain ownership.
        return result


def search_state(job=None, **changes):
    return {"job_result": replace(cached_result(), listings=[job or selected()], **changes)}


@pytest.mark.parametrize("board", load_employer_boards())
def test_one_detail_request_binds_configured_board_posting_and_dates_without_profile_or_keys(board):
    seen = []
    result = checked(board=board, seen=seen)
    assert result.status == "verified" and result.checked_at == result.requested_at == NOW
    assert result.source_url == board.endpoint + "/12" and result.changed_fields == []
    assert result.posting.employer == board.employer and result.posting.posted_at != result.posting.updated_at
    assert len(seen) == 1 and seen[0].method == "GET"
    assert str(seen[0].url) == result.source_url and not seen[0].url.query
    assert "authorization" not in seen[0].headers and not seen[0].content
    assert result.posting.description == "Requirements\n\n• C programming\n• Review degree requirements"
    assert result.posting.description_sha256 == hashlib.sha256(result.posting.description.encode()).hexdigest()


def test_html_is_plain_text_with_readable_lists_and_no_active_or_hidden_markup():
    text = posting_text('&lt;h2&gt;Requirements&lt;/h2&gt;&lt;p&gt;C &amp;amp; C++&lt;/p&gt;'
        '<script>private-script</script><style>private-style</style><template>private-template</template>'
        '<p><a href="https://other.example">Source words</a><img src="https://other.example/x"></p>')
    assert text == "Requirements\n\nC & C++\n\nSource words"
    assert "https://" not in text and "private-" not in text


@pytest.mark.parametrize("content", [None, [], "", "   ", "<script>hidden</script>", "x" * (MAX_CONTENT_CHARS + 1)],
    ids=["missing", "wrong_type", "empty", "whitespace", "hidden_only", "excessive"])
def test_missing_invisible_or_excessive_content_cannot_claim_a_verified_description(content):
    result = checked({**post(), "content": content})
    assert result.status == "invalid_response" and result.http_status == 200
    assert result.posting is None and result.checked_at is None


def test_shortened_description_is_explicit_and_fingerprint_covers_the_full_text():
    text = "Requirements " + "x" * MAX_DESCRIPTION_CHARS
    result = checked({**post(), "content": "<p>" + text + "</p>"})
    assert result.status == "verified" and result.posting.truncated
    assert len(result.posting.description) == MAX_DESCRIPTION_CHARS
    assert result.posting.description_chars == len(text)
    assert result.posting.description_sha256 == hashlib.sha256(text.encode()).hexdigest()


@pytest.mark.parametrize("change", [{"id": 13}, {"id": True}, {"internal_job_id": None},
    {"company_name": "Other employer"}, {"absolute_url": "https://boards.greenhouse.io/other/jobs/12"},
    {"location": []}])
def test_detail_identity_and_source_validation_are_separate_from_http_success(change):
    result = checked({**post(), "content": "Requirements", **change})
    assert result.status == "invalid_response" and result.posting is None


@pytest.mark.parametrize("field,value", [("title", "Senior Firmware Engineer"), ("location", {"name": "Boston, MA"}),
    ("absolute_url", "https://job-boards.greenhouse.io/samsara/jobs/12"),
    ("first_published", "2026-09-02T12:00:00Z"), ("updated_at", "2026-11-04T12:00:00Z")])
def test_metadata_drift_is_reported_without_overwriting_the_search_or_reapplying_filters(field, value):
    job = selected()
    result = checked({**post(), "content": "Requirements", field: value}, job=job)
    expected = {"absolute_url": "url", "first_published": "posted_at"}.get(field, field)
    assert result.status == "verified" and result.changed_fields == [expected]
    assert job == selected()


@pytest.mark.parametrize("status,expected", [(404, "not_listed"), (410, "not_listed"), (429, "unavailable"),
    (503, "unavailable"), (302, "unavailable")])
def test_non_success_statuses_do_not_retry_redirect_or_claim_a_closed_job(status, expected):
    seen = []
    result = checked(httpx.Response(status, headers={"location": "https://other.example", "retry-after": "10"}), seen=seen)
    assert result.status == expected and result.http_status == status and len(seen) == 1
    assert result.posting is None and result.checked_at is None


@pytest.mark.parametrize("error,kind", [(httpx.ReadTimeout("private diagnostic"), "timeout"),
    (httpx.ConnectError("private diagnostic"), "network")])
def test_transport_failure_is_sanitized_and_never_reuses_a_description(error, kind):
    seen = []
    result = checked(error, seen=seen)
    assert result.status == "unavailable" and result.failure_kind == kind and len(seen) == 2
    assert result.retry_count == 1 and len(result.attempts) == 2
    assert "private diagnostic" not in result.model_dump_json() and result.posting is None


@pytest.mark.parametrize("response", [httpx.Response(200, text="invalid", headers={"content-type": "application/json"}),
    httpx.Response(200, json={"content": "words"}, headers={"content-type": "text/html"}),
    httpx.Response(200, json={}, headers={"content-length": "3000001"})])
def test_json_format_type_and_size_limits_apply_to_details(response):
    assert checked(response).status == "invalid_response"


def test_partial_stream_is_closed_and_discarded():
    class Interrupted(httpx.SyncByteStream):
        closed = False
        def __iter__(self):
            yield b'{"content":"partial private body'
            raise httpx.ReadError("private stream error")
        def close(self): self.closed = True
    streams = []
    def respond(request):
        stream = Interrupted()
        streams.append(stream)
        return httpx.Response(200, stream=stream, headers={"content-type": "application/json"})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = fetch_posting_detail(selected(), client=client, now=NOW)
    assert len(streams) == 2 and all(stream.closed for stream in streams)
    assert result.status == "unavailable" and result.posting is None
    assert "private" not in result.model_dump_json()


@pytest.mark.parametrize("phase", ["headers", "body_end"])
def test_elapsed_guard_rejects_late_headers_and_end_of_empty_body(monkeypatch, phase):
    import src.source_http as transport
    clock = [0.0]
    monkeypatch.setattr(transport, "_now", lambda: clock[0])
    class LateEmpty(httpx.SyncByteStream):
        def __iter__(self):
            clock[0] = 13.0
            return iter(())
    def respond(request):
        if phase == "headers": clock[0] = 13.0
        return httpx.Response(200, stream=LateEmpty(), headers={"content-type": "application/json"})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = fetch_posting_detail(selected(), client=client, now=NOW)
    assert result.status == "unavailable" and result.failure_kind == "timeout" and result.checked_at is None
    assert result.retry_count == 0 and len(result.attempts) == 1


@pytest.mark.parametrize("change", [{"id": "greenhouse:samsara:012"}, {"id": "greenhouse:other:12"},
    {"id": "https://other.example"}, {"url": "https://other.example/jobs/12"}, {"employer": "Other"}])
def test_invalid_selection_fails_before_any_network_and_clears_old_details(change):
    state = {**search_state({**selected(), **change}), "job_detail": checked()}
    with pytest.raises(ValueError):
        request_posting_detail(state, state["job_result"].listings[0]["id"],
            fetcher=lambda *a, **k: pytest.fail("Invalid selection must not fetch"))
    assert "job_detail" not in state


@pytest.mark.parametrize("changes", [{"provider": "adzuna"}, {"listings": []}, {"source_scope_hash": "f" * 64}])
def test_only_a_displayed_public_posting_in_the_current_scope_can_be_checked(changes):
    state = search_state()
    state["job_result"] = replace(state["job_result"], **changes)
    with pytest.raises(ValueError):
        request_posting_detail(state, selected()["id"], fetcher=lambda *a, **k: pytest.fail("Do not fetch"))


def test_every_action_rechecks_and_a_failure_replaces_previous_verified_content():
    state, calls = search_state(), []
    outcomes = iter([checked(), checked(httpx.Response(404))])
    def fetch(job, **kwargs): calls.append(job["id"]); return next(outcomes)
    request_posting_detail(state, selected()["id"], fetcher=fetch)
    assert state["job_detail"].posting
    request_posting_detail(state, selected()["id"], fetcher=fetch)
    assert calls == [selected()["id"]] * 2
    assert state["job_detail"].status == "not_listed" and state["job_detail"].posting is None


@pytest.mark.parametrize("change", [{"posting_id": "greenhouse:samsara:13"}, {"source_url": "https://other.example"},
    {"checked_at": None}])
def test_inconsistent_or_wrong_source_returned_results_are_not_stored(change):
    state = search_state()
    bad = checked().model_copy(update=change)
    with pytest.raises(ValueError):
        request_posting_detail(state, selected()["id"], fetcher=lambda *a, **k: bad)
    assert "job_detail" not in state


def test_new_search_even_when_invalid_and_profile_change_clear_the_detail_state():
    state = {**search_state(), "job_detail": checked(), "job_detail_error": selected()["id"]}
    with pytest.raises(ValueError): request_opportunities(state, "invalid", "", False)
    assert "job_detail" not in state and "job_detail_error" not in state
    from src.models import StudentProfile
    state.update(job_detail=checked(), job_detail_error=selected()["id"])
    apply_profile(state, StudentProfile())
    assert "job_detail" not in state and "job_detail_error" not in state


def test_naive_time_fails_before_request():
    with pytest.raises(ValueError): fetch_posting_detail(selected(), now=NOW.replace(tzinfo=None))


@pytest.mark.parametrize("status", [200, 404])
def test_opt_in_cli_checks_one_selected_detail_and_keeps_only_metadata(monkeypatch, tmp_path, status):
    from scripts import check_opportunities as cli
    result = search_state()["job_result"]
    calls = []
    monkeypatch.setattr(cli, "search_employer_jobs", lambda *a, **k: result)
    def detail(state, posting_id):
        calls.append(posting_id)
        return checked() if status == 200 else checked(httpx.Response(status))
    monkeypatch.setattr(cli, "request_posting_detail", detail)
    output = tmp_path / "detail.json"
    monkeypatch.setattr("sys.argv", ["check", "--check-first-detail", "--output", str(output)])
    assert cli.main() == (0 if status == 200 else 1)
    report = json.loads(output.read_text())
    assert calls == [selected()["id"]] and report["model_calls"] == 0 and not report["credentials_used"]
    assert report["detail"]["status"] == ("verified" if status == 200 else "not_listed")
    if report["detail"]["posting"]: assert "description" not in report["detail"]["posting"]


def test_cli_opt_in_with_no_match_cannot_claim_a_detail_was_verified(monkeypatch, tmp_path):
    from scripts import check_opportunities as cli
    monkeypatch.setattr(cli, "search_employer_jobs", lambda *a, **k: cached_result())
    monkeypatch.setattr(cli, "request_posting_detail", lambda *a, **k: pytest.fail("No selection exists"))
    output = tmp_path / "empty.json"
    monkeypatch.setattr("sys.argv", ["check", "--check-first-detail", "--output", str(output)])
    assert cli.main() == 1
    assert json.loads(output.read_text())["detail_error"]
