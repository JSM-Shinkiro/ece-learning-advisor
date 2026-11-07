"""Explicitly controlled employer results and a delayed posting for browser QA."""

from datetime import datetime,timezone
from hashlib import sha256
import os
from pathlib import Path
import time

from src.jobs import JobSearchResult
from src.opportunities import load_employer_boards,normalize_post
from src.opportunity_details import PostingContent,PostingDetailCheck,posting_binding

NOW=datetime(2026,11,7,18,tzinfo=timezone.utc)


def count_action(name):
    path=Path(os.environ["ECE_BROWSER_CONTROL_DIR"])/(name+".calls")
    with path.open("a") as handle:handle.write("called\n")
    return len(path.read_text().splitlines())


def search(career,location,internship,*,updated_within=None,early_career=False,boards=None):
    count_action("opportunity_search")
    board=(boards or load_employer_boards())[0]
    url=board.job_base_url+"12" if board.url_style=="id_path" else board.job_base_url+"?gh_jid=12"
    job=normalize_post({"id":12,"internal_job_id":1012,"title":"Controlled Embedded Intern",
        "company_name":board.employer,"location":{"name":"Remote - US"},"absolute_url":url,
        "first_published":"2026-09-01T12:00:00Z","updated_at":"2026-11-03T12:00:00Z"},board,NOW)
    return JobSearchResult([job],NOW.isoformat(),"embedded software",location or "All listed locations",
        provider="greenhouse",total_matches=1,checks=[{"board":board.token,"status":"controlled_fixture"}])


def fetch_detail(job,*,boards=None,now=None):
    number=count_action("posting_detail")
    control=Path(os.environ["ECE_BROWSER_CONTROL_DIR"])
    _,_,url=posting_binding(job,boards or load_employer_boards())
    if number==1:
        (control/"posting.started").touch();deadline=time.monotonic()+20
        while not (control/"posting.release").exists():
            if time.monotonic()>deadline:raise RuntimeError("Controlled posting release did not arrive")
            time.sleep(0.02)
        text="Controlled posting description: embedded programming practice."
        return PostingDetailCheck(posting_id=job["id"],source_url=url,requested_at=NOW,checked_at=NOW,
            status="verified",http_status=200,posting=PostingContent(**{k:job.get(k) for k in
                ("title","employer","location","url","posted_at","updated_at")},description=text,
                description_chars=len(text),description_sha256=sha256(text.encode()).hexdigest(),truncated=False))
    return PostingDetailCheck(posting_id=job["id"],source_url=url,requested_at=NOW,status="unavailable",failure_kind="network")
