"""Bounded embedding snapshots for offline scoring of external judgments.

Fingerprints bind vectors to exact inputs, not authenticated provider provenance.
Only explicit snapshot creation can call a supplied embedding adapter.
"""

from datetime import datetime, timezone
import hashlib
import re
from typing import Annotated, Literal

import numpy as np
from pydantic import AwareDatetime, Field, model_validator

from .catalog import build_evidence
from .models import StrictModel
from .providers import EmbeddingCache
from .query import QUERY_POLICY_VERSION
from .review import Fingerprint, Identity, fingerprint, review_queries, validate_packet

Finite = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Vector = Annotated[list[Finite], Field(min_length=1, max_length=3072)]


class EmbeddedQuestion(StrictModel):
    case_id: Identity
    effective_query: str = Field(min_length=1, max_length=8000)
    vector: Vector


def _matrix(values, dimensions):
    matrix = np.asarray(values, dtype=float)
    if matrix.ndim != 2 or matrix.shape[1] != dimensions or not np.isfinite(matrix).all():
        raise ValueError("Embedding dimensions or values are invalid")
    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        norms = np.linalg.norm(matrix, axis=1)
    if not np.isfinite(norms).all() or np.any(norms <= 0):
        raise ValueError("Embedding vectors must have finite nonzero norms")
    return matrix


class ReviewVectors(StrictModel):
    schema_version: Literal[1] = 1
    created_at: AwareDatetime
    packet_hash: Fingerprint
    corpus_hash: Fingerprint
    catalog_snapshot_hash: Fingerprint
    query_mode: Literal["raw", "expanded"]
    query_policy: str = Field(min_length=1, max_length=100)
    embedding_model: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,149}$")
    embedding_format: Literal["gemini-retrieval-prefix-v1"] = "gemini-retrieval-prefix-v1"
    vector_provenance: Literal["operator_supplied_unverified"] = "operator_supplied_unverified"
    dimensions: int = Field(strict=True, ge=1, le=3072)
    chunk_ids: list[str] = Field(min_length=1, max_length=100)
    chunk_text_hashes: list[Fingerprint] = Field(min_length=1, max_length=100)
    document_vectors: list[Vector] = Field(min_length=1, max_length=100)
    questions: list[EmbeddedQuestion] = Field(min_length=1, max_length=50)
    document_embedding_calls: int = Field(strict=True, ge=0, le=100)
    query_embedding_calls: int = Field(strict=True, ge=0, le=50)
    cache_state: str = Field(min_length=1, max_length=80)
    snapshot_hash: Fingerprint

    @model_validator(mode="after")
    def aligned_vectors(self):
        if len(self.chunk_ids) != len(self.document_vectors) or len(self.chunk_ids) != len(self.chunk_text_hashes):
            raise ValueError("Embedding rows and evidence identities do not align")
        if len(set(self.chunk_ids)) != len(self.chunk_ids) or len({q.case_id for q in self.questions}) != len(self.questions):
            raise ValueError("Embedding identities must be unique")
        _matrix(self.document_vectors, self.dimensions)
        _matrix([q.vector for q in self.questions], self.dimensions)
        return self


def vector_hash(snapshot):
    data = snapshot.model_dump(mode="json") if isinstance(snapshot, ReviewVectors) else dict(snapshot)
    data.pop("snapshot_hash", None)
    return fingerprint(data)


def validate_vectors(snapshot, catalog, packet, query_mode):
    packet = validate_packet(packet, catalog)
    snapshot = ReviewVectors.model_validate(snapshot.model_dump(warnings=False))
    if snapshot.snapshot_hash != vector_hash(snapshot):
        raise ValueError("The embedding snapshot fingerprint changed")
    if (snapshot.packet_hash != packet.packet_hash or snapshot.corpus_hash != packet.corpus_hash
            or snapshot.catalog_snapshot_hash != packet.catalog_snapshot_hash):
        raise ValueError("Embeddings do not match the reviewed packet and catalog snapshot")
    if (snapshot.query_mode != query_mode or snapshot.query_policy != QUERY_POLICY_VERSION
            or snapshot.embedding_format != EmbeddingCache.FORMAT or snapshot.created_at < packet.created_at):
        raise ValueError("Embedding query treatment, format, policy, or timestamp differs")
    evidence = build_evidence(catalog)
    if (snapshot.chunk_ids != [c.chunk_id for c in evidence]
            or snapshot.chunk_text_hashes != [hashlib.sha256(c.text.encode()).hexdigest() for c in evidence]):
        raise ValueError("Embedding evidence order or text differs")
    expected = [(q["case_id"], q["effective_query"]) for q in review_queries(catalog, packet, query_mode)]
    if [(q.case_id, q.effective_query) for q in snapshot.questions] != expected:
        raise ValueError("Embedding questions must match the exact effective queries and order")
    return snapshot


def make_vectors(catalog, packet, provider, cache, *, query_mode="raw", now=None):
    """Explicit creation only; accepts no grades and never calls generation."""
    packet = validate_packet(packet, catalog)
    queries = review_queries(catalog, packet, query_mode)
    if now is not None and (not isinstance(now, datetime) or now.tzinfo is None or now < packet.created_at):
        raise ValueError("Embedding creation needs an aware timestamp at or after packet creation")
    model, dimensions = provider.embedding_model, provider.dimensions
    if (not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,149}", model)
            or type(dimensions) is not int or not 1 <= dimensions <= 3072):
        raise ValueError("Embedding configuration is invalid")
    class Counted:
        def __init__(self):
            self.embedding_model, self.dimensions, self.calls = model, dimensions, 0
        def embed_document(self, chunk):
            self.calls += 1
            return provider.embed_document(chunk)
    counted = Counted()
    evidence = build_evidence(catalog)
    vectors, state, _ = cache.get(catalog, evidence, counted)
    vectors = _matrix(vectors, dimensions)
    questions = []
    for query in queries:
        vector = _matrix([provider.embed_query(query["effective_query"])], dimensions)[0]
        questions.append(EmbeddedQuestion(case_id=query["case_id"], effective_query=query["effective_query"], vector=vector.tolist()))
    snapshot = ReviewVectors(created_at=now or datetime.now(timezone.utc), packet_hash=packet.packet_hash,
        corpus_hash=packet.corpus_hash, catalog_snapshot_hash=packet.catalog_snapshot_hash,
        query_mode=query_mode, query_policy=QUERY_POLICY_VERSION, embedding_model=model, dimensions=dimensions,
        chunk_ids=[c.chunk_id for c in evidence], chunk_text_hashes=[hashlib.sha256(c.text.encode()).hexdigest() for c in evidence],
        document_vectors=vectors.tolist(), questions=questions, document_embedding_calls=counted.calls,
        query_embedding_calls=len(questions), cache_state=state, snapshot_hash="0" * 64)
    snapshot.snapshot_hash = vector_hash(snapshot)
    return validate_vectors(snapshot, catalog, packet, query_mode)
