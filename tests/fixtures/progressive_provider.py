"""Deterministic, event-controlled provider used only by optional browser checks."""

import os
from pathlib import Path
import time

import numpy as np

from src.models import ExplanationSelection, SelectedRecommendation

CASES = {"Controlled draft request":"draft", "Controlled old request":"old", "Controlled stop request":"stop"}


class ControlledProvider:
    def __init__(self,api_key,*,embedding_model,generation_model,dimensions):
        self.embedding_model = "controlled-browser-vectors"
        self.generation_model = "controlled-browser-statements"
        self.dimensions = dimensions
        self.case = None
        self.control = Path(os.environ["ECE_BROWSER_CONTROL_DIR"])

    def embed_document(self,chunk):
        return np.arange(1,self.dimensions+1,dtype=float)

    def embed_query(self,query):
        return np.arange(1,self.dimensions+1,dtype=float)

    def generate(self,context):
        self.case = CASES.get(context.profile.question)
        if self.case:
            (self.control / (self.case+".started")).touch()
            deadline = time.monotonic()+35
            while not (self.control / (self.case+".release")).exists():
                if time.monotonic()>deadline:
                    raise RuntimeError("The controlled browser release did not arrive")
                time.sleep(0.02)
        record=context.allowed_record_ids[0]
        statement=next(s for s in context.allowed_statements if s.record_id==record and s.claim_type=="recommendation")
        return ExplanationSelection(status="answered",recommendations=[
            SelectedRecommendation(record_id=record,statement_ids=[statement.statement_id])])

    def close(self):
        if self.case:
            (self.control / (self.case+".closed")).touch()
