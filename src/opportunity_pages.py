"""Local pages of one bounded, dated employer-search snapshot; no fetching."""

from dataclasses import dataclass, replace

from .jobs import JobSearchResult, MAX_SNAPSHOT_MATCHES, OPPORTUNITY_PAGE_SIZE
from .opportunities import MAX_BOARDS, MAX_POSTS, board_scope_hash, load_employer_boards
from .opportunity_details import posting_binding


@dataclass(frozen=True)
class OpportunityPage:
    number: int
    pages: int
    first: int
    last: int
    retained: int
    total_matches: int
    truncated: bool


def page_info(result):
    """Validate page/snapshot alignment; older unpaged adapters return None."""
    if not isinstance(result, JobSearchResult):
        raise ValueError("Run an employer-board search before browsing pages")
    snapshot = result.snapshot_listings
    if snapshot is None:
        return None
    if (result.provider != "greenhouse" or not isinstance(snapshot, list)
            or type(result.total_matches) is not int or not 0 <= result.total_matches <= MAX_BOARDS * MAX_POSTS
            or len(snapshot) != min(result.total_matches, MAX_SNAPSHOT_MATCHES)):
        raise ValueError("Opportunity snapshot exceeds its limits or has inconsistent counts")
    required = {"id", "title", "employer", "location", "url", "posted_at", "description_snippet"}
    if any(not isinstance(job, dict) or not required <= job.keys()
            or not isinstance(job["id"], str) for job in snapshot):
        raise ValueError("Opportunity snapshot records are incomplete")
    if len({job["id"] for job in snapshot}) != len(snapshot):
        raise ValueError("Opportunity snapshot contains duplicate posting identities")
    pages = max(1, (len(snapshot) + OPPORTUNITY_PAGE_SIZE - 1) // OPPORTUNITY_PAGE_SIZE)
    if type(result.page) is not int or not 0 <= result.page < pages:
        raise ValueError("Opportunity page is outside its saved snapshot")
    offset = result.page * OPPORTUNITY_PAGE_SIZE
    expected = snapshot[offset:offset + OPPORTUNITY_PAGE_SIZE]
    if result.listings != expected:
        raise ValueError("Displayed opportunities do not match the saved page")
    return OpportunityPage(result.page + 1, pages, offset + 1 if expected else 0,
        offset + len(expected), len(snapshot), result.total_matches, len(snapshot) < result.total_matches)


def request_opportunity_page(state, page):
    """Select an absolute zero-based page without changing the cache or dates."""
    state.pop("job_detail", None)
    state.pop("job_detail_error", None)
    state.pop("job_page_error", None)
    state.pop("pending_posting_detail", None)
    result = state.get("job_result")
    info = page_info(result)
    if info is None or type(page) is not int or not 0 <= page < info.pages:
        raise ValueError("Choose an available page from the current employer search")
    boards = load_employer_boards()
    if result.source_scope_hash not in {None, board_scope_hash(boards)}:
        raise ValueError("Employer-board settings changed; run a new search")
    offset = page * OPPORTUNITY_PAGE_SIZE
    listings = result.snapshot_listings[offset:offset + OPPORTUNITY_PAGE_SIZE]
    for job in listings:
        posting_binding(job, boards)
    selected = replace(result, listings=listings, page=page)
    state["job_result"] = selected
    return selected
