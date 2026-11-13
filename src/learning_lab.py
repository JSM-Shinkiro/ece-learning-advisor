"""A local retrieval experiment using public descriptions and teachable topic vectors."""

from dataclasses import dataclass
from functools import lru_cache
import re

import numpy as np

from .catalog import build_evidence
from .models import Catalog
from .retrieval import Hit, Retriever, project_embeddings, reciprocal_rank_fusion, tokenize

TOPICS = {
    "Programming": ("programming", "code", "python", "c++", "software", "c programming",
                    "program in c", "code in c", "coding in c", "write c"),
    "Embedded hardware": ("microcontroller", "microcontrollers", "embedded", "hardware", "processor",
                          "interrupt", "sensor", "sensors", "robot", "robots", "robotics", "arduino"),
    "Machine learning": ("machine learning", "neural", "classification", "deep learning", "pytorch",
                         "computer vision", "image recognition", "classify images", "classify pictures",
                         "recognize pictures", "recognise pictures"),
    "Data structures": ("data structure", "data structures", "algorithm", "algorithms", "array",
                        "arrays", "list", "lists", "tree", "hash table"),
}

QUESTION_WORDS = frozenset(
    "about am are be build can could does do find get how is it know learning me need please "
    "practice should start study teach the use want was were which why will would you your".split()
)

PRESETS = {
    "Program a sensor": "How do I read sensors with a microcontroller using C?",
    "Learn image classification": "How do I train a neural network for image classification in Python?",
    "Choose a data structure": "When should I use an array, list or hash table in a program?",
}

RECORDS = ("ECE101", "ECE369A", "ECE372A", "ECE425", "CSC120", "resource:pytorch", "resource:cs50")
TOPIC_PATTERNS = {
    topic: tuple((term, re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)")) for term in terms)
    for topic, terms in TOPICS.items()
}


def matched_topic_terms(text):
    words = text.casefold()
    return {topic: tuple(term for term, pattern in terms if pattern.search(words))
            for topic, terms in TOPIC_PATTERNS.items()}


def topic_vector(text):
    """Count distinct listed terms in each topic dimension."""
    return np.array([len(matches) for matches in matched_topic_terms(text).values()], dtype=float)


def keyword_terms(text):
    return set(tokenize(text)) - QUESTION_WORDS


@dataclass(frozen=True)
class LabIndex:
    labels: tuple[str, ...]
    retriever: Retriever
    vectors: np.ndarray
    catalog: Catalog


@lru_cache(maxsize=4)
def build_lab_index(catalog_json):
    catalog = Catalog.model_validate_json(catalog_json)
    overviews = {chunk.record_id: chunk for chunk in build_evidence(catalog)
                 if chunk.chunk_id.endswith(":overview")}
    records = {record.code or record.record_id: record for record in catalog.records}
    chosen = [records[key] for key in RECORDS if key in records]
    labels = tuple(record.code or record.title for record in chosen)
    evidence = [overviews[record.record_id] for record in chosen]
    vectors = np.array([topic_vector(doc.text) for doc in evidence])
    return LabIndex(labels, Retriever(evidence, vectors), vectors, catalog)


@dataclass(frozen=True)
class Experiment:
    query: str
    method: str
    hits: tuple[Hit, ...]
    vector: np.ndarray
    points: np.ndarray
    query_point: np.ndarray | None


def run_experiment(index, query, method):
    if method not in {"keyword", "semantic", "hybrid"}:
        raise ValueError("Unknown retrieval method")
    vector = topic_vector(query)
    has_topics = bool(np.any(vector))
    if not has_topics:
        method = "keyword"
    limit = len(index.labels)
    keywords = index.retriever.keyword(" ".join(sorted(keyword_terms(query))), limit) if method != "semantic" else []
    topics = [hit for hit in index.retriever.semantic(vector, limit) if hit.score > 0] if method != "keyword" else []
    hits = keywords if method == "keyword" else topics
    if method == "hybrid":
        hits = reciprocal_rank_fusion(keywords, topics)
    if not hits:
        if method == "keyword" and has_topics:
            raise ValueError("Keyword found no shared search words. Try Topic cosine to compare the recognized topics.")
        raise ValueError("The seven lesson records have no match for this question. "
                         "Try ECE425, a sensor question, computer vision or C programming.")
    points, query_point = project_embeddings(index.vectors, vector if has_topics else None)
    return Experiment(query, method, tuple(hits), vector, points, query_point)


def compare_embedding_ranks(index, chunks, vectors, query, query_vector):
    """Rank the lesson overviews from an existing advisor request in both representations."""
    positions = {chunk.chunk_id: i for i, chunk in enumerate(chunks)}
    documents = index.retriever.evidence
    neural_vectors = vectors[[positions[doc.chunk_id] for doc in documents]]
    neural = Retriever(documents, neural_vectors).semantic(query_vector, len(documents))
    counts = topic_vector(query)
    topic_hits = index.retriever.semantic(counts, len(documents)) if np.any(counts) else []
    topic_ranks = {hit.chunk_id: (rank, hit.score) for rank, hit in enumerate(
        (hit for hit in topic_hits if hit.score > 0), 1)}
    rows = []
    for rank, hit in enumerate(neural, 1):
        topic_rank, cosine = topic_ranks.get(hit.chunk_id, (None, None))
        rows.append({"Record ID": hit.record_id, "Topic rank": topic_rank, "Topic cosine": cosine,
                     "Neural rank": rank, "Neural cosine": hit.score})
    return rows


def compare_ranks(original, variation):
    before = {hit.record_id: rank for rank, hit in enumerate(original.hits, 1)}
    after = {hit.record_id: rank for rank, hit in enumerate(variation.hits, 1)}
    return [{"Record": label, "Preset rank": before.get(label), "Your rank": after.get(label)}
            for label in dict.fromkeys([*after, *before])]


def evidence_fit(experiment, expected_record_ids):
    """Count the learner's expected records in the first three results."""
    top_three = {hit.record_id for hit in experiment.hits[:3]}
    return len(top_three.intersection(expected_record_ids))


def plot_experiment(index, experiment):
    """Plot the same normalized vectors used by the topic retriever."""
    import plotly.graph_objects as go

    ranking = {hit.record_id: rank for rank, hit in enumerate(experiment.hits, 1)}
    records = index.retriever.evidence
    text = [f"Rank {ranking[doc.record_id]}" if doc.record_id in ranking else "Outside the ranking" for doc in records]
    colors = ["#62d6c7" if ranking.get(doc.record_id, 999) <= 3 else "#7995b1" for doc in records]
    chart = go.Figure(go.Scatter(
        x=experiment.points[:, 0], y=experiment.points[:, 1], mode="markers",
        text=index.labels, customdata=text, name="Saved evidence",
        marker={"size": 13, "color": colors, "line": {"color": "#0b1220", "width": 1}},
        hovertemplate="%{text}<br>%{customdata}<extra></extra>",
    ))
    if experiment.query_point is not None:
        chart.add_trace(go.Scatter(
            x=[experiment.query_point[0]], y=[experiment.query_point[1]],
            mode="markers", name="Question", marker={"size": 18, "symbol": "star", "color": "#ffd17a"},
            hovertemplate="Your question<extra></extra>",
        ))
    chart.update_layout(template="plotly_dark", height=295, margin={"l": 25, "r": 18, "t": 12, "b": 30},
                        xaxis_title="PCA 1", yaxis_title="PCA 2", paper_bgcolor="#131e31",
                        plot_bgcolor="#131e31", legend={"orientation": "h", "y": -0.21})
    return chart
