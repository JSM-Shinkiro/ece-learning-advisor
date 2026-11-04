"""Controlled public-board and explicit-search boundaries; no real requests."""

import io
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from pydantic import ValidationError

from src.jobs import JobSearchResult, search_jobs
from src.opportunities import (CACHE_SECONDS, MAX_RESULTS, EmployerBoard, load_employer_boards,
    OpportunitySearchError, normalize_post, request_opportunities, search_employer_jobs, valid_posting_url)

NOW = datetime(2026, 11, 4, 22, tzinfo=timezone.utc)


def post(board=None, identity=12, **changes):
    board = board or load_employer_boards()[0]
    url = board.job_base_url + str(identity) if board.url_style == "id_path" else board.job_base_url + "?gh_jid=" + str(identity)
    return {"id": identity, "internal_job_id": identity + 1000, "title": "Machine Learning Engineer",
        "company_name": board.employer, "location": {"name": "Remote - US"}, "absolute_url": url,
        "first_published": "2026-09-01T12:00:00Z", "updated_at": "2026-11-03T12:00:00Z", **changes}


def client_for(payloads, seen=None):
    def handle(request):
        if seen is not None:
            seen.append(request)
        value = payloads[request.url.path.split('/')[3]]
        if isinstance(value, Exception):
            raise value
        if isinstance(value, httpx.Response):
            return value
        return httpx.Response(200, json=value)
    return httpx.Client(transport=httpx.MockTransport(handle))


def one_board(items, **options):
    boards = load_employer_boards()[:1]
    with client_for({boards[0].token: {"jobs": items}}) as client:
        return search_employer_jobs(options.pop("career", "ai_ml"), client=client, boards=boards, now=NOW, **options)


def cached_result(provider="greenhouse"):
    return JobSearchResult([], NOW.isoformat(), "AI / Machine Learning", "All listed locations", provider=provider)


def test_live_contract_normalizes_sources_and_dates_without_career_data_in_requests():
    boards = load_employer_boards()
    seen = []
    with client_for({b.token: {"jobs": [post(b)]} for b in boards}, seen) as client:
        result = search_employer_jobs("ai_ml", client=client, now=NOW)
    assert len(seen) == 2 and all(r.method == "GET" and not r.url.query for r in seen)
    assert all(r.url.host == "boards-api.greenhouse.io" for r in seen)
    assert len(result.listings) == 2  # Same numeric ID in two boards remains distinct.
    assert len({j["id"] for j in result.listings}) == 2
    assert result.provider == "greenhouse" and result.total_matches == 2
    assert all(c["status"] == "verified" for c in result.checks)
    assert result.listings[0]["posted_at"] != result.listings[0]["updated_at"]
    assert result.listings[0]["description_snippet"] == ""
    assert result.listings[0]["matched_terms"] == ["machine learning"]


@pytest.mark.parametrize("career,title", [("ai_ml", "Computer Vision Research Scientist"),
    ("ai_ml", "AI Platform Software Engineer Intern"), ("embedded", "Firmware Engineer Co-Op"),
    ("embedded", "Embedded Software Engineer"), ("embedded", "Electrical Engineer")])
def test_relevant_engineering_title_filters(career, title):
    result = one_board([post(title=title)], career=career)
    assert len(result.listings) == 1


@pytest.mark.parametrize("title", ["Family Benefits Engineer", "AI Sales Engineer", "Hardware Recruiter",
    "Engineering Recruiting Manager", "Marketing Intern, AI Products", "Autonomous Vehicle Operator"])
def test_title_scope_does_not_treat_substrings_or_nonengineering_roles_as_matches(title):
    assert not one_board([post(title=title)]).listings


@pytest.mark.parametrize("title,expected", [("Firmware Engineer Intern", True), ("Firmware Engineer Co-Op", True),
    ("Internal Firmware Engineer", False), ("Senior Firmware Engineer", False)])
def test_internship_is_an_exact_title_filter(title, expected):
    result = one_board([post(title=title)], career="embedded", internship=True)
    assert bool(result.listings) is expected


def test_location_is_literal_employer_text_not_a_radius_or_eligibility_inference():
    item = post(location={"name": "Remote - US; San Francisco, CA"})
    assert one_board([item], location=" remote - us ").listings
    assert not one_board([item], location="Tucson").listings
    assert not one_board([item], location="United States").listings  # No unproven geographic expansion.


def test_age_filter_uses_update_date_and_retains_original_publication_date():
    result = one_board([post()], updated_within=7)
    assert result.listings[0]["posted_at"].startswith("2026-09-01")
    assert result.listings[0]["updated_at"].startswith("2026-11-03")
    assert not one_board([post(updated_at="2026-08-01T10:00:00Z")], updated_within=7).listings


@pytest.mark.parametrize("date", [None, "not a date", "2026-11-03", "2027-01-01T10:00:00Z"])
def test_missing_invalid_or_future_update_dates_cannot_pass_an_age_filter(date):
    assert not one_board([post(updated_at=date)], updated_within=7).listings
    assert one_board([post(updated_at=date)]).listings[0]["updated_at"] is None


def test_postings_are_deduplicated_sorted_and_capped():
    items = [post(identity=i, updated_at=(NOW - timedelta(days=i)).isoformat()) for i in range(1, 15)]
    result = one_board([*reversed(items), items[0]])
    assert result.total_matches == 14 and len(result.listings) == MAX_RESULTS
    assert result.listings[0]["id"].endswith(":1")


@pytest.mark.parametrize("url", ["http://www.samsara.com/company/careers/roles/12",
    "https://www.samsara.com.evil.example/company/careers/roles/12", "https://user:pass@www.samsara.com/company/careers/roles/12",
    "https://www.samsara.com:444/company/careers/roles/12", "https://www.samsara.com/company/careers/roles/13",
    "https://www.samsara.com/company/careers/roles/12?gh_jid=13", "https://www.samsara.com/company/careers/roles/12?redirect=https://evil.example",
    "https://boards.greenhouse.io/other/jobs/12", "javascript:alert(1)", "https://www.samsara.com/company/careers/roles/12#other"])
def test_links_must_bind_https_host_board_and_posting_id(url):
    with pytest.raises(ValueError):
        valid_posting_url(url, load_employer_boards()[0], "12")


@pytest.mark.parametrize("host", ["boards.greenhouse.io", "job-boards.greenhouse.io"])
def test_standard_hosted_board_links_are_accepted(host):
    url = "https://" + host + "/samsara/jobs/12?gh_jid=12"
    assert valid_posting_url(url, load_employer_boards()[0], "12") == url


def test_custom_query_id_url_must_have_the_same_post_id():
    board = load_employer_boards()[1]
    assert valid_posting_url("https://nuro.ai/careersitem?gh_jid=12", board, "12")
    with pytest.raises(ValueError):
        valid_posting_url("https://nuro.ai/careersitem", board, "12")


@pytest.mark.parametrize("changes", [{"id": True}, {"id": "12"}, {"id": -2}, {"internal_job_id": "12"},
    {"company_name": "Different employer"}, {"title": 123}, {"title": ""}, {"location": []},
    {"location": {"name": "x" * 501}}])
def test_malformed_records_are_omitted_without_losing_valid_posts(changes):
    result = one_board([post(), post(identity=13, **changes)] if "id" not in changes else [post(), post(**changes)])
    assert len(result.listings) == 1 and result.issues
    assert result.checks[0]["rejected_posts"] == 1


def test_talent_network_posts_are_not_job_recommendations():
    assert not one_board([post(internal_job_id=None)]).listings


def test_posting_text_is_plain_text_without_script_content():
    result = one_board([post(title="&lt;script&gt;private&lt;/script&gt;Machine Learning Engineer")])
    assert result.listings[0]["title"] == "Machine Learning Engineer"


@pytest.mark.parametrize("status", [301, 302, 403, 404, 429, 500])
def test_http_failures_do_not_follow_redirects_or_become_empty_success(status):
    board = load_employer_boards()[0]
    seen = []
    with client_for({board.token: httpx.Response(status, headers={"Location": "https://elsewhere.example"})}, seen) as client:
        with pytest.raises(RuntimeError):
            search_employer_jobs("ai_ml", client=client, boards=[board], now=NOW)
    assert len(seen) == 1


def test_partial_failure_retains_only_checked_boards_with_a_visible_issue():
    boards = load_employer_boards()
    with client_for({boards[0].token: {"jobs": [post(boards[0])]}, boards[1].token: httpx.Response(429)}) as client:
        result = search_employer_jobs("ai_ml", client=client, now=NOW)
    assert len(result.listings) == 1 and result.issues
    assert result.checks[1]["http_status"] == 429 and result.checks[1]["checked_at"] is None


def test_all_board_failures_keep_safe_source_diagnostics_and_do_not_become_results():
    boards = load_employer_boards()
    state = {"job_result": cached_result()}
    def search(*a, **k):
        with client_for({b.token: httpx.Response(429) for b in boards}) as client:
            return search_employer_jobs("ai_ml", client=client, now=NOW)
    with pytest.raises(OpportunitySearchError) as exc:
        request_opportunities(state, "ai_ml", "", False, public_search=search, now=NOW)
    assert "job_result" not in state
    assert state["job_error"]["checks"] == exc.value.checks
    assert all(c["http_status"] == 429 and c["checked_at"] is None for c in exc.value.checks)


@pytest.mark.parametrize("payload", [{}, {"jobs": {}}, {"jobs": [None]}, {"jobs": [{}] * 4001}])
def test_invalid_or_excessive_payloads_do_not_claim_an_empty_search(payload):
    board = load_employer_boards()[0]
    with client_for({board.token: payload}) as client:
        with pytest.raises(RuntimeError):
            search_employer_jobs("ai_ml", client=client, boards=[board], now=NOW)


@pytest.mark.parametrize("response", [httpx.Response(200, text="{}", headers={"content-type": "text/html"}),
    httpx.Response(200, text="invalid JSON", headers={"content-type": "application/json"}),
    httpx.Response(200, json={"jobs": []}, headers={"content-length": "3000001"}),
    httpx.Response(200, json={"jobs": []}, headers={"content-length": "bad"})])
def test_response_type_size_and_json_are_validated(response):
    board = load_employer_boards()[0]
    with client_for({board.token: response}) as client:
        with pytest.raises(RuntimeError):
            search_employer_jobs("ai_ml", client=client, boards=[board], now=NOW)


def test_timeout_is_sanitized_and_is_not_an_empty_result():
    board = load_employer_boards()[0]
    with client_for({board.token: httpx.ReadTimeout("private detail")}) as client:
        with pytest.raises(RuntimeError) as exc:
            search_employer_jobs("ai_ml", client=client, boards=[board], now=NOW)
    assert "private detail" not in str(exc.value)


@pytest.mark.parametrize("options", [{"career": "exploring"}, {"career": []}, {"location": "x" * 121},
    {"location": None}, {"location": "a\nb"}, {"internship": "yes"}, {"updated_within": 7.0},
    {"updated_within": True}, {"updated_within": "7"}, {"updated_within": []}])
def test_invalid_filters_fail_before_network(options):
    values = {"career": "ai_ml", **options}
    def forbidden(request): pytest.fail("Invalid filters must not contact a provider")
    with httpx.Client(transport=httpx.MockTransport(forbidden)) as client:
        with pytest.raises(ValueError):
            search_employer_jobs(client=client, **values)


def test_naive_clock_and_excessive_boards_fail_before_fetch():
    with pytest.raises(ValueError):
        search_employer_jobs("ai_ml", now=NOW.replace(tzinfo=None))
    with pytest.raises(ValueError):
        search_employer_jobs("ai_ml", boards=load_employer_boards() * 2)


@pytest.mark.parametrize("change", [{"token": "../other"}, {"job_base_url": "https://other.example/jobs/"},
    {"careers_url": "http://www.samsara.com/careers"}])
def test_invalid_board_configuration_is_rejected(change):
    data = load_employer_boards()[0].model_dump()
    with pytest.raises(ValidationError):
        EmployerBoard.model_validate({**data, **change})


def test_default_search_revalidates_and_cache_reuse_is_explicit():
    calls, state = [], {}
    def fetch(*a, **k): calls.append(1); return cached_result()
    first = request_opportunities(state, "ai_ml", "", False, public_search=fetch, now=NOW)
    request_opportunities(state, "ai_ml", "", False, public_search=fetch, now=NOW + timedelta(seconds=1))
    assert len(calls) == 2
    reused = request_opportunities(state, "ai_ml", "", False, public_search=fetch, now=NOW + timedelta(seconds=2), reuse=True)
    assert len(calls) == 2 and reused.cache_state == "reused" and first.cache_state == "fresh"
    assert reused.retrieved_at == first.retrieved_at


@pytest.mark.parametrize("change", [{"career": "embedded"}, {"location": "Tucson"}, {"internship": True},
    {"updated_within": 7}, {"provider": "adzuna"}])
def test_cache_identity_includes_all_query_filters_and_source(change):
    calls, state = [], {}
    def public(*a, **k): calls.append("greenhouse"); return cached_result()
    def adzuna(*a, **k): calls.append("adzuna"); return cached_result("adzuna")
    options = {"career": "ai_ml", "location": "", "internship": False, "provider": "greenhouse"}
    request_opportunities(state, **options, public_search=public, adzuna_search=adzuna, now=NOW)
    request_opportunities(state, **{**options, **change}, public_search=public, adzuna_search=adzuna, now=NOW, reuse=True)
    assert len(calls) == 2


@pytest.mark.parametrize("offset", [-1, CACHE_SECONDS])
def test_future_or_expired_cache_is_not_reused(offset):
    state = {}
    calls = []
    def fetch(*a, **k): calls.append(1); return cached_result()
    request_opportunities(state, "ai_ml", "", False, public_search=fetch, now=NOW)
    request_opportunities(state, "ai_ml", "", False, public_search=fetch, now=NOW + timedelta(seconds=offset), reuse=True)
    assert len(calls) == 2


def test_failure_clears_previous_visible_results_without_silent_stale_fallback():
    state = {}
    request_opportunities(state, "ai_ml", "", False, public_search=lambda *a, **k: cached_result(), now=NOW)
    def fail(*a, **k): raise RuntimeError("Unavailable")
    with pytest.raises(RuntimeError):
        request_opportunities(state, "ai_ml", "", False, public_search=fail, now=NOW)
    assert "job_result" not in state


def test_invalid_search_clears_previous_visible_results_before_validation():
    state = {"job_result": cached_result()}
    with pytest.raises(ValueError):
        request_opportunities(state, "ai_ml", "x" * 121, False, now=NOW)
    assert "job_result" not in state


def test_wrong_provider_result_cannot_be_cached_or_displayed():
    state = {}
    with pytest.raises(ValueError):
        request_opportunities(state, "ai_ml", "", False, public_search=lambda *a, **k: cached_result("adzuna"), now=NOW)
    assert "job_result" not in state and "jobs_cache" not in state


def test_corrupt_cache_rebuilds_and_does_not_expose_credentials():
    state = {"jobs_cache": "invalid"}
    result = request_opportunities(state, "ai_ml", "", False, public_search=lambda *a, **k: cached_result(), reuse=True, now=NOW,
                                   app_id="private-id", app_key="private-key")
    assert result.cache_state == "fresh" and "private-key" not in repr(state)


@pytest.mark.parametrize("options", [{"career": "invalid"}, {"location": "x\ny"}, {"internship": "true"}])
def test_legacy_adzuna_filters_are_validated_before_credentialed_requests(options):
    def forbidden(*a, **k): pytest.fail("Invalid inputs must not be sent")
    with pytest.raises(ValueError):
        search_jobs("fixture-id", "fixture-key", opener=forbidden, **{"career": "ai_ml", "location": "Tucson", **options})


def test_legacy_adzuna_response_download_is_bounded(monkeypatch):
    monkeypatch.setattr("src.jobs.MAX_JOB_BYTES", 10)
    with pytest.raises(RuntimeError):
        search_jobs("fixture-id", "fixture-key", "ai_ml", "Tucson", opener=lambda *a, **k: io.BytesIO(b"x" * 11))


def test_public_checker_saves_a_real_source_contract_without_models(monkeypatch, tmp_path):
    import json
    from scripts import check_opportunities as cli
    output = tmp_path / "check.json"
    result = cached_result()
    result.checks = [{"status": "verified", "employer": "Fixture", "valid_posts": 0}]
    result.total_matches = 0
    monkeypatch.setattr(cli, "search_employer_jobs", lambda *a, **k: result)
    monkeypatch.setattr("sys.argv", ["check_opportunities", "--output", str(output)])
    assert cli.main() == 0
    report = json.loads(output.read_text())
    assert report["model_calls"] == 0 and report["credentials_used"] is False
    assert report["result"]["provider"] == "greenhouse" and report["passed"]


def test_public_checker_retains_failed_observation(monkeypatch, tmp_path):
    import json
    from scripts import check_opportunities as cli
    output = tmp_path / "failed.json"
    def fail(*args, **kwargs): raise RuntimeError("private diagnostic")
    monkeypatch.setattr(cli, "search_employer_jobs", fail)
    monkeypatch.setattr("sys.argv", ["check_opportunities", "--output", str(output)])
    assert cli.main() == 1
    report = json.loads(output.read_text())
    assert report["passed"] is False and "private diagnostic" not in output.read_text()
