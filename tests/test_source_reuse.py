"""Public-cache reuse controls: HTTP counts, freshness and academic outcomes."""

from datetime import timedelta
import json

import httpx
import pytest

from src.controller import run_advisor
from src.models import Completion, SourceCheck, StudentProfile
from src.rules import evaluate_course
from src.source_reuse import RecentSourceChecks
from src.sources import CachedCourse, refresh_catalog
from test_sources import NOW, course_page, fixture_client, one_course
from test_rule_sources import http_fixture, rule_catalog
from test_resource_sources import client_for as resource_client, resource_catalog
from test_discovery import client_for as discovery_client, plans, new_courses


def test_repeat_update_reuses_public_pages_but_recomputes_profile_plan(one_course, tmp_path):
    seen = []
    with fixture_client(one_course, seen=seen) as client:
        def refresh(catalog, profile, **kwargs):
            return refresh_catalog(catalog, profile, client=client, now=NOW, **kwargs)
        first = run_advisor(one_course, StudentProfile(), source_refresher=refresh, source_cache_dir=tmp_path)
        second = run_advisor(one_course, StudentProfile(completed=[Completion(course_code="ECE101")]),
            source_refresher=refresh, source_cache_dir=tmp_path)
    assert seen == ["ECE101"]
    assert first.context.allowed_record_ids and not second.context.allowed_record_ids
    check = second.trace["source_refresh"]["checks"][0]
    assert check["status"] == "recent_cache" and check["http_status"] is None and not check["attempts"]
    assert check["last_checked_at"] == first.trace["source_refresh"]["checks"][0]["last_checked_at"]
    assert second.trace["source_refresh"]["reuse_window_seconds"] == 300


@pytest.mark.parametrize("elapsed,reuse,expected_calls", [(299,300,1),(300,300,2),(-1,300,2),(1,0,2)])
def test_expiry_future_clock_and_force_check(one_course, tmp_path, elapsed, reuse, expected_calls):
    seen = []
    with fixture_client(one_course, seen=seen) as client:
        refresh_catalog(one_course, StudentProfile(), client=client, cache_dir=tmp_path, now=NOW)
        second = refresh_catalog(one_course, StudentProfile(), client=client, cache_dir=tmp_path,
            now=NOW+timedelta(seconds=elapsed), reuse_seconds=reuse)
    assert len(seen) == expected_calls
    assert (second.checks[0].status == "recent_cache") == (expected_calls == 1)


def test_manual_recheck_updates_changed_source_and_revokes_old_lease(one_course, tmp_path):
    with fixture_client(one_course) as client:
        refresh_catalog(one_course, StudentProfile(), client=client, cache_dir=tmp_path, now=NOW)
    calls = []
    def respond(request):
        calls.append(1)
        return httpx.Response(200, text=course_page(one_course.records[0], summary="Changed public description."),
                              headers={"Content-Type":"text/html"})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        fresh = refresh_catalog(one_course, StudentProfile(), client=client, cache_dir=tmp_path,
                                now=NOW+timedelta(seconds=1), reuse_seconds=0)
        reused = refresh_catalog(one_course, StudentProfile(), client=client, cache_dir=tmp_path,
                                 now=NOW+timedelta(seconds=2), reuse_seconds=300)
    assert calls == [1] and fresh.checks[0].content_changed and reused.checks[0].status == "recent_cache"
    assert reused.catalog.records[0].summary == "Changed public description."


def test_failed_force_check_cannot_be_followed_by_false_freshness(rule_catalog, tmp_path):
    profile = StudentProfile(completed=[Completion(course_code="ECE101",grade="B")])
    with http_fixture(rule_catalog) as client:
        first = refresh_catalog(rule_catalog, profile, client=client, cache_dir=tmp_path, now=NOW)
    assert evaluate_course(first.catalog.records[0],profile).status == "satisfied"
    seen = []
    with http_fixture(rule_catalog, course_status=404, program_status=404, seen=seen) as client:
        failed = refresh_catalog(rule_catalog, profile, client=client, cache_dir=tmp_path,
                                 now=NOW+timedelta(seconds=1), reuse_seconds=0)
        count = len(seen)
        retry = refresh_catalog(rule_catalog, profile, client=client, cache_dir=tmp_path,
                                now=NOW+timedelta(seconds=2), reuse_seconds=300)
    assert count > 0 and len(seen) == 2 * count
    for result in (failed,retry):
        assert all(c.status == "stale_cache" and c.last_checked_at == NOW for c in result.checks)
        assert evaluate_course(result.catalog.records[0],profile).status == "unknown"


def test_recent_rules_still_require_exact_reviewed_statement(rule_catalog, tmp_path):
    profile=StudentProfile(completed=[Completion(course_code="ECE101",grade="B")])
    with http_fixture(rule_catalog) as client:
        first=refresh_catalog(rule_catalog,profile,client=client,cache_dir=tmp_path,now=NOW)
        second=refresh_catalog(rule_catalog,profile,client=client,cache_dir=tmp_path,now=NOW,reuse_seconds=300)
    assert evaluate_course(first.catalog.records[0],profile).status == "satisfied"
    assert evaluate_course(second.catalog.records[0],profile).status == "satisfied"
    assert all(c.status == "recent_cache" for c in second.checks)
    from test_rule_sources import program_page
    changed=program_page(rule_catalog.records[0],text="Changed condition requiring new review.")
    with http_fixture(rule_catalog,program=changed) as client:
        refresh_catalog(rule_catalog,profile,client=client,cache_dir=tmp_path,now=NOW,reuse_seconds=0)
        reused=refresh_catalog(rule_catalog,profile,client=client,cache_dir=tmp_path,now=NOW,reuse_seconds=300)
    assert all(c.status == "recent_cache" for c in reused.checks)
    assert evaluate_course(reused.catalog.records[0],profile).status == "unknown"


def test_resources_keep_original_dates_and_do_not_make_repeat_requests(resource_catalog, tmp_path):
    seen = []
    with resource_client(seen=seen) as client:
        first = refresh_catalog(resource_catalog, StudentProfile(), client=client, cache_dir=tmp_path,
                                resource_checks=True, now=NOW)
        count = len(seen)
        second = refresh_catalog(resource_catalog, StudentProfile(), client=client, cache_dir=tmp_path,
                                 resource_checks=True, now=NOW+timedelta(seconds=20), reuse_seconds=300)
    assert count > 0 and len(seen) == count
    assert all(c.status == "recent_cache" and c.last_checked_at == NOW and c.resolved_url for c in second.checks)
    assert [s.model_dump() for s in first.catalog.sources] == [s.model_dump() for s in second.catalog.sources]


def test_program_and_discovery_reuse_preserve_identity_and_unknown_rules(catalog, plans, new_courses, tmp_path):
    seen = []
    with discovery_client(catalog, plans, new_courses, seen=seen) as client:
        first = refresh_catalog(catalog, StudentProfile(), client=client, discovery_plans=plans, cache_dir=tmp_path, now=NOW)
        count = len(seen)
        second = refresh_catalog(catalog, StudentProfile(), client=client, discovery_plans=plans, cache_dir=tmp_path,
                                 now=NOW+timedelta(seconds=10), reuse_seconds=300)
    assert count > 0 and len(seen) == count
    assert all(c.status == "recent_cache" for c in second.checks)
    assert {r.record_id for r in first.catalog.records} == {r.record_id for r in second.catalog.records}
    assert all(evaluate_course(r,StudentProfile()).status == "unknown" for r in second.catalog.records if r.discovery)


@pytest.mark.parametrize("case", ["corrupt", "restart", "uncached_path"])
def test_disk_cache_alone_or_corrupt_cache_never_grants_recent_freshness(one_course, tmp_path, case, monkeypatch):
    seen = []
    with fixture_client(one_course, seen=seen) as client:
        refresh_catalog(one_course, StudentProfile(), client=client, cache_dir=tmp_path, now=NOW)
        path = next(tmp_path.glob("*.json"))
        if case == "corrupt":
            saved=json.loads(path.read_text()); saved["data"]["summary"]="Tampered evidence"; path.write_text(json.dumps(saved))
        elif case == "restart":
            monkeypatch.setattr("src.sources.recent_sources",RecentSourceChecks())
        else:
            other=tmp_path/"other"; other.mkdir(); (other/path.name).write_bytes(path.read_bytes()); tmp_path=other
        result=refresh_catalog(one_course,StudentProfile(),client=client,cache_dir=tmp_path,now=NOW,reuse_seconds=300)
    assert len(seen)==2 and result.checks[0].status != "recent_cache"
    assert "Tampered" not in result.catalog.records[0].summary


def test_monotonic_expiry_and_bounded_memory_do_not_extend_with_reads(one_course, tmp_path):
    with fixture_client(one_course) as client:
        refresh_catalog(one_course,StudentProfile(),client=client,cache_dir=tmp_path,now=NOW)
    saved=CachedCourse.model_validate_json(next(tmp_path.glob("*.json")).read_bytes())
    tick=[0.0]; cache=RecentSourceChecks(clock=lambda:tick[0],max_entries=2)
    def check(path):
        row=SourceCheck(source_id="catalog:ECE101",code="ECE101",url=saved.url,status="bundled_fallback",attempted_at=NOW)
        return cache.reuse(tmp_path/path,saved,row,300)
    cache.remember(tmp_path/"a",saved)
    tick[0]=299; assert check("a")
    tick[0]=300; assert not check("a")
    for key in ("a","b","c"): cache.remember(tmp_path/key,saved)
    assert len(cache.entries)==2 and not check("a") and check("b") and check("c")
