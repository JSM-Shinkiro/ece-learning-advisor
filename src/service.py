"""Compose retrieval, academic checks, evidence context, and generation."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .catalog import build_evidence, code_lookup, corpus_hash
from .models import Catalog, GeneratedAnswer, GenerationContext, StudentProfile
from .providers import EmbeddingCache, ProviderError
from .planning import coverage_message, learning_phase, needs_programming_foundations
from .retrieval import Hit, Retriever
from .rules import dependency_codes, evaluate_course


class CitationError(ValueError):
    pass


def validate_answer(answer: GeneratedAnswer, context: GenerationContext):
    evidence = {e.chunk_id: e for e in context.evidence}
    used = set()
    for recommendation in answer.recommendations:
        if recommendation.record_id not in context.allowed_record_ids:
            raise CitationError("The response recommended an out-of-context record")
        if recommendation.record_id in used:
            raise CitationError("The response repeated a recommendation")
        used.add(recommendation.record_id)
        direct_reference = False
        for reason in recommendation.reasons:
            if re.search(r"https?://", reason.text, flags=re.I):
                raise CitationError("Generated URLs cannot be used as citations")
            for citation in reason.evidence_ids:
                if citation not in evidence:
                    raise CitationError("The response cited evidence not supplied to the model")
                direct_reference |= evidence[citation].record_id == recommendation.record_id
        if not direct_reference:
            raise CitationError("A recommendation needs evidence about that record")
    return answer


@dataclass
class AdvisorResult:
    context: GenerationContext
    hits: list[Hit]
    answer: GeneratedAnswer | None = None
    retrieval_mode: str = "keyword"
    generation_complete: bool = False
    generation_status: str = "not_requested"
    coverage_notice: str | None = None
    issues: list[str] = field(default_factory=list)
    timings: dict[str, float] = field(default_factory=dict)
    vectors: np.ndarray | None = None
    query_vector: np.ndarray | None = None
    cache_state: str = "not_used"
    trace: dict = field(default_factory=dict)


def build_query(catalog: Catalog, profile: StudentProfile, question: str):
    careers = [r for r in catalog.records if r.kind == "career" and (
        profile.career_id == "exploring" or r.record_id == "career:" + profile.career_id)]
    direction = " ".join(r.title + " " + " ".join(r.topics) for r in careers)
    foundations = "introductory programming foundations C" if needs_programming_foundations(profile) else ""
    return " ".join([direction, foundations, profile.interests, profile.experience, question]).strip()[:5000]


def build_context(catalog: Catalog, profile: StudentProfile, question: str, query: str,
                  hits: list[Hit], max_chunks=8, max_characters=16000):
    records = {r.record_id: r for r in catalog.records}
    chunks = {e.record_id: e for e in build_evidence(catalog)}
    completed = {c.course_code for c in profile.completed if c.grade not in {"E", "F"}}
    courses, resources = [], []
    for hit in hits:
        record = records[hit.record_id]
        if record.career_ids and profile.career_id != "exploring" and profile.career_id not in record.career_ids:
            continue
        if record.kind == "course" and record.code not in completed and record.record_id not in courses:
            courses.append(record.record_id)
        elif record.kind == "resource" and record.record_id not in resources:
            resources.append(record.record_id)
    beginner = needs_programming_foundations(profile)
    if beginner:
        foundations=[rid for rid in courses if records[rid].study_stage=="foundation"]
        bridges=[rid for rid in courses if records[rid].study_stage=="intermediate"]
        goals=[rid for rid in courses if records[rid].study_stage=="advanced"]
        courses=(foundations[:1]+bridges[:1]+goals[:1])[:3]
        resources=sorted(resources,key=lambda rid:records[rid].study_stage!="foundation")
    if profile.career_id == "exploring":
        # Show both directions instead of allowing one query to displace the other.
        foundations=[rid for rid in courses if records[rid].study_stage=="foundation"]
        goals=[]
        candidates=[h.record_id for h in hits if records[h.record_id].kind=="course"
                    and records[h.record_id].code not in completed]
        for career in ["ai_ml", "embedded"]:
            matches=[rid for rid in candidates if records[rid].study_stage=="advanced"
                     and career in records[rid].career_ids]
            goals.extend(matches[:1])
        courses=list(dict.fromkeys(foundations[:1]+goals+courses))[:3]
    selected = courses[:3] + resources[:2]
    career_ids = [
        r.record_id for r in catalog.records
        if r.kind == "career" and (profile.career_id == "exploring" or r.record_id == "career:" + profile.career_id)
    ]
    # Include supporting rules from the full collection, independently of relevance.
    lookup = code_lookup(catalog)
    dependency_ids = []
    queue = [records[r] for r in courses[:3]]
    seen = set()
    while queue:
        record = queue.pop(0)
        if record.record_id in seen:
            continue
        seen.add(record.record_id)
        if record.rule_reviewed:
            for code in dependency_codes(record.rule):
                dependency = lookup.get(code)
                if dependency and dependency.record_id not in seen:
                    dependency_ids.append(dependency.record_id)
                    queue.append(dependency)
    # A reviewed rule is contained in the course chunk. Additional descriptions
    # help exploration, but an absent alternative must not invalidate a satisfied OR.
    ordered = list(dict.fromkeys(selected + dependency_ids + career_ids))
    evidence, consumed = [], 0
    for record_id in ordered:
        candidate = chunks[record_id]
        if len(evidence) >= max_chunks or consumed + len(candidate.text) > max_characters:
            continue
        evidence.append(candidate)
        consumed += len(candidate.text)
    included = {e.record_id for e in evidence}
    allowed = [r for r in selected if r in included]
    rule_results = {}
    for record_id in allowed:
        record = records[record_id]
        if record.kind == "course":
            evaluation = evaluate_course(record, profile)
            if record.rule_reviewed:
                absent = [c for c in dependency_codes(record.rule) if c not in lookup]
                omitted = [c for c in dependency_codes(record.rule) if c in lookup and lookup[c].record_id not in included]
                if (absent or omitted) and evaluation.status == "unknown":
                    evaluation.reasons.append("Some supporting requirement records are outside this reviewed context.")
            rule_results[record_id] = evaluation
    return GenerationContext(
        profile=profile, question=question, query=query,
        allowed_record_ids=allowed, evidence=evidence, rule_results=rule_results,
        suggested_phases={rid:learning_phase(records[rid], profile, rule_results.get(rid)) for rid in allowed},
    )


def recommend(catalog: Catalog, profile: StudentProfile, question: str = "",
              provider=None, method="hybrid", cache_dir=Path(".cache/embeddings")) -> AdvisorResult:
    started = time.perf_counter()
    question = question or profile.question
    if len(question) > 1200:
        raise ValueError("Keep the learning question within 1,200 characters")
    notice = coverage_message(catalog, profile, question)
    if notice:
        context = GenerationContext(profile=profile, question=question, query=question,
                                    allowed_record_ids=[], evidence=[], rule_results={})
        result = AdvisorResult(context=context, hits=[], coverage_notice=notice,
                               generation_status="insufficient_evidence")
        result.timings["total"] = time.perf_counter() - started
        result.trace = {"data_version":catalog.version, "prompt_version":context.prompt_version,
                        "generation_status":"insufficient_evidence", "generation_complete":False,
                        "coverage_guard":"no_vocabulary_match", "model_calls":0,
                        "context_chunk_ids":[], "allowed_record_ids":[], "timings_seconds":result.timings}
        return result
    chunks = build_evidence(catalog)
    query = build_query(catalog, profile, question)
    vectors, query_vector, manifest = None, None, {}
    issues, timings = [], {}
    mode, cache_state = "keyword", "not_used"
    if provider and method in {"semantic", "hybrid"}:
        before = time.perf_counter()
        try:
            vectors, cache_state, manifest = EmbeddingCache(cache_dir).get(catalog, chunks, provider)
            query_vector = provider.embed_query(query)
            mode = method
        except (ProviderError, ValueError):
            issues.append("Semantic retrieval is unavailable. Using keyword retrieval for this request.")
            vectors, query_vector = None, None
        timings["embedding"] = time.perf_counter() - before
    before = time.perf_counter()
    retriever = Retriever(chunks, vectors)
    hits = retriever.search(query, mode, query_vector)
    timings["retrieval"] = time.perf_counter() - before
    context = build_context(catalog, profile, question, query, hits)
    result = AdvisorResult(
        context=context, hits=hits, retrieval_mode=mode,
        issues=issues, timings=timings, vectors=vectors,
        query_vector=query_vector, cache_state=cache_state,
    )
    if provider and context.allowed_record_ids:
        before = time.perf_counter()
        try:
            result.answer = validate_answer(provider.generate(context), context)
            result.generation_status = result.answer.status
            result.generation_complete = result.answer.status == "answered"
        except (ProviderError, CitationError, ValueError):
            result.generation_status = "failed"
            result.issues.append("The AI explanation was unavailable or failed reference checks. Showing source information.")
        timings["generation"] = time.perf_counter() - before
    elif provider:
        result.generation_status = "insufficient_evidence"
        result.issues.append("There is not enough reviewed evidence for this request.")
    timings["total"] = time.perf_counter() - started
    result.trace = {
        "data_version": catalog.version,
        "corpus_hash": corpus_hash(catalog),
        "prompt_version": context.prompt_version,
        "retrieval_mode": mode,
        "embedding_model": getattr(provider, "embedding_model", None),
        "generation_model": getattr(provider, "generation_model", None),
        "cache_state": cache_state,
        "retrieved_chunk_ids": [h.chunk_id for h in hits],
        "context_chunk_ids": [e.chunk_id for e in context.evidence],
        "allowed_record_ids": context.allowed_record_ids,
        "generation_complete": result.generation_complete,
        "generation_status": result.generation_status,
        "reference_checks_passed": True if result.answer else (False if result.generation_status=="failed" else None),
        "timings_seconds": timings,
    }
    return result
