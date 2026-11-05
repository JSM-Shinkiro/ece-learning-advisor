"""Compose retrieval, academic checks, evidence context, and generation."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .catalog import build_evidence, code_lookup, corpus_hash
from .models import Catalog, GeneratedAnswer, GenerationContext, SourceFreshness, StudentProfile
from .providers import EmbeddingCache, ProviderError
from .planning import coverage_message, learning_phase, needs_programming_foundations, requested_record_ids
from .retrieval import Hit, Retriever, tokenize
from .rules import dependency_codes, evaluate_course
from .grounding import ANSWER_CONTRACT, GroundingError, build_statements, materialize_answer, validate_wording
from .query import interpret_query


class CitationError(ValueError):
    pass


def validate_references(answer: GeneratedAnswer, context: GenerationContext):
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


def validate_answer(answer: GeneratedAnswer, context: GenerationContext, catalog: Catalog):
    try:
        answer = GeneratedAnswer.model_validate(answer.model_dump())
    except (ValueError, AttributeError) as exc:
        raise GroundingError("invalid_answer", "The rendered explanation has an invalid structure") from exc
    validate_references(answer, context)
    return validate_wording(answer, context, catalog)


@dataclass
class AdvisorResult:
    context: GenerationContext
    hits: list[Hit]
    catalog: Catalog | None = None
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
    selected_statement_ids: list[str] = field(default_factory=list)
    statement_validation_passed: bool | None = None
    validation_error: str | None = None
    trace: dict = field(default_factory=dict)


def build_query(catalog: Catalog, profile: StudentProfile, question: str, *, interpretation=None):
    careers = [r for r in catalog.records if r.kind == "career" and (
        profile.career_id == "exploring" or r.record_id == "career:" + profile.career_id)]
    direction = " ".join(r.title + " " + " ".join(r.topics) for r in careers)
    foundations = "introductory programming foundations C" if needs_programming_foundations(profile) else ""
    interpretation = interpretation or interpret_query(question.strip() or profile.interests.strip(), catalog)
    original = " ".join([direction, foundations, profile.interests, profile.experience, question]).strip()
    suffix = " ".join(interpretation.added_terms)
    # Reserve space for bounded aliases even with a maximum-length profile.
    return (original[:5000 - len(suffix) - 1] + " " + suffix).strip() if suffix else original[:5000]


def build_context(catalog: Catalog, profile: StudentProfile, question: str, query: str,
                  hits: list[Hit], max_chunks=8, max_characters=16000, *, focused_record_ids=()):
    records = {r.record_id: r for r in catalog.records}
    chunks = {}
    for chunk in build_evidence(catalog):
        chunks.setdefault(chunk.record_id, []).append(chunk)
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
    # A matched question may prefer an existing course, without changing the
    # selected career, excluding foundations, or granting academic clearance.
    courses.sort(key=lambda rid: rid not in focused_record_ids)
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
        focused = [rid for rid in courses if rid in focused_record_ids]
        courses=list(dict.fromkeys(foundations[:1]+focused[:1]+goals+courses))[:3]
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
    # Keep reviewed conditions with their course evidence. Additional dependency
    # descriptions help exploration; an absent alternative cannot invalidate a satisfied OR.
    ordered = list(dict.fromkeys(selected + dependency_ids + career_ids))
    evidence, consumed = [], 0
    for record_id in ordered:
        candidates = chunks[record_id]
        size = sum(len(chunk.text) for chunk in candidates)
        # A recommendation must not lose its prerequisite-source evidence to
        # the context cutoff. Include each course's evidence as one bundle.
        if len(evidence) + len(candidates) > max_chunks or consumed + size > max_characters:
            continue
        evidence.extend(candidates)
        consumed += size
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
    context = GenerationContext(
        profile=profile, question=question, query=query,
        allowed_record_ids=allowed, evidence=evidence, rule_results=rule_results,
        source_freshness={s.source_id: SourceFreshness(
            verification_status=s.verification_status, retrieved_at=s.retrieved_at,
            last_checked_at=s.last_checked_at) for s in catalog.sources
            if s.source_id in {sid for chunk in evidence for sid in chunk.source_ids}},
        field_sources={rid: records[rid].field_sources for rid in allowed if records[rid].field_sources},
        suggested_phases={rid:learning_phase(records[rid], profile, rule_results.get(rid)) for rid in allowed},
    )
    context.allowed_statements = build_statements(catalog, context)
    return context


def recommend(catalog: Catalog, profile: StudentProfile, question: str = "",
              provider=None, method="hybrid", cache_dir=Path(".cache/embeddings"), *, preferred_course_codes=()) -> AdvisorResult:
    started = time.perf_counter()
    question = question or profile.question
    if len(question) > 1200:
        raise ValueError("Keep the learning question within 1,200 characters")
    interpretation = interpret_query(question.strip() or profile.interests.strip(), catalog)
    preferred = requested_record_ids(catalog, profile, preferred_course_codes)
    notice = coverage_message(catalog, profile, question)
    if notice and not preferred:
        context = GenerationContext(profile=profile, question=question, query=question,
                                    allowed_record_ids=[], evidence=[], rule_results={})
        result = AdvisorResult(context=context, hits=[], catalog=catalog, coverage_notice=notice,
                               generation_status="insufficient_evidence")
        result.timings["total"] = time.perf_counter() - started
        result.trace = {"data_version":catalog.version, "prompt_version":context.prompt_version,
                        "generation_status":"insufficient_evidence", "generation_complete":False,
                        "coverage_guard":"no_vocabulary_match", "model_calls":0,
                        "query_interpretation": interpretation.trace(),
                        "context_chunk_ids":[], "allowed_record_ids":[], "timings_seconds":result.timings}
        return result
    chunks = build_evidence(catalog)
    query = build_query(catalog, profile, question, interpretation=interpretation)
    records = {r.record_id: r for r in catalog.records}
    discovery_terms = [records[rid].code for rid in preferred if records[rid].code.lower() not in set(tokenize(query))]
    if discovery_terms:
        suffix = " ".join(discovery_terms)
        query = query[:5000 - len(suffix) - 1] + " " + suffix
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
    focused = preferred[:1]
    question_terms = set(tokenize(question))
    named_course = any(r.code and r.code.lower() in question_terms for r in catalog.records if r.kind == "course")
    if question.strip() and not focused:
        for hit in retriever.keyword(interpretation.expand(question)):
            record = records[hit.record_id]
            if record.kind != "course" or (profile.career_id != "exploring" and record.career_ids
                                          and profile.career_id not in record.career_ids):
                continue
            description_terms = set(tokenize(record.title + " " + record.summary + " " + " ".join(record.topics)))
            if interpretation.matched_aliases or named_course or len(question_terms & description_terms) >= 2:
                focused = [record.record_id]
                break
    timings["retrieval"] = time.perf_counter() - before
    context = build_context(catalog, profile, question, query, hits, focused_record_ids=focused)
    result = AdvisorResult(
        context=context, hits=hits, catalog=catalog, retrieval_mode=mode,
        issues=issues, timings=timings, vectors=vectors,
        query_vector=query_vector, cache_state=cache_state,
    )
    if provider and context.allowed_record_ids:
        before = time.perf_counter()
        try:
            selection = provider.generate(context)
            answer = materialize_answer(selection, context, catalog)
            result.answer = validate_answer(answer, context, catalog)
            result.selected_statement_ids = [sid for rec in selection.recommendations for sid in rec.statement_ids]
            result.statement_validation_passed = True
            result.generation_status = result.answer.status
            result.generation_complete = result.answer.status == "answered"
        except (ProviderError, CitationError, ValueError) as exc:
            result.generation_status = "failed"
            result.statement_validation_passed = False
            result.validation_error = (exc.code if isinstance(exc, GroundingError) else
                                       "invalid_reference" if isinstance(exc, CitationError) else "provider_or_format")
            result.issues.append("The AI explanation was unavailable or did not match the supported explanation format. Showing source information.")
        timings["generation"] = time.perf_counter() - before
    elif provider:
        result.generation_status = "insufficient_evidence"
        result.issues.append("There is not enough reviewed evidence for this request.")
    timings["total"] = time.perf_counter() - started
    result.trace = {
        "data_version": catalog.version,
        "corpus_hash": corpus_hash(catalog),
        "prompt_version": context.prompt_version,
        "query_interpretation": interpretation.trace(),
        "focused_record_ids": focused, "discovery_query_terms": discovery_terms,
        "retrieval_mode": mode,
        "embedding_model": getattr(provider, "embedding_model", None),
        "generation_model": getattr(provider, "generation_model", None),
        "cache_state": cache_state,
        "retrieved_chunk_ids": [h.chunk_id for h in hits],
        "context_chunk_ids": [e.chunk_id for e in context.evidence],
        "allowed_record_ids": context.allowed_record_ids,
        "source_freshness": {sid: status.model_dump(mode="json") for sid, status in context.source_freshness.items()},
        "field_sources": context.field_sources,
        "resource_versions": {r.record_id: r.resource_version for r in catalog.records
                              if r.kind == "resource" and r.resource_version},
        "answer_contract": ANSWER_CONTRACT,
        "selected_statement_ids": result.selected_statement_ids,
        "statement_validation_passed": result.statement_validation_passed,
        "validation_error": result.validation_error,
        "generation_complete": result.generation_complete,
        "generation_status": result.generation_status,
        "reference_checks_passed": True if result.answer else (False if result.generation_status=="failed" else None),
        "timings_seconds": timings,
    }
    return result
