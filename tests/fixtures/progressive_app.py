"""Optional browser control process; runs the production UI with a test provider.

This file is never imported by the student app or production launcher. No live
HTTP requests, real credentials, relevance judgments or model results are used.
"""

import os
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(Path(__file__).resolve().parent))

import dotenv
import httpx
import src.controller
import src.opportunities
import src.opportunity_details
from progressive_provider import ControlledProvider
from browsing_provider import search,fetch_detail

def forbidden(*args,**kwargs):
    raise AssertionError("The controlled browser process must not make external HTTP requests")

assert os.environ.get("ECE_BROWSER_CONTROL_DIR")
dotenv.load_dotenv = lambda *a,**k: False
httpx.Client.send = forbidden
src.controller.GeminiProvider = ControlledProvider
src.opportunities.search_employer_jobs = search
src.opportunity_details.fetch_posting_detail = fetch_detail
runpy.run_path(str(ROOT / "app.py"),run_name="__main__")
