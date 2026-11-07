"""One deferred posting action bound to the search and page that displayed it."""

from dataclasses import dataclass

from .jobs import JobSearchResult


@dataclass(frozen=True)
class PostingDetailIntent:
    posting_id:str
    result:JobSearchResult
    page:int


def queue_posting_detail(state,posting_id,displayed_result):
    if (state.get("job_result") is not displayed_result or not isinstance(displayed_result,JobSearchResult)
            or displayed_result.provider!="greenhouse"
            or sum(job.get("id")==posting_id for job in displayed_result.listings)!=1):
        return False
    state.pop("job_detail",None)
    state.pop("job_detail_error",None)
    state["pending_posting_detail"]=PostingDetailIntent(posting_id,displayed_result,displayed_result.page)
    return True


def take_posting_detail(state):
    intent=state.pop("pending_posting_detail",None)
    if (not isinstance(intent,PostingDetailIntent) or state.get("job_result") is not intent.result
            or intent.result.page!=intent.page
            or sum(job.get("id")==intent.posting_id for job in intent.result.listings)!=1):
        return None
    return intent
