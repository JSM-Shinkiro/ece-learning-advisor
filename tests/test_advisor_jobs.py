"""Deterministic request races; events replace provider/network timing guesses."""

from threading import BoundedSemaphore, Event

import pytest

from src.advisor_jobs import (AdvisorBusy, AdvisorJob, collect_advisor_job, discard_advisor_job,
                             keep_source_plan, start_advisor_job)
from src.controller import run_advisor
from src.models import StudentProfile
from src.progress import AdvisorCancelled
from src.service import recommend
from src.session import apply_profile
from conftest import FakeProvider


def start(catalog, profile=None, **options):
    return start_advisor_job(catalog, profile or StudentProfile(), slots=BoundedSemaphore(1), **options)


def test_source_plan_is_published_before_provider_finishes_and_is_not_mutated(catalog, tmp_path):
    entered, release = Event(), Event()
    class Provider(FakeProvider):
        closed = 0
        def generate(self, context):
            entered.set()
            assert release.wait(5)
            return super().generate(context)
        def close(self): self.closed += 1
    provider=Provider()
    job=start(catalog,api_key="controlled-private",use_ai=True,method="keyword",refresh_sources=False,
              cache_dir=tmp_path,provider_factory=lambda *a,**k:provider)
    try:
        assert entered.wait(5)
        snapshot=job.snapshot(); preview=snapshot.result
        assert not snapshot.done and preview.context.allowed_record_ids and not preview.generation_complete
        assert preview.trace["early_source_plan"] and preview.trace["source_refresh"]["enabled"] is False
        trace=repr(preview.trace)
        state={"profile":StudentProfile(),"advisor_job":job}
        assert collect_advisor_job(state,job) and state["result"] is preview
        release.set(); assert job.wait(5)
        assert collect_advisor_job(state,job)
        assert state["result"].generation_complete and "advisor_job" not in state
        assert repr(preview.trace)==trace and not preview.generation_complete
        assert provider.closed==1
        assert "controlled-private" not in repr(job) + repr(state["advisor_activity"])
    finally:
        release.set(); job.wait(5)


def test_replaced_request_cannot_publish_after_new_profile_result(catalog):
    entered, release = Event(), Event()
    def old_runner(cat, profile, **options):
        entered.set(); assert release.wait(5)
        return recommend(cat,profile)
    old=start(catalog,runner=old_runner)
    try:
        assert entered.wait(5)
        state={"profile":StudentProfile(),"advisor_job":old}
        newer=StudentProfile(career_id="embedded",interests="Newer profile")
        apply_profile(state,newer)
        latest=recommend(catalog,newer)
        state["result"]=latest
        release.set(); assert old.wait(5)
        assert not collect_advisor_job(state,old)
        assert state["result"] is latest and old.snapshot().result is None
    finally:
        release.set(); old.wait(5)


def test_profile_guard_rejects_a_direct_change_even_without_transition_helper(catalog):
    profile=StudentProfile(); job=AdvisorJob(profile)
    job.publish(recommend(catalog,profile),done=True)
    state={"profile":StudentProfile(career_id="embedded"),"advisor_job":job}
    assert collect_advisor_job(state,job) and "result" not in state and "advisor_job" not in state
    assert job.is_cancelled()


def test_keeping_source_plan_discards_late_answer_and_closes_provider(catalog,tmp_path):
    entered, release=Event(),Event()
    class Provider(FakeProvider):
        closed=0
        def generate(self,context):
            entered.set(); assert release.wait(5)
            return super().generate(context)
        def close(self): self.closed+=1
    provider=Provider()
    job=start(catalog,api_key="controlled",use_ai=True,method="keyword",refresh_sources=False,
              cache_dir=tmp_path,provider_factory=lambda *a,**k:provider)
    try:
        assert entered.wait(5)
        state={"profile":StudentProfile(),"advisor_job":job};collect_advisor_job(state,job)
        preview=state["result"];keep_source_plan(state)
        release.set();assert job.wait(5)
        assert not collect_advisor_job(state,job) and state["result"] is preview
        assert not preview.generation_complete and provider.closed==1 and "stopped" in state["advisor_activity"]["notice"]
    finally:
        release.set();job.wait(5)


def test_cancel_during_source_work_prevents_provider_initialization(catalog,tmp_path):
    from src.sources import CatalogRefresh
    entered,release=Event(),Event()
    def sources(cat,profile,**options):
        entered.set(); assert release.wait(5)
        return CatalogRefresh(cat.model_copy(deep=True))
    def forbidden(*a,**k): pytest.fail("Superseded source work must not start a provider")
    job=start(catalog,api_key="controlled",use_ai=True,source_refresher=sources,provider_factory=forbidden,cache_dir=tmp_path)
    try:
        assert entered.wait(5);job.cancel();release.set();assert job.wait(5)
        assert job.snapshot().cancelled and job.snapshot().result is None
    finally:
        release.set();job.wait(5)


def test_admission_is_bounded_and_cancel_does_not_release_a_running_slot(catalog):
    slots=BoundedSemaphore(1);entered,release=Event(),Event()
    def runner(cat,profile,**options):
        entered.set(); assert release.wait(5)
        return recommend(cat,profile)
    job=start_advisor_job(catalog,StudentProfile(),runner=runner,slots=slots)
    try:
        assert entered.wait(5);job.cancel()
        with pytest.raises(AdvisorBusy):start_advisor_job(catalog,StudentProfile(),runner=runner,slots=slots)
        release.set();assert job.wait(5)
        next_job=start_advisor_job(catalog,StudentProfile(),runner=runner,slots=slots)
        assert next_job.wait(5)
    finally:
        release.set();job.wait(5)


@pytest.mark.parametrize("after_preview",[False,True])
def test_unexpected_worker_error_is_terminal_and_sanitized(catalog,after_preview):
    def runner(cat,profile,**options):
        if after_preview:options["on_plan"](recommend(cat,profile))
        raise OSError("controlled-private-api-key-and-profile")
    job=start(catalog,runner=runner);assert job.wait(5)
    state={"profile":StudentProfile(),"advisor_job":job};collect_advisor_job(state,job)
    assert "advisor_job" not in state
    assert ("result" in state)==after_preview
    assert state["advisor_activity"]["error"] != after_preview
    assert "private" not in repr(state["advisor_activity"]) + repr(job)


def test_two_sessions_can_only_collect_their_own_job(catalog):
    a,b=StudentProfile(),StudentProfile(career_id="embedded")
    one,two=AdvisorJob(a),AdvisorJob(b)
    one.publish(recommend(catalog,a),done=True);two.publish(recommend(catalog,b),done=True)
    first,second={"profile":a,"advisor_job":one},{"profile":b,"advisor_job":two}
    assert not collect_advisor_job(first,two) and not collect_advisor_job(second,one)
    assert collect_advisor_job(first,one) and collect_advisor_job(second,two)
    assert first["result"].context.profile==a and second["result"].context.profile==b


def test_thread_start_failure_releases_admission(catalog,monkeypatch):
    slots=BoundedSemaphore(1)
    def fail(*a,**k):raise RuntimeError("controlled thread start failure")
    monkeypatch.setattr("src.advisor_jobs.Thread.start",fail)
    with pytest.raises(RuntimeError):start_advisor_job(catalog,StudentProfile(),slots=slots)
    assert slots.acquire(blocking=False)
    slots.release()


def test_early_plan_observer_failure_does_not_retry_sources_or_provider(catalog,tmp_path):
    provider=FakeProvider();provider.close=lambda:None
    seen=[]
    def broken(result):
        seen.append(1);raise ValueError("controlled private preview observer")
    result=run_advisor(catalog,StudentProfile(),api_key="controlled",use_ai=True,refresh_sources=False,
        cache_dir=tmp_path,provider_factory=lambda *a,**k:provider,on_plan=broken)
    assert result.generation_complete and seen==[1] and result.trace["early_plan"]["observer_failed"]
    assert "private" not in repr(result.trace["early_plan"])
