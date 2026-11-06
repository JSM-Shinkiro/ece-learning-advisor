"""Bounded public snapshots and local navigation, with real fetching forbidden."""

import copy
import json
from dataclasses import replace

import httpx
import pytest

from src.jobs import MAX_SNAPSHOT_MATCHES, OPPORTUNITY_PAGE_SIZE
from src.models import StudentProfile
from src.opportunities import load_employer_boards, request_opportunities, search_employer_jobs
from src.opportunity_details import request_posting_detail
from src.opportunity_pages import page_info, request_opportunity_page
from src.session import apply_profile
from test_opportunities import NOW, cached_result, client_for, post


def paged_result(count=23, *, seen=None, items=None):
    boards = load_employer_boards()
    payloads = {b.token: {"jobs": []} for b in boards}
    payloads[boards[0].token] = {"jobs": items if items is not None else [
        post(identity=i, title="Machine Learning Engineer " + str(i)) for i in range(1, count + 1)]}
    with client_for(payloads, seen) as client:
        return search_employer_jobs("ai_ml", client=client, now=NOW)


def block_http(monkeypatch):
    def forbidden(*a, **k): pytest.fail("Paging must not fetch sources or providers")
    monkeypatch.setattr(httpx.Client, "send", forbidden)
    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr("src.opportunities.search_employer_jobs", forbidden)
    monkeypatch.setattr("src.opportunity_details.fetch_posting_detail", forbidden)


def test_browse_all_pages_without_requests_reordering_or_mutating_the_original_cache(monkeypatch):
    seen = []
    first = paged_result(seen=seen)
    state = {"job_result": first, "jobs_cache": {"result": first}}
    original = copy.deepcopy(first)
    block_http(monkeypatch)
    ids = []
    for number, expected_count in [(0, 10), (1, 10), (2, 3)]:
        result = request_opportunity_page(state, number)
        ids.extend(j["id"] for j in result.listings)
        info = page_info(result)
        assert len(result.listings) == expected_count and info.number == number + 1 and info.pages == 3
        assert result.retrieved_at == first.retrieved_at and result.checks == first.checks
        assert result.query == first.query and result.location == first.location
        assert result.role_filter == first.role_filter and result.source_scope_hash == first.source_scope_hash
        assert result.cache_state == "fresh" and result.issues == first.issues
    assert ids == [j["id"] for j in first.snapshot_listings] and len(set(ids)) == 23
    assert len(seen) == 3 and first == original and state["jobs_cache"]["result"] is first
    assert request_opportunity_page(state, 0).listings == original.listings


@pytest.mark.parametrize("count,expected_pages,truncated", [(0, 1, False), (1, 1, False), (10, 1, False),
    (11, 2, False), (200, 20, False), (201, 20, True)])
def test_empty_exact_partial_and_capped_snapshots_have_consistent_ranges(count, expected_pages, truncated):
    result = paged_result(count)
    info = page_info(result)
    assert info.pages == expected_pages and info.truncated is truncated and info.total_matches == count
    assert info.retained == min(count, MAX_SNAPSHOT_MATCHES)
    assert len(result.listings) == min(count, OPPORTUNITY_PAGE_SIZE)
    state = {"job_result": result}
    last = page_info(request_opportunity_page(state, expected_pages - 1))
    assert last.last == min(count, MAX_SNAPSHOT_MATCHES)
    assert last.first == ((expected_pages - 1) * OPPORTUNITY_PAGE_SIZE + 1 if count else 0)


def test_filtering_and_deduplication_precede_snapshot_cap_and_paging():
    # Irrelevant earlier source rows cannot consume the 200 retained slots.
    irrelevant = [post(identity=i, title="Marketing Manager") for i in range(1, 251)]
    wanted = [post(identity=i, title="Machine Learning Engineer Intern") for i in range(251, 266)]
    result = paged_result(items=[*irrelevant, *wanted, wanted[0]])
    state = {"job_result": result}
    assert result.total_matches == 15 and len(result.snapshot_listings) == 15
    second = request_opportunity_page(state, 1)
    assert len(second.listings) == 5 and all("Intern" in j["title"] for j in second.listings)


@pytest.mark.parametrize("page", [-1, 3, True, "1", None, 1.0])
def test_unavailable_or_noninteger_pages_fail_locally_without_changing_the_search(monkeypatch, page):
    first = paged_result()
    state = {"job_result": first, "job_detail": object(), "job_detail_error": "old"}
    block_http(monkeypatch)
    with pytest.raises(ValueError): request_opportunity_page(state, page)
    assert state["job_result"] is first and "job_detail" not in state and "job_detail_error" not in state


@pytest.mark.parametrize("change", [{"total_matches": True}, {"total_matches": 24}, {"total_matches": 12001},
    {"page": -1}, {"page": True}, {"listings": []}, {"provider": "adzuna"}])
def test_corrupt_snapshot_counts_alignment_and_provider_are_rejected(change):
    result = replace(paged_result(), **change)
    with pytest.raises(ValueError): page_info(result)


@pytest.mark.parametrize("mutation", ["duplicate_id", "missing_field", "wrong_record_type", "excessive"])
def test_corrupt_retained_records_are_rejected_even_on_unvisited_pages(mutation):
    result = paged_result()
    if mutation == "duplicate_id": result.snapshot_listings[-1] = result.snapshot_listings[0]
    elif mutation == "missing_field": result.snapshot_listings[-1].pop("url")
    elif mutation == "wrong_record_type": result.snapshot_listings[-1] = None
    else: result.snapshot_listings = result.snapshot_listings * 10
    with pytest.raises(ValueError): request_opportunity_page({"job_result": result}, 1)


def test_changed_configuration_requires_a_new_search_before_navigation(monkeypatch):
    state = {"job_result": paged_result()}
    boards = load_employer_boards()
    boards[0].employer = "Changed configured employer"
    monkeypatch.setattr("src.opportunity_pages.load_employer_boards", lambda: boards)
    with pytest.raises(ValueError, match="settings changed"): request_opportunity_page(state, 1)
    assert state["job_result"].page == 0


def test_target_page_links_are_still_bound_to_the_configured_employer_and_id():
    result = paged_result()
    result.snapshot_listings[10]["url"] = "https://other.example/jobs/12"
    with pytest.raises(ValueError): request_opportunity_page({"job_result": result}, 1)


def test_browsing_clears_details_and_only_visible_page_postings_can_be_rechecked():
    from test_opportunity_details import checked
    state = {"job_result": paged_result(), "job_detail": checked()}
    first_id = state["job_result"].listings[0]["id"]
    request_opportunity_page(state, 1)
    assert "job_detail" not in state
    with pytest.raises(ValueError):
        request_posting_detail(state, first_id, fetcher=lambda *a, **k: pytest.fail("Hidden posting must not fetch"))
    job = state["job_result"].listings[0]
    calls = []
    def fetch(selected, **kwargs):
        calls.append(selected["id"])
        return checked({**post(identity=int(selected["id"].split(":")[-1])), "content": "Later-page requirements"}, job=selected)
    result = request_posting_detail(state, job["id"], fetcher=fetch)
    assert result.status == "verified" and calls == [job["id"]]


def test_new_search_and_explicit_cache_reuse_reset_to_first_page_and_clear_page_errors():
    state, calls = {}, []
    def search(*a, **k): calls.append(1); return paged_result()
    first = request_opportunities(state, "ai_ml", "", False, public_search=search, now=NOW)
    request_opportunity_page(state, 2)
    state["job_page_error"] = "old"
    reused = request_opportunities(state, "ai_ml", "", False, public_search=search, now=NOW, reuse=True)
    assert calls == [1] and reused.page == 0 and reused.cache_state == "reused"
    assert reused.listings == first.listings and reused.retrieved_at == first.retrieved_at
    assert "job_page_error" not in state
    request_opportunity_page(state, 1)
    fresh = request_opportunities(state, "ai_ml", "", False, public_search=search, now=NOW)
    assert calls == [1, 1] and fresh.page == 0 and fresh.cache_state == "fresh"


def test_failed_new_search_and_profile_transition_remove_the_entire_snapshot():
    state = {"job_result": paged_result(), "job_page_error": "old"}
    with pytest.raises(ValueError): request_opportunities(state, "invalid", "", False)
    assert "job_result" not in state and "job_page_error" not in state
    state.update(job_result=paged_result(), jobs_cache={"result": paged_result()}, job_page_error="old")
    apply_profile(state, StudentProfile())
    assert not {"job_result", "jobs_cache", "job_page_error"} & state.keys()


@pytest.mark.parametrize("provider", ["adzuna", "greenhouse"])
def test_legacy_unpaged_results_remain_compatible_but_cannot_invent_other_pages(provider):
    result = cached_result(provider)
    assert page_info(result) is None
    with pytest.raises(ValueError): request_opportunity_page({"job_result": result}, 1)


def test_cli_selects_second_page_without_serializing_all_retained_postings(monkeypatch, tmp_path):
    from scripts import check_opportunities as cli
    result, calls = paged_result(), []
    def search(*a, **k): calls.append(1); return result
    monkeypatch.setattr(cli, "search_employer_jobs", search)
    output = tmp_path / "page.json"
    monkeypatch.setattr("sys.argv", ["check", "--page", "2", "--output", str(output)])
    assert cli.main() == 0
    report = json.loads(output.read_text())
    assert calls == [1] and report["requested_page"] == 2 and report["result"]["page"] == 1
    assert report["pagination"]["first"] == 11 and report["pagination"]["last"] == 20
    assert report["result"]["retrieved_at"] == result.retrieved_at
    assert "snapshot_listings" not in report["result"] and report["model_calls"] == 0


def test_cli_unavailable_page_is_a_failure_without_a_fake_empty_result(monkeypatch, tmp_path):
    from scripts import check_opportunities as cli
    monkeypatch.setattr(cli, "search_employer_jobs", lambda *a, **k: paged_result(2))
    output = tmp_path / "missing.json"
    monkeypatch.setattr("sys.argv", ["check", "--page", "2", "--output", str(output)])
    assert cli.main() == 1
    report = json.loads(output.read_text())
    assert not report["passed"] and "result" not in report


def test_cli_rejects_out_of_bound_page_before_fetch(monkeypatch):
    from scripts import check_opportunities as cli
    monkeypatch.setattr(cli, "search_employer_jobs", lambda *a, **k: pytest.fail("Do not fetch"))
    monkeypatch.setattr("sys.argv", ["check", "--page", "21"])
    with pytest.raises(SystemExit) as result: cli.main()
    assert result.value.code == 2
