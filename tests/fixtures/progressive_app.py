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
from progressive_provider import ControlledProvider

def forbidden(*args,**kwargs):
    raise AssertionError("The controlled browser process must not make external HTTP requests")

assert os.environ.get("ECE_BROWSER_CONTROL_DIR")
dotenv.load_dotenv = lambda *a,**k: False
httpx.Client.send = forbidden
src.controller.GeminiProvider = ControlledProvider
runpy.run_path(str(ROOT / "app.py"),run_name="__main__")
