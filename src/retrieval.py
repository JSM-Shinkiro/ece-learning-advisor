"""BM25, cosine retrieval, and rank fusion over stable evidence IDs."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

import numpy as np

from .models import Evidence

STOP_WORDS = {"the", "a", "an", "and", "or", "for", "to", "of", "in", "my", "i", "with", "what", "should", "learn", "next", "course", "courses"}


def tokenize(text: str) -> list[str]:
    text = re.sub(r"\b([A-Za-z]{2,8})\s+(\d{3}[A-Za-z]{0,2})\b", r"\1\2", text)
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP_WORDS]


@dataclass(frozen=True)
class Hit:
    chunk_id: str
    record_id: str
    score: float
    method: str
    keyword_score: float | None = None
    cosine_score: float | None = None


def normalized(vectors) -> np.ndarray:
    values = np.asarray(vectors, dtype=float)
    if values.ndim != 2 or values.shape[0] == 0 or values.shape[1] == 0:
        raise ValueError("Expected a nonempty vector matrix")
    if not np.isfinite(values).all():
        raise ValueError("Vectors must be finite")
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    if np.any(norms <= 0):
        raise ValueError("Zero vectors cannot be ranked by cosine similarity")
    return values / norms


class Retriever:
    def __init__(self, evidence: list[Evidence], vectors=None):
        self.evidence = evidence
        self.docs = [Counter(tokenize(e.text)) for e in evidence]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.average = sum(self.lengths) / max(len(self.lengths), 1)
        self.df = Counter(t for doc in self.docs for t in doc)
        self.vectors = normalized(vectors) if vectors is not None else None
        if self.vectors is not None and len(self.vectors) != len(evidence):
            raise ValueError("Vector rows and evidence IDs do not align")

    def keyword(self, query: str, limit=20) -> list[Hit]:
        terms = set(tokenize(query))
        scored = []
        n = len(self.docs)
        for i, doc in enumerate(self.docs):
            score = 0.0
            for term in terms:
                tf = doc[term]
                if not tf:
                    continue
                idf = math.log(1 + (n - self.df[term] + .5) / (self.df[term] + .5))
                score += idf * (tf * 2.5) / (tf + 1.5 * (.25 + .75 * self.lengths[i] / (self.average or 1)))
            if score > 0:
                e = self.evidence[i]
                scored.append(Hit(e.chunk_id, e.record_id, score, "keyword", keyword_score=score))
        return sorted(scored, key=lambda h: (-h.score, h.chunk_id))[:limit]

    def semantic(self, vector, limit=20) -> list[Hit]:
        if self.vectors is None:
            raise ValueError("A semantic index is not loaded")
        query = normalized([vector])[0]
        if len(query) != self.vectors.shape[1]:
            raise ValueError("Query and index dimensions differ")
        scores = self.vectors @ query
        hits = [Hit(e.chunk_id, e.record_id, float(scores[i]), "semantic", cosine_score=float(scores[i])) for i, e in enumerate(self.evidence)]
        return sorted(hits, key=lambda h: (-h.score, h.chunk_id))[:limit]

    def search(self, query: str, method="keyword", query_vector=None, limit=20) -> list[Hit]:
        if method == "keyword":
            return self.keyword(query, limit)
        semantic = self.semantic(query_vector, limit)
        if method == "semantic":
            return semantic
        if method != "hybrid":
            raise ValueError("Unknown retrieval method")
        keyword = self.keyword(query, limit)
        return reciprocal_rank_fusion(keyword, semantic)[:limit]


def reciprocal_rank_fusion(*lists: list[Hit], constant=60) -> list[Hit]:
    if constant < 1:
        raise ValueError("Rank constant must be positive")
    scores, examples, keywords, cosines = {}, {}, {}, {}
    for hits in lists:
        for rank, hit in enumerate(hits, start=1):
            scores[hit.chunk_id] = scores.get(hit.chunk_id, 0) + 1 / (constant + rank)
            examples[hit.chunk_id] = hit
            if hit.keyword_score is not None:
                keywords[hit.chunk_id] = hit.keyword_score
            if hit.cosine_score is not None:
                cosines[hit.chunk_id] = hit.cosine_score
    fused = [Hit(k, examples[k].record_id, v, "hybrid", keywords.get(k), cosines.get(k)) for k, v in scores.items()]
    return sorted(fused, key=lambda h: (-h.score, h.chunk_id))


def project_embeddings(vectors, query_vector=None):
    """Fit one PCA projection on record vectors and transform the query with it."""
    values = normalized(vectors)
    center = values.mean(axis=0)
    centered = values - center
    _, _, axes = np.linalg.svd(centered, full_matrices=False)
    axes = axes[:2]
    if len(axes) < 2:
        axes = np.vstack([axes, np.zeros_like(axes[0])])
    points = centered @ axes.T
    query = None
    if query_vector is not None:
        query = (normalized([query_vector])[0] - center) @ axes.T
    return points, query
