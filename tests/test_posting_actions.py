"""Deferred posting intents reject stale browser actions and in-flight returns."""

from dataclasses import replace

import pytest

from src.models import StudentProfile
from src.opportunity_details import request_posting_detail
from src.opportunity_pages import request_opportunity_page
from src.posting_actions import queue_posting_detail,take_posting_detail
from src.session import apply_profile
from test_opportunity_details import checked,search_state
from test_opportunity_pages import paged_result
from test_opportunities import post


def test_queue_clears_old_content_and_is_consumed_once_without_fetching():
    state=search_state();jobs=state["job_result"]
    state["job_detail"]=checked();state["job_detail_error"]="earlier"
    assert queue_posting_detail(state,jobs.listings[0]["id"],jobs)
    assert "job_detail" not in state and "job_detail_error" not in state
    intent=take_posting_detail(state)
    assert intent.result is jobs and intent.posting_id==jobs.listings[0]["id"]
    assert take_posting_detail(state) is None


def test_stale_click_from_an_identical_new_search_cannot_queue_or_clear_current_detail():
    state=search_state();old=state["job_result"]
    state["job_result"]=replace(old);current=checked();state["job_detail"]=current
    assert not queue_posting_detail(state,old.listings[0]["id"],old)
    assert take_posting_detail(state) is None and state["job_detail"] is current


@pytest.mark.parametrize("transition",["profile","page","search"])
def test_pending_intent_is_discarded_after_scope_transition(transition):
    state={"job_result":paged_result()};jobs=state["job_result"]
    assert queue_posting_detail(state,jobs.listings[0]["id"],jobs)
    if transition=="profile":apply_profile(state,StudentProfile(career_id="embedded"))
    elif transition=="page":request_opportunity_page(state,1)
    else:state["job_result"]=replace(jobs)
    assert take_posting_detail(state) is None


@pytest.mark.parametrize("transition",["profile","page","search"])
def test_late_posting_check_cannot_overwrite_a_new_scope(transition):
    state={"job_result":paged_result()};jobs=state["job_result"];posting_id=jobs.listings[0]["id"]
    newer=checked()
    def fetch(job,**kwargs):
        if transition=="profile":apply_profile(state,StudentProfile(career_id="embedded"))
        elif transition=="page":request_opportunity_page(state,1)
        else:state["job_result"]=replace(jobs)
        state["job_detail"]=newer
        result=checked({**post(identity=int(job["id"].rsplit(":",1)[-1])),"content":"Late verified posting."},job=job)
        assert result.status=="verified"
        return result
    assert request_posting_detail(state,posting_id,fetcher=fetch) is None
    assert state["job_detail"] is newer
