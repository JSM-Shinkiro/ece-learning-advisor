"""Student title filters and reviewed third-board coverage, not qualification inference."""

from dataclasses import replace
import json

import httpx
import pytest
from pydantic import ValidationError

import src.opportunities as opportunities
from src.jobs import JobSearchResult
from src.opportunities import (EmployerBoard, OpportunitySearchError, board_scope_hash, load_employer_boards,
    request_opportunities, search_employer_jobs, valid_posting_url)
from test_opportunities import NOW, cached_result, client_for, one_board, post


@pytest.mark.parametrize("title", ["New Grad Machine Learning Engineer", "Machine Learning Engineer - New Graduate (2027)",
    "University Graduate AI Research Scientist", "Recent Graduate Embedded Software Engineer", "Entry-Level Firmware Engineer",
    "Early Career FPGA Engineer", "Junior Computer Vision Engineer", "Machine–Learning Engineer — New‐Grad"])
def test_explicit_early_career_title_labels_match(title):
    career = "embedded" if any(t in title for t in ["Embedded", "Firmware", "FPGA"]) else "ai_ml"
    result = one_board([post(title=title)], career=career, early_career=True)
    assert len(result.listings) == 1 and result.listings[0]["title"] == title
    assert result.role_filter == "early_career" and result.source_scope_hash


@pytest.mark.parametrize("title", ["Senior Machine Learning Engineer - New Grad Mentor", "Sr. AI Engineer, Early Career Team",
    "Staff Embedded Engineer - University Graduate Team", "Principal AI Engineer, Junior Mentorship",
    "Lead Firmware Engineer - Early Career", "AI Engineering Manager - New Grad Team", "Director, AI Engineering - Entry Level",
    "Head of AI Engineering - New Graduate Team", "Machine Learning Engineer I", "Graduate Research Scientist",
    "AI Engineer Intern - New Grad", "Junior Firmware Co-Op Engineer", "AI Sales Engineer - Entry Level",
    "Junior Hardware Recruiter", "New Grade Machine Learning Engineer", "Machine Learning Engineer - Juniority"])
def test_unlabeled_senior_intern_and_unrelated_roles_do_not_pass_the_new_filter(title):
    career = "embedded" if any(t in title for t in ["Embedded", "Firmware", "Hardware"]) else "ai_ml"
    assert not one_board([post(title=title)], career=career, early_career=True).listings


def test_all_levels_preserves_senior_results_and_internships_have_a_separate_filter():
    senior = post(title="Senior Firmware Engineer")
    assert one_board([senior], career="embedded").listings
    assert not one_board([senior], career="embedded", early_career=True).listings
    intern = post(title="Firmware Engineer Co‑Op")
    result = one_board([intern], career="embedded", internship=True)
    assert result.listings and result.role_filter == "internship"
    assert not one_board([intern], career="embedded", early_career=True).listings


@pytest.mark.parametrize("options", [{"early_career": "true"}, {"early_career": 1}, {"early_career": None},
    {"early_career": []}, {"early_career": True, "internship": True}])
def test_invalid_or_conflicting_role_filters_stop_before_network(options):
    def forbidden(request): pytest.fail("Invalid role filters must not make requests")
    with httpx.Client(transport=httpx.MockTransport(forbidden)) as client:
        with pytest.raises(ValueError): search_employer_jobs("ai_ml", client=client, **options)


def test_early_career_composes_with_local_direction_location_and_age_filters():
    items = [post(identity=1, title="Junior Firmware Engineer", location={"name": "Tucson, AZ"}),
        post(identity=2, title="Junior Firmware Engineer", location={"name": "Remote - US"}),
        post(identity=3, title="Junior Firmware Engineer", location={"name": "Tucson, AZ"}, updated_at="2026-08-01T12:00:00Z"),
        post(identity=4, title="Junior Machine Learning Engineer", location={"name": "Tucson, AZ"})]
    result = one_board(items, career="embedded", location="tucson", updated_within=7, early_career=True)
    assert [p["id"].rsplit(":", 1)[-1] for p in result.listings] == ["1"]


def test_early_career_and_location_filters_never_enter_public_get_requests():
    boards, seen = load_employer_boards(), []
    with client_for({b.token: {"jobs": [post(b, title="Junior Firmware Engineer")]} for b in boards}, seen) as client:
        result = search_employer_jobs("embedded", location="private-place-sentinel", early_career=True, client=client, now=NOW)
    assert len(seen) == 3 and not result.listings
    assert all(not request.url.query and request.method == "GET" and "private-place-sentinel" not in str(request.url) for request in seen)


def test_third_board_matches_its_reviewed_hosted_identity_and_supports_both_hostnames():
    board = load_employer_boards()[-1]
    assert board.token == "andurilindustries" and board.employer == "Anduril Industries"
    for host in ["boards.greenhouse.io", "job-boards.greenhouse.io"]:
        url = f"https://{host}/andurilindustries/jobs/12?gh_jid=12"
        assert valid_posting_url(url, board, "12") == url


@pytest.mark.parametrize("changes", [{"job_base_url": "https://job-boards.greenhouse.io/other/jobs/"},
    {"job_base_url": "https://job-boards.greenhouse.io/andurilindustries/not-jobs/"},
    {"job_base_url": "https://job-boards.greenhouse.io/andurilindustries/jobs/", "url_style": "id_query"},
    {"job_base_url": "https://job-boards.greenhouse.io.evil.example/andurilindustries/jobs/"}])
def test_hosted_board_exception_needs_the_exact_reviewed_token_path(changes):
    data = load_employer_boards()[-1].model_dump()
    with pytest.raises(ValidationError): EmployerBoard.model_validate({**data, **changes})


def test_third_board_failure_retains_other_boards_without_relaxing_the_three_board_cap():
    boards = load_employer_boards()
    payloads = {b.token: {"jobs": [post(b)]} for b in boards}
    payloads[boards[-1].token] = httpx.Response(503)
    with client_for(payloads) as client:
        result = search_employer_jobs("ai_ml", client=client, now=NOW)
    assert len(result.checks) == 3 and len(result.listings) == 2 and result.issues
    assert result.checks[-1]["status"] == "unavailable"
    with pytest.raises(ValueError): search_employer_jobs("ai_ml", boards=[*boards, boards[0]])


def test_all_board_failure_remains_an_error_for_the_new_role_filter():
    boards = load_employer_boards()
    with client_for({b.token: httpx.Response(429) for b in boards}) as client:
        with pytest.raises(OpportunitySearchError) as caught:
            search_employer_jobs("ai_ml", early_career=True, client=client, now=NOW)
    assert len(caught.value.checks) == 3 and all(c["http_status"] == 429 for c in caught.value.checks)


def test_role_filter_is_part_of_explicit_reuse_identity():
    state, calls = {}, []
    def search(*a, **kwargs):
        calls.append(kwargs)
        return replace(cached_result(), role_filter="early_career" if kwargs["early_career"] else "all")
    all_roles = request_opportunities(state, "ai_ml", "", False, public_search=search, now=NOW)
    early = request_opportunities(state, "ai_ml", "", False, early_career=True, reuse=True, public_search=search, now=NOW)
    reused = request_opportunities(state, "ai_ml", "", False, early_career=True, reuse=True, public_search=search, now=NOW)
    assert len(calls) == 2 and all_roles.role_filter == "all" and early.role_filter == reused.role_filter == "early_career"
    assert reused.cache_state == "reused" and reused.retrieved_at == early.retrieved_at


@pytest.mark.parametrize("change", ["boards", "policy"])
def test_changed_board_scope_or_policy_invalidates_even_opted_in_reuse(monkeypatch, change):
    boards = load_employer_boards()
    state, calls = {}, []
    def search(*a, **kwargs): calls.append(kwargs["boards"]); return cached_result()
    request_opportunities(state, "ai_ml", "", False, public_search=search, now=NOW)
    if change == "boards": monkeypatch.setattr(opportunities, "load_employer_boards", lambda: boards[:2])
    else: monkeypatch.setattr(opportunities, "OPPORTUNITY_POLICY_VERSION", "controlled-policy-change")
    request_opportunities(state, "ai_ml", "", False, public_search=search, now=NOW, reuse=True)
    assert len(calls) == 2


def test_fetch_uses_the_exact_board_snapshot_bound_into_the_cache_key(monkeypatch):
    boards = load_employer_boards()
    reads = []
    def load(): reads.append(1); return boards
    monkeypatch.setattr(opportunities, "load_employer_boards", load)
    def search(*a, **kwargs):
        assert kwargs["boards"] is boards
        return replace(cached_result(), source_scope_hash=board_scope_hash(boards))
    state = {}
    result = request_opportunities(state, "ai_ml", "", False, public_search=search, now=NOW)
    assert reads == [1] and state["jobs_cache"]["key"][-1] == result.source_scope_hash


def test_wrong_response_scope_is_not_displayed_or_cached():
    state = {}
    with pytest.raises(ValueError, match="configured boards"):
        request_opportunities(state, "ai_ml", "", False, now=NOW,
            public_search=lambda *a, **k: replace(cached_result(), source_scope_hash="f" * 64))
    assert "job_result" not in state and "jobs_cache" not in state


def test_optional_adzuna_does_not_silently_claim_the_new_title_filter():
    state = {"job_result": cached_result("adzuna")}
    def forbidden(*a, **k): pytest.fail("Unsupported title filter must not reach credentials or provider")
    with pytest.raises(ValueError):
        request_opportunities(state, "ai_ml", "", False, provider="adzuna", early_career=True,
            adzuna_search=forbidden, app_id="fixture-id", app_key="fixture-key", now=NOW)
    assert "job_result" not in state


def test_cli_exposes_the_role_filter_and_reports_the_result(monkeypatch, tmp_path):
    from scripts import check_opportunities as cli
    calls = []
    def search(*a, **k): calls.append((a, k)); return replace(cached_result(), role_filter="early_career")
    monkeypatch.setattr(cli, "search_employer_jobs", search)
    output = tmp_path / "early.json"
    monkeypatch.setattr("sys.argv", ["check", "--career", "embedded", "--early-career", "--output", str(output)])
    assert cli.main() == 0
    report = json.loads(output.read_text())
    assert calls[0][1]["early_career"] is True and report["filters"]["early_career"] is True
    assert report["result"]["role_filter"] == "early_career" and report["model_calls"] == 0


def test_cli_rejects_conflicting_title_filters_before_any_search(monkeypatch):
    from scripts import check_opportunities as cli
    monkeypatch.setattr("sys.argv", ["check", "--internship", "--early-career"])
    monkeypatch.setattr(cli, "search_employer_jobs", lambda *a, **k: pytest.fail("Conflicting filters must not run"))
    with pytest.raises(SystemExit) as result: cli.main()
    assert result.value.code == 2
