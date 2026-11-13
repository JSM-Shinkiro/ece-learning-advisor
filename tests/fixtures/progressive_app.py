"""Optional browser control process; runs the production UI with a test provider.

This file is never imported by the student app or production launcher. No live
HTTP requests, real credentials, relevance judgments or model results are used.
"""

import os
from pathlib import Path
import runpy
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(Path(__file__).resolve().parent))

import dotenv
import httpx
import src.controller
import src.opportunities
import src.opportunity_details
from src.models import SourceCheck
from src.sources import CatalogRefresh
from progressive_provider import ControlledProvider
from browsing_provider import search,fetch_detail

def forbidden(*args,**kwargs):
    raise AssertionError("The controlled browser process must not make external HTTP requests")


def refresh_sources(catalog, profile, **options):
    if profile.question in {"ECE101 controlled source update", "ECE101 controlled keep saved plan"}:
        case = "source-update" if profile.question.endswith("source update") else "source-keep"
        (control / (case + ".started")).touch()
        try:
            deadline = time.monotonic() + 35
            while not (control / (case + ".release")).exists():
                if time.monotonic() > deadline:
                    raise RuntimeError("The controlled source release did not arrive")
                time.sleep(0.02)
        finally:
            (control / (case + ".closed")).touch()
    source = next(source for source in catalog.sources if source.source_id == "catalog:ECE101")
    checked = datetime.now(timezone.utc)
    source.verification_status = "verified"
    source.last_checked_at = checked
    check = SourceCheck(source_id=source.source_id, code="ECE101", url=source.url,
                        status="unchanged", attempted_at=checked, last_checked_at=checked)
    return CatalogRefresh(catalog, checks=[check], reuse_seconds=options["reuse_seconds"])


control = Path(os.environ["ECE_BROWSER_CONTROL_DIR"])
os.environ["ECE_REFRESH_SOURCES"] = "true"
dotenv.load_dotenv = lambda *a,**k: False
httpx.Client.send = forbidden
src.controller.GeminiProvider = ControlledProvider
src.controller.refresh_catalog = refresh_sources
src.opportunities.search_employer_jobs = search
src.opportunity_details.fetch_posting_detail = fetch_detail
runpy.run_path(str(ROOT / "app.py"),run_name="__main__")
