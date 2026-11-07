"""Unscored review packets and separately supplied retrieval judgments.

Packets contain no rankings or prior labels. Reviewer identity/role and custom
question provenance are self-reported; a completed form is not proof of a
held-out experiment. This local workflow makes no network or provider calls.
"""

from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, model_validator

from .catalog import ROOT, build_evidence, corpus_hash, load_catalog
from .evaluation import catalog_snapshot_hash, load_suite, rank_metrics, suite_hash
from .models import Catalog, Evidence, Source, StrictModel
from .query import QUERY_POLICY_VERSION, interpret_query
from .retrieval import Retriever

MAX_REVIEW_BYTES = 2_000_000
MAX_VECTOR_BYTES = 24_000_000
Identity = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")]
Fingerprint = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Grade = Annotated[int, Field(strict=True, ge=0, le=3)]


def fingerprint(value):
    data = value.model_dump(mode="json") if isinstance(value, StrictModel) else value
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode()).hexdigest()


class ReviewQuestion(StrictModel):
    case_id: Identity
    query: str = Field(min_length=1, max_length=1200)

    @model_validator(mode="after")
    def meaningful_query(self):
        if not self.query.strip():
            raise ValueError("Review questions cannot be blank")
        return self


class PacketQuestion(ReviewQuestion):
    candidate_ids: list[str] = Field(min_length=1, max_length=100)


class ReviewPacket(StrictModel):
    schema_version: Literal[1] = 1
    packet_id: Identity
    created_at: AwareDatetime
    question_origin: Literal["existing_development_questions", "custom_questions_unverified"]
    source_suite_hash: Fingerprint | None = None
    corpus_hash: Fingerprint
    catalog_snapshot_hash: Fingerprint
    evidence: list[Evidence] = Field(min_length=1, max_length=100)
    sources: list[Source] = Field(min_length=1, max_length=200)
    questions: list[PacketQuestion] = Field(min_length=1, max_length=50)
    shuffle_seed: int = Field(strict=True, ge=0, le=2**32 - 1)
    packet_hash: Fingerprint


class CaseJudgments(StrictModel):
    case_id: Identity
    relevance: dict[str, Grade | None] = Field(min_length=1, max_length=100)
    note: str = Field(default="", max_length=2000)


class ReviewForm(StrictModel):
    schema_version: Literal[1] = 1
    packet_hash: Fingerprint
    reviewer_id: Identity | None = None
    reviewer_role: Literal["independent_reviewer", "project_contributor", "controlled_fixture"] | None = None
    reviewed_at: AwareDatetime | None = None
    cases: list[CaseJudgments] = Field(min_length=1, max_length=50)


def _question_identities(questions):
    ids = [q.case_id for q in questions]
    text = [" ".join(q.query.casefold().split()) for q in questions]
    if len(ids) != len(set(ids)) or len(text) != len(set(text)):
        raise ValueError("Review question IDs and normalized text must be unique")


def packet_hash(packet):
    data = packet.model_dump(mode="json") if isinstance(packet, ReviewPacket) else dict(packet)
    data.pop("packet_hash", None)
    return fingerprint(data)


def _development_questions():
    # The frozen suite identifies only the reused question bank here. Its
    # relevance grades do not transfer to a larger evidence collection.
    suite = load_suite(load_catalog())
    return [ReviewQuestion(case_id=c.case_id, query=c.query) for c in suite.retrieval_cases], suite_hash(suite)


def make_packet(catalog, *, packet_id="p07-review-v1", questions=None, seed=7, now=None):
    source_hash = None
    if questions is None:
        questions, source_hash = _development_questions()
    else:
        questions = [ReviewQuestion.model_validate(q) for q in questions]
    _question_identities(questions)
    evidence = build_evidence(catalog)
    rng, cases = random.Random(seed), []
    for question in questions:
        ids = [e.chunk_id for e in evidence]
        rng.shuffle(ids)
        cases.append({**question.model_dump(), "candidate_ids": ids})
    data = dict(schema_version=1, packet_id=packet_id, created_at=now or datetime.now(timezone.utc),
        question_origin="existing_development_questions" if source_hash else "custom_questions_unverified",
        source_suite_hash=source_hash, corpus_hash=corpus_hash(catalog),
        catalog_snapshot_hash=catalog_snapshot_hash(catalog), evidence=evidence,
        sources=catalog.sources, questions=cases, shuffle_seed=seed, packet_hash="0" * 64)
    packet = ReviewPacket.model_validate(data)
    packet.packet_hash = packet_hash(packet)
    return validate_packet(packet, catalog)


def validate_packet(packet, catalog):
    # Revalidate even in-memory copies; model_copy(update=...) does not validate.
    packet = ReviewPacket.model_validate(packet.model_dump(warnings=False))
    if packet.packet_hash != packet_hash(packet):
        raise ValueError("The review packet fingerprint changed")
    if packet.corpus_hash != corpus_hash(catalog) or packet.catalog_snapshot_hash != catalog_snapshot_hash(catalog):
        raise ValueError("The review packet does not match this catalog snapshot")
    expected = [e.model_dump(mode="json") for e in build_evidence(catalog)]
    if [e.model_dump(mode="json") for e in packet.evidence] != expected or packet.sources != catalog.sources:
        raise ValueError("Review evidence and source metadata must match the bound snapshot")
    _question_identities(packet.questions)
    ids = {e.chunk_id for e in packet.evidence}
    for question in packet.questions:
        if len(question.candidate_ids) != len(ids) or set(question.candidate_ids) != ids:
            raise ValueError("Every review question needs every evidence chunk exactly once")
    if packet.question_origin == "existing_development_questions":
        originals, source_hash = _development_questions()
        expected_questions = [(q.case_id, q.query) for q in originals]
        if packet.source_suite_hash != source_hash or [(q.case_id, q.query) for q in packet.questions] != expected_questions:
            raise ValueError("Existing development questions must match their frozen suite")
    elif packet.source_suite_hash is not None:
        raise ValueError("Custom questions cannot claim a frozen-suite origin")
    return packet


def blank_form(packet):
    return ReviewForm(packet_hash=packet.packet_hash, cases=[CaseJudgments(case_id=q.case_id,
        relevance={key: None for key in q.candidate_ids}) for q in packet.questions])


def validate_review(form, packet):
    # Preserve native types: JSON-mode serialization can turn bool into int
    # before a strict grade validator sees an in-memory mutation.
    form = ReviewForm.model_validate(form.model_dump(warnings=False))
    if form.packet_hash != packet.packet_hash:
        raise ValueError("Review judgments belong to a different packet")
    if not form.reviewer_id or not form.reviewer_role or not form.reviewed_at:
        raise ValueError("Completed reviews need a reviewer alias, role, and aware review timestamp")
    if form.reviewed_at < packet.created_at:
        raise ValueError("Review completion cannot precede packet creation")
    expected = {q.case_id for q in packet.questions}
    actual = [c.case_id for c in form.cases]
    if len(actual) != len(expected) or set(actual) != expected:
        raise ValueError("Review judgments must cover each packet question exactly once")
    ids = {e.chunk_id for e in packet.evidence}
    for case in form.cases:
        if set(case.relevance) != ids or any(g is None for g in case.relevance.values()):
            raise ValueError("Every evidence chunk needs an explicit relevance grade for every question")
    return form


def parse_review_json(raw, *, max_bytes=MAX_REVIEW_BYTES):
    """Parse bounded review bytes, rejecting duplicate keys at every level."""
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Review JSON contains duplicate keys")
            result[key] = value
        return result

    if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_VECTOR_BYTES:
        raise ValueError("Invalid review input size limit")
    if not isinstance(raw, bytes):
        raise ValueError("Review input must be bytes")
    if len(raw) > max_bytes:
        raise ValueError("Review file exceeds the size limit")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_keys)


def load_review_json(path, *, max_bytes=MAX_REVIEW_BYTES):
    """Read bounded review JSON; never silently discard duplicate judgments."""
    if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_VECTOR_BYTES:
        raise ValueError("Invalid review input size limit")
    with Path(path).open("rb") as handle:
        raw = handle.read(max_bytes + 1)
    return parse_review_json(raw, max_bytes=max_bytes)


def load_catalog_snapshot(path):
    """Load a bounded, duplicate-key-checked saved catalog, without source calls."""
    catalog = Catalog.model_validate(load_review_json(path))
    if any(record.review_status == "synthetic_fixture" for record in catalog.records):
        raise ValueError("Synthetic fixture catalogs cannot supply review evidence")
    return catalog


def review_queries(catalog, packet, query_mode):
    if not isinstance(query_mode, str) or query_mode not in {"raw", "expanded"}:
        raise ValueError("Choose raw or expanded query evaluation")
    rows = []
    for question in packet.questions:
        interpretation = interpret_query(question.query, catalog) if query_mode == "expanded" else None
        rows.append({"case_id": question.case_id, "query": question.query,
            "effective_query": interpretation.expand(question.query) if interpretation else question.query,
            "query_interpretation": interpretation.trace() if interpretation else None})
    return rows


def score_review(catalog, packet, form, *, k=5, query_mode="raw", method="keyword", embeddings=None):
    packet = validate_packet(packet, catalog)
    form = validate_review(form, packet)
    queries = review_queries(catalog, packet, query_mode)
    rank_metrics([], form.cases[0].relevance, k=k)
    if not isinstance(method, str) or method not in {"keyword", "semantic", "hybrid"} or (method == "keyword") != (embeddings is None):
        raise ValueError("Semantic/hybrid scoring requires a bound embedding snapshot; keyword uses none")
    vectors, query_vectors, embedding_info = None, {}, None
    if embeddings is not None:
        from .review_vectors import validate_vectors
        snapshot = validate_vectors(embeddings, catalog, packet, query_mode)
        vectors = snapshot.document_vectors
        query_vectors = {q.case_id: q.vector for q in snapshot.questions}
        embedding_info = snapshot.model_dump(mode="json", exclude={"document_vectors", "questions", "chunk_ids", "chunk_text_hashes"})
    retriever = Retriever(build_evidence(catalog), vectors)
    judgments = {case.case_id: case for case in form.cases}
    rows = []
    for query in queries:
        case = judgments[query["case_id"]]
        hits = retriever.search(query["effective_query"], method=method,
            query_vector=query_vectors.get(case.case_id), limit=100)
        relevant = [key for key, grade in case.relevance.items() if grade >= 2]
        rows.append({**query,
            "ranked_chunk_ids": [h.chunk_id for h in hits], "scores": [h.score for h in hits],
            "component_scores": [{"keyword": h.keyword_score, "cosine": h.cosine_score} for h in hits],
            "judgments": case.relevance, "review_note": case.note, "relevant_chunk_ids": relevant,
            "precision_ceiling": min(k, len(relevant)) / k,
            "metrics": rank_metrics([h.chunk_id for h in hits], case.relevance, k=k)})
    summary, defined = {}, {}
    for metric in ("precision", "recall", "reciprocal_rank", "ndcg"):
        values = [row["metrics"][metric] for row in rows if row["metrics"][metric] is not None]
        summary[metric] = mean(values) if values else None
        defined[metric] = len(values)
    implementation = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
        "src/review.py", "scripts/review_retrieval.py", "src/catalog.py", "src/evaluation.py",
        "src/query.py", "src/retrieval.py", "src/models.py", "src/review_vectors.py", "src/providers.py")}
    return {"schema_version": 2, "created_at": datetime.now(timezone.utc).isoformat(),
        "packet_id": packet.packet_id, "packet_hash": packet.packet_hash, "review_hash": fingerprint(form),
        "corpus_hash": packet.corpus_hash, "catalog_snapshot_hash": packet.catalog_snapshot_hash,
        "catalog": {"data_version": catalog.version, "catalog_year": catalog.catalog_version,
                    "records": len(catalog.records), "evidence_chunks": len(packet.evidence),
                    "courses": sum(r.kind == "course" for r in catalog.records),
                    "resources": sum(r.kind == "resource" for r in catalog.records)},
        "source_suite_hash": packet.source_suite_hash, "question_origin": packet.question_origin,
        "reviewer": {"alias": form.reviewer_id, "self_reported_role": form.reviewer_role,
                     "reviewed_at": form.reviewed_at.isoformat()},
        "limitations": "Reviewer identity, independence, and question provenance are not authenticated. "
            "Reused development questions are not held out; custom questions have unverified provenance. "
            "Controlled fixture labels verify tooling only. Vector provenance and model identity are not authenticated. "
            "This measures retrieval on the supplied "
            "snapshot, not answer accuracy, enrollment eligibility, source freshness, or live discovery.",
        "method": method, "cutoff": k, "query_mode": query_mode, "runtime_query_policy": QUERY_POLICY_VERSION,
        "embedding_snapshot": embedding_info,
        "metric_conventions": {"unit": "evidence chunk", "binary_relevance_minimum": 2,
            "precision_denominator": "fixed cutoff", "ndcg_gain": "linear grade / log2(rank + 1)",
            "aggregation": "equal query weights; undefined values excluded with counts"},
        "summary": {"cases": len(rows), **summary, "defined_cases": defined,
            "queries_without_relevant_evidence": sum(not row["relevant_chunk_ids"] for row in rows),
            "precision_ceiling": mean(row["precision_ceiling"] for row in rows)},
        "cases": rows, "implementation": implementation,
        "embedding_calls": 0, "generation_calls": 0, "source_refresh_calls": 0}


def packet_markdown(packet):
    """A reading guide, separate from both grading and score reports."""
    sources = {s.source_id: s for s in packet.sources}
    lines = ["# Retrieval relevance review", "", f"Packet: `{packet.packet_id}`",
        f"Packet fingerprint: `{packet.packet_hash}`",
        f"Corpus fingerprint: `{packet.corpus_hash}`",
        f"Catalog snapshot fingerprint: `{packet.catalog_snapshot_hash}`",
        f"Saved evidence: {len(packet.evidence)} chunks from {len(packet.sources)} sources.",
        f"Review workload: {len(packet.questions)} questions × {len(packet.evidence)} chunks = {len(packet.questions) * len(packet.evidence)} grades.", "",
        "Read the saved evidence below, then fill review_template.json. Use an alias; no name or email is needed.",
        "Set reviewer_role to independent_reviewer, project_contributor, or controlled_fixture, and reviewed_at to an ISO timestamp with timezone.",
        "Grade every chunk for every question. null means unfinished, not irrelevant. Optional notes can explain uncertainty.",
        "", "| Grade | Meaning |", "| --- | --- |", "| 0 | Unrelated |", "| 1 | Broad background |",
        "| 2 | Useful supporting evidence |", "| 3 | Direct evidence |", "",
        "All-zero judgments are allowed when nothing in this collection helps answer the question.",
        "Candidate order is shuffled, not ranked. Prior grades, expected answers, scores, and aliases are omitted.",
        "Judge the saved text. Source links are for provenance; live pages may differ from this dated snapshot.",
        "Question origin: " + packet.question_origin + ". Existing development questions are not held out.",
        "A completed form does not authenticate reviewer independence or establish answer correctness.", "", "## Questions", ""]
    for question in packet.questions:
        lines += [f"### {question.case_id}", "", question.query, "", "Candidate order:", "",
                  ", ".join("`" + key + "`" for key in question.candidate_ids), ""]
    lines += ["## Saved evidence", ""]
    for chunk in packet.evidence:
        lines += [f"### {chunk.chunk_id}", "", chunk.text, "", "Sources:", ""]
        for sid in chunk.source_ids:
            source = sources[sid]
            lines.append(f"- {sid}: {source.title} — {source.url} (snapshot retrieved {source.retrieved_at.isoformat()})")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"
