"""A local retrieval experiment using public descriptions and teachable topic vectors."""

from dataclasses import dataclass
from functools import lru_cache
import re

import numpy as np

from .catalog import build_evidence
from .models import Catalog
from .retrieval import Hit, Retriever, project_embeddings

TOPICS = {
    "Programming": ("programming", "code", "python", "c++", "software"),
    "Embedded hardware": ("microcontroller", "microcontrollers", "embedded", "hardware", "processor", "interrupt", "sensor", "sensors"),
    "Machine learning": ("machine learning", "neural", "classification", "deep learning", "pytorch"),
    "Data structures": ("data structure", "data structures", "algorithm", "algorithms", "array", "arrays",
                        "list", "lists", "tree", "hash table"),
}

PRESETS = {
    "Program a sensor": "How do I read sensors with a microcontroller using C?",
    "Learn image classification": "How do I train a neural network for image classification in Python?",
    "Choose a data structure": "When should I use an array, list or hash table in a program?",
}

RECORDS = ("ECE101", "ECE369A", "ECE372A", "ECE425", "CSC120", "resource:pytorch", "resource:cs50")
TOPIC_PATTERNS = tuple(tuple(re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)") for term in terms)
                       for terms in TOPICS.values())


def topic_vector(text):
    """Count distinct listed terms in each topic dimension."""
    words = text.lower()
    return np.array([sum(bool(pattern.search(words)) for pattern in patterns)
                     for patterns in TOPIC_PATTERNS], dtype=float)


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
    vector = topic_vector(query)
    if method != "keyword" and not np.any(vector):
        raise ValueError("Include a topic word such as Python, sensor, neural network or array, or try Keyword.")
    hits = index.retriever.search(query, method, vector, limit=len(index.labels))
    points, query_point = project_embeddings(index.vectors, vector if np.any(vector) else None)
    return Experiment(query, method, tuple(hits), vector, points, query_point)


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
