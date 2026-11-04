from types import SimpleNamespace

import numpy as np
import pytest

from src.catalog import load_catalog
from src.models import GeneratedAnswer, Reason, Recommendation


@pytest.fixture
def catalog():
    return load_catalog()


class FakeProvider:
    """Controlled provider for integration tests, never used by the running app."""
    embedding_model = "fixture-vectors"
    generation_model = "fixture-generator"
    dimensions = 3

    def __init__(self):
        self.context = None
        self.document_calls = 0

    def embed_document(self, chunk):
        self.document_calls += 1
        text = chunk.text.lower()
        return np.array([1 + text.count("learning"), 1 + text.count("microcontroller"), 1])

    def embed_query(self, query):
        return np.array([2, 1, 1]) if "machine learning" in query.lower() else np.array([1, 2, 1])

    def generate(self, context):
        self.context = context
        rid = context.allowed_record_ids[0]
        evidence = next(e for e in context.evidence if e.record_id == rid)
        return GeneratedAnswer(status="answered", recommendations=[
            Recommendation(record_id=rid, reasons=[
                Reason(text="Consider this topic as a learning connection.",claim_type="recommendation",
                       evidence_ids=[evidence.chunk_id])
            ])
        ])


@pytest.fixture
def fake_provider():
    return FakeProvider()
