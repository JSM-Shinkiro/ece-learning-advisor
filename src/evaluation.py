"""Frozen development references for retrieval, roadmap policy, and claim audits.

Claim verdicts are authored review labels, never inferred from citation validity.
The default runner uses a fixed local corpus and makes no provider requests.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .catalog import ROOT, build_evidence, corpus_hash
from .models import (ExplanationSelection, GeneratedAnswer, GenerationContext, SelectedRecommendation,
                     SourceFreshness, StrictModel, StudentProfile)
from .planning import learning_phase
from .providers import EmbeddingCache
from .retrieval import Retriever
from .rules import evaluate_course
from .service import CitationError, recommend, validate_answer, validate_references
from .grounding import ANSWER_CONTRACT, GroundingError, build_statements, materialize_answer
from .query import QUERY_POLICY_VERSION, interpret_query

DEFAULT_SUITE = ROOT / "data" / "evaluation" / "reviewed_v1.json"
Grade = Annotated[int, Field(strict=True, ge=0, le=3)]
RuleStatus = Literal["satisfied", "unsatisfied", "unknown"]
Verification = Literal["snapshot", "verified", "stale", "changed", "unavailable", "unsupported", "unreviewed"]


class RetrievalCase(StrictModel):
    case_id: str
    split: Literal["development", "validation"]
    query: str = Field(min_length=1, max_length=1200)
    relevance: dict[str, Grade] = Field(min_length=1, max_length=100)
    rationale: str = Field(min_length=1, max_length=1600)


class RuleExpectation(StrictModel):
    status: RuleStatus
    verification: Verification = "snapshot"


class PolicyCase(StrictModel):
    case_id: str
    profile: StudentProfile
    required_records: list[str] = Field(default_factory=list)
    forbidden_records: list[str] = Field(default_factory=list)
    first_course: str | None = None
    rule_results: dict[str, RuleExpectation] = Field(default_factory=dict)
    phases: dict[str, Literal["next", "build", "later"]] = Field(default_factory=dict)
    coverage_notice: bool = False
    rule_state_overrides: dict[str, Literal["stale", "changed", "unavailable", "unsupported"]] = Field(default_factory=dict)
    rationale: str = Field(min_length=1, max_length=1600)


class ClaimReview(StrictModel):
    recommendation_index: int = Field(ge=0)
    reason_index: int = Field(ge=0)
    verdict: Literal["supported", "contradicted", "insufficient_evidence", "recommendation"]
    reference_evidence_ids: list[str] = Field(default_factory=list)
    rationale: str = Field(min_length=1, max_length=1600)


class ClaimProbe(StrictModel):
    case_id: str
    profile: StudentProfile = Field(default_factory=StudentProfile)
    allowed_record_ids: list[str] = Field(min_length=1, max_length=5)
    context_chunk_ids: list[str] = Field(min_length=1, max_length=8)
    answer: GeneratedAnswer
    reference_integrity_expected: bool
    reviews: list[ClaimReview] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def reviews_cover_each_reason(self):
        expected = {(i, j) for i, rec in enumerate(self.answer.recommendations) for j, _ in enumerate(rec.reasons)}
        actual = [(r.recommendation_index, r.reason_index) for r in self.reviews]
        if len(actual) != len(set(actual)) or set(actual) != expected:
            raise ValueError("Each authored probe reason needs exactly one review label")
        for review in self.reviews:
            reason = self.answer.recommendations[review.recommendation_index].reasons[review.reason_index]
            if (review.verdict == "recommendation") != (reason.claim_type == "recommendation"):
                raise ValueError("Recommendation reviews must match the authored claim type")
        return self


class EvaluationSuite(StrictModel):
    schema_version: Literal[1] = 1
    suite_id: str
    label_origin: Literal["assistant-authored source review"]
    limitations: str
    corpus_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    catalog_snapshot_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    labels_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    binary_relevance_minimum: Literal[2] = 2
    retrieval_cases: list[RetrievalCase] = Field(min_length=1, max_length=100)
    policy_cases: list[PolicyCase] = Field(min_length=1, max_length=100)
    claim_probes: list[ClaimProbe] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_cases(self):
        ids = [c.case_id for cases in (self.retrieval_cases, self.policy_cases, self.claim_probes) for c in cases]
        if len(ids) != len(set(ids)):
            raise ValueError("Evaluation case identities must be unique")
        return self


def suite_hash(suite):
    return hashlib.sha256(json.dumps(suite.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()


def catalog_snapshot_hash(catalog):
    # Evidence identity alone does not capture rule trees, stages, or freshness.
    return hashlib.sha256(json.dumps(catalog.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()


def labels_hash(suite):
    data = suite.model_dump(mode="json") if isinstance(suite, EvaluationSuite) else suite
    labels = {key: data[key] for key in ("retrieval_cases", "policy_cases", "claim_probes")}
    return hashlib.sha256(json.dumps(labels, sort_keys=True).encode()).hexdigest()


def validate_suite(suite, catalog):
    if suite.corpus_hash != corpus_hash(catalog) or suite.catalog_snapshot_hash != catalog_snapshot_hash(catalog):
        raise ValueError("The frozen evaluation corpus changed; review the labels before creating a new suite")
    if suite.labels_hash != labels_hash(suite):
        raise ValueError("The frozen reference labels changed; review and version the suite explicitly")
    chunks = {e.chunk_id: e for e in build_evidence(catalog)}
    records = {r.record_id: r for r in catalog.records}
    for case in suite.retrieval_cases:
        if set(case.relevance) != set(chunks) or not any(g >= suite.binary_relevance_minimum for g in case.relevance.values()):
            raise ValueError("Each retrieval case needs complete judgments and at least one relevant chunk")
        if not case.query.strip():
            raise ValueError("Retrieval queries cannot be blank")
    for case in suite.policy_cases:
        referenced = (set(case.required_records) | set(case.forbidden_records) | set(case.rule_results)
                      | set(case.phases) | set(case.rule_state_overrides) | ({case.first_course} if case.first_course else set()))
        if not referenced <= records.keys() or set(case.required_records) & set(case.forbidden_records):
            raise ValueError("Policy references must resolve without contradictory inclusion expectations")
        if not set(case.rule_results) <= set(case.required_records) or not set(case.phases) <= set(case.required_records):
            raise ValueError("Policy status/phase expectations need a required record")
        for rid in set(case.rule_results) | set(case.rule_state_overrides) | ({case.first_course} if case.first_course else set()):
            if records[rid].kind != "course":
                raise ValueError("Academic expectations must refer to a course")
    for probe in suite.claim_probes:
        if (not set(probe.allowed_record_ids) <= records.keys() or not set(probe.context_chunk_ids) <= chunks.keys()
                or len(probe.context_chunk_ids) != len(set(probe.context_chunk_ids))
                or len(probe.allowed_record_ids) != len(set(probe.allowed_record_ids))
                or sum(len(chunks[key].text) for key in probe.context_chunk_ids) > 16000):
            raise ValueError("Probe contexts must resolve to unique supplied evidence")
        context_ids = set(probe.context_chunk_ids)
        for rid in probe.allowed_record_ids:
            needed = {e.chunk_id for e in chunks.values() if e.record_id == rid}
            if not needed <= context_ids:
                raise ValueError("An allowed probe record must retain its complete evidence bundle")
        for review in probe.reviews:
            if not set(review.reference_evidence_ids) <= context_ids:
                raise ValueError("Claim review references must be present in the probe context")
    return suite


def load_suite(catalog, path=DEFAULT_SUITE):
    return validate_suite(EvaluationSuite.model_validate_json(Path(path).read_bytes()), catalog)


def rank_metrics(ranked_ids, judgments, *, k=5, relevant_minimum=2):
    """Fixed-k precision, recall, truncated reciprocal rank, and linear-gain nDCG."""
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= 100:
        raise ValueError("The ranking cutoff must be an integer from 1 to 100")
    if isinstance(relevant_minimum, bool) or not isinstance(relevant_minimum, int) or not 1 <= relevant_minimum <= 3:
        raise ValueError("The binary relevance threshold must be an integer from one to three")
    if len(ranked_ids) != len(set(ranked_ids)) or not set(ranked_ids) <= judgments.keys():
        raise ValueError("Ranked evidence IDs must be unique and judged")
    if any(isinstance(g, bool) or not isinstance(g, int) or not 0 <= g <= 3 for g in judgments.values()):
        raise ValueError("Relevance grades must be integers from zero to three")
    relevant = {key for key, grade in judgments.items() if grade >= relevant_minimum}
    top = ranked_ids[:k]
    found = [i for i, key in enumerate(top, 1) if key in relevant]
    dcg = sum(judgments[key] / math.log2(i + 1) for i, key in enumerate(top, 1))
    ideal = sum(grade / math.log2(i + 1) for i, grade in enumerate(sorted(judgments.values(), reverse=True)[:k], 1))
    return {"precision": len(found) / k, "recall": len(found) / len(relevant) if relevant else None,
            "reciprocal_rank": 1 / found[0] if found else (0.0 if relevant else None),
            "ndcg": dcg / ideal if ideal else None}


def _aggregate(rows):
    metrics = {metric: mean(values) if (values := [r["metrics"][metric] for r in rows if r["metrics"][metric] is not None]) else None
               for metric in ("precision", "recall", "reciprocal_rank", "ndcg")}
    return {**metrics, "precision_ceiling": mean(r["precision_ceiling"] for r in rows)}


def _policy_result(catalog, case):
    active = catalog.model_copy(deep=True)
    for record in active.records:
        if record.record_id in case.rule_state_overrides:
            record.rule_verification = case.rule_state_overrides[record.record_id]
            for proof in record.rule_evidence:
                proof.verification_status = record.rule_verification
    result = recommend(active, case.profile, method="keyword")
    context = result.context
    allowed = context.allowed_record_ids
    record_map = {r.record_id: r for r in active.records}
    courses = [rid for rid in allowed if record_map[rid].kind == "course"]
    checks = {"coverage_notice": bool(result.coverage_notice) == case.coverage_notice,
              "required_records": set(case.required_records) <= set(allowed),
              "forbidden_records": not set(case.forbidden_records) & set(allowed)}
    if case.first_course:
        checks["first_course"] = bool(courses) and courses[0] == case.first_course
    for rid, expected in case.rule_results.items():
        observed = context.rule_results.get(rid)
        checks["rule:" + rid] = observed is not None and observed.status == expected.status and observed.verification_status == expected.verification
    for rid, phase in case.phases.items():
        checks["phase:" + rid] = context.suggested_phases.get(rid) == phase
    return {"case_id": case.case_id, "passed": all(checks.values()), "checks": checks,
        "scenario_snapshot_hash": catalog_snapshot_hash(active),
        "allowed_record_ids": allowed, "coverage_notice": bool(result.coverage_notice),
        "rule_results": {rid: rule.model_dump(mode="json") for rid, rule in context.rule_results.items()},
        "phases": context.suggested_phases, "synthetic_rule_state_overrides": case.rule_state_overrides,
        "context_chunk_ids": [e.chunk_id for e in context.evidence], "rationale": case.rationale}


def _probe_context(catalog, probe):
    chunks = {e.chunk_id: e for e in build_evidence(catalog)}
    records = {r.record_id: r for r in catalog.records}
    evidence = [chunks[key] for key in probe.context_chunk_ids]
    source_ids = {sid for e in evidence for sid in e.source_ids}
    rules = {rid: evaluate_course(records[rid], probe.profile) for rid in probe.allowed_record_ids if records[rid].kind == "course"}
    context = GenerationContext(profile=probe.profile, question=probe.profile.question, query=probe.profile.question,
        allowed_record_ids=probe.allowed_record_ids, evidence=evidence, rule_results=rules,
        source_freshness={s.source_id: SourceFreshness(verification_status=s.verification_status,
            retrieved_at=s.retrieved_at, last_checked_at=s.last_checked_at) for s in catalog.sources if s.source_id in source_ids},
        suggested_phases={rid: learning_phase(records[rid], probe.profile, rules.get(rid)) for rid in probe.allowed_record_ids})
    context.field_sources = {rid: records[rid].field_sources for rid in probe.allowed_record_ids if records[rid].field_sources}
    context.allowed_statements = build_statements(catalog, context)
    return context


def _claim_result(catalog, probe):
    error = None
    context = _probe_context(catalog, probe)
    try:
        validate_references(probe.answer, context)
    except CitationError as exc:
        error = str(exc)
    accepted = error is None
    render_error = None
    try:
        validate_answer(probe.answer, context, catalog)
    except (CitationError, GroundingError) as exc:
        render_error = exc.code if isinstance(exc, GroundingError) else "invalid_reference"
    # Positive controls use every available canonical statement, not authored
    # paraphrases. A validator that rejects everything must fail this audit.
    control_failures = []
    for statement in context.allowed_statements:
        selection = ExplanationSelection(status="answered", recommendations=[SelectedRecommendation(
            record_id=statement.record_id, statement_ids=[statement.statement_id])])
        try:
            answer = materialize_answer(selection, context, catalog)
            validate_answer(answer, context, catalog)
        except (CitationError, GroundingError) as exc:
            control_failures.append({"statement_id": statement.statement_id,
                "error": exc.code if isinstance(exc, GroundingError) else "invalid_reference"})
    claims = []
    for review in probe.reviews:
        recommendation = probe.answer.recommendations[review.recommendation_index]
        reason = recommendation.reasons[review.reason_index]
        claims.append({**review.model_dump(mode="json"), "text": reason.text, "claim_type": reason.claim_type,
            "cited_evidence_ids": reason.evidence_ids,
            "unsupported_claim_admitted_by_render_contract": render_error is None and review.verdict in {"contradicted", "insufficient_evidence"},
            "unsupported_claim_admitted_by_reference_checks": accepted and review.verdict in {"contradicted", "insufficient_evidence"}})
    return {"case_id": probe.case_id, "answer_origin": "authored_probe", "reference_checks_accepted": accepted,
        "reference_integrity_expected": probe.reference_integrity_expected,
        "integrity_matches_reference": accepted == probe.reference_integrity_expected,
        "reference_error": error, "reference_reviews": claims,
        "render_contract_accepted": render_error is None, "render_contract_error": render_error,
        "canonical_controls": {"attempted": len(context.allowed_statements),
            "accepted": len(context.allowed_statements) - len(control_failures), "failures": control_failures}}


def _implementation_hash():
    files = ["src/evaluation.py", "src/retrieval.py", "src/service.py", "src/models.py", "src/catalog.py",
             "src/planning.py", "src/query.py", "src/rules.py", "src/providers.py", "src/grounding.py", "scripts/evaluate_reviewed.py"]
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files}
    return {"files": hashes, "sha256": hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()}


class _CountedEmbeddings:
    def __init__(self, provider):
        self.provider, self.document_calls, self.query_calls = provider, 0, 0
        self.embedding_model, self.dimensions = provider.embedding_model, provider.dimensions

    def embed_document(self, chunk):
        self.document_calls += 1
        return self.provider.embed_document(chunk)

    def embed_query(self, query):
        self.query_calls += 1
        return self.provider.embed_query(query)


def evaluate_suite(catalog, suite, *, k=5, methods=("keyword",), embedder=None, embedding_origin=None,
                   cache_dir=ROOT / ".cache" / "evaluation_embeddings", query_mode="raw"):
    validate_suite(suite, catalog)
    if not methods or len(set(methods)) != len(methods) or not set(methods) <= {"keyword", "semantic", "hybrid"}:
        raise ValueError("Choose unique supported retrieval methods")
    if query_mode not in {"raw", "expanded"}:
        raise ValueError("Choose raw or expanded query evaluation")
    neural = bool(set(methods) & {"semantic", "hybrid"})
    if neural and (embedder is None or embedding_origin not in {"live_provider", "controlled_fixture"}):
        raise ValueError("Semantic/hybrid evaluation needs an explicit embedding provider and origin; no silent keyword fallback")
    chunks = build_evidence(catalog)
    by_chunk = {e.chunk_id: e for e in chunks}
    # Validate the cutoff before any optional provider requests.
    rank_metrics([], suite.retrieval_cases[0].relevance, k=k)
    counted = _CountedEmbeddings(embedder) if neural else None
    vectors, cache_state = None, "not_used"
    if neural:
        vectors, cache_state, _ = EmbeddingCache(cache_dir).get(catalog, chunks, counted)
    retriever = Retriever(chunks, vectors)
    rows = []
    for case in suite.retrieval_cases:
        interpretation = interpret_query(case.query, catalog) if query_mode == "expanded" else None
        effective_query = interpretation.expand(case.query) if interpretation else case.query
        query_vector = counted.embed_query(effective_query) if neural else None
        for method in methods:
            started = time.perf_counter()
            hits = retriever.search(effective_query, method=method, query_vector=query_vector, limit=max(k, 20))
            elapsed = time.perf_counter() - started
            relevant_ids = [key for key, grade in case.relevance.items() if grade >= suite.binary_relevance_minimum]
            rows.append({"case_id": case.case_id, "split": case.split, "method": method, "query": case.query,
                "effective_query": effective_query, "query_interpretation": interpretation.trace() if interpretation else None,
                "ranked_chunk_ids": [h.chunk_id for h in hits], "scores": [h.score for h in hits],
                "relevant_chunk_ids": relevant_ids,
                "relevant_source_ids": sorted({sid for key in relevant_ids for sid in by_chunk[key].source_ids}),
                "retrieved_source_ids_at_k": sorted({sid for hit in hits[:k] for sid in by_chunk[hit.chunk_id].source_ids}),
                "precision_ceiling": min(k, len(relevant_ids)) / k,
                "metrics": rank_metrics([h.chunk_id for h in hits], case.relevance, k=k,
                    relevant_minimum=suite.binary_relevance_minimum),
                "ranking_seconds": elapsed, "rationale": case.rationale})
    policies = [_policy_result(catalog, case) for case in suite.policy_cases]
    claims = [_claim_result(catalog, probe) for probe in suite.claim_probes]
    verdicts = Counter(review["verdict"] for case in claims for review in case["reference_reviews"])
    gaps = sum(review["unsupported_claim_admitted_by_reference_checks"] for case in claims for review in case["reference_reviews"])
    render_gaps = sum(r["unsupported_claim_admitted_by_render_contract"] for c in claims for r in c["reference_reviews"])
    controls = {key: sum(c["canonical_controls"][key] for c in claims) for key in ("attempted", "accepted")}
    return {"schema_version": 1, "suite_id": suite.suite_id, "suite_hash": suite_hash(suite),
        "created_at": datetime.now(timezone.utc).isoformat(), "data_version": catalog.version,
        "corpus_hash": corpus_hash(catalog), "catalog_snapshot_hash": catalog_snapshot_hash(catalog),
        "labels_hash": labels_hash(suite), "evidence_count": len(chunks), "cutoff": k,
        "label_origin": suite.label_origin, "limitations": suite.limitations,
        "prompt_version": GenerationContext.model_fields['prompt_version'].default,
        "metric_conventions": {"unit": "evidence chunk", "binary_relevance_minimum": suite.binary_relevance_minimum,
            "precision_denominator": "fixed cutoff, including short result lists", "ndcg_gain": "linear grade / log2(rank + 1)",
            "ties": "retriever score order, then stable chunk ID", "aggregation": "equal query weights; undefined values excluded"},
        "retrieval_query_mode": ("raw reference query without profile expansion" if query_mode == "raw"
                                 else "domain-alias expansion without profile expansion"),
        "query_mode": query_mode, "runtime_query_policy": QUERY_POLICY_VERSION, "policy_method": "keyword",
        "implementation": _implementation_hash(), "methods": list(methods),
        "embedding": {"origin": embedding_origin if neural else None,
            "model": counted.embedding_model if counted else None, "dimensions": counted.dimensions if counted else None,
            "cache_state": cache_state, "document_calls": counted.document_calls if counted else 0,
            "query_calls": counted.query_calls if counted else 0}, "generation_calls": 0, "source_refresh_calls": 0,
        "retrieval_summary": {method: {split: {"cases": len(selected), **_aggregate(selected)}
            for split in ("development", "validation", "all")
            if (selected := [row for row in rows if row["method"] == method and (split == "all" or row["split"] == split)])}
            for method in methods}, "retrieval_cases": rows,
        "policy_summary": {"cases": len(policies), "passed": sum(p["passed"] for p in policies)}, "policy_cases": policies,
        "claim_summary": {"authored_probes": len(claims), "reference_verdicts": dict(verdicts),
            "integrity_expectations_matched": sum(c["integrity_matches_reference"] for c in claims),
            "unsupported_claims_admitted_by_reference_checks": gaps,
            "scope": "Authored counterexamples; not generated-model accuracy or an automatic entailment score."},
        "render_contract_summary": {"answer_contract": ANSWER_CONTRACT,
            "legacy_authored_answers_accepted": sum(c["render_contract_accepted"] for c in claims),
            "unsupported_reviewed_claims_admitted": render_gaps, "canonical_controls": controls,
            "scope": "Strict application-owned wording contract, not an unrestricted entailment classifier."},
        "claim_probes": claims,
        "regression_checks_passed": (all(p["passed"] for p in policies)
            and all(c["integrity_matches_reference"] for c in claims)
            and render_gaps == 0 and controls["attempted"] > 0 and controls["accepted"] == controls["attempted"])}


def report_markdown(report):
    def fmt(value):
        return f"{value:.4f}" if value is not None else "n/a"
    lines = ["# Reviewed development evaluation", "", "Fixed saved corpus; assistant-authored references. This is not an independent held-out benchmark.",
        "", f"Suite: `{report['suite_id']}` · {report['evidence_count']} evidence chunks · cutoff {report['cutoff']}.",
        f"Suite hash: `{report['suite_hash']}`.", f"Corpus hash: `{report['corpus_hash']}`.",
        f"Retrieval query mode: {report['retrieval_query_mode']}.",
        "Expanded-query results use aliases authored after the known misses; they are development tuning, not held-out validation."
        if report['query_mode'] == 'expanded' else "Raw-query scoring preserves the original retrieval input.", "",
        "| Method | Split | Cases | Precision | Maximum precision | Recall | MRR | nDCG |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for method, splits in report["retrieval_summary"].items():
        for split, row in splits.items():
            lines.append(f"| {method} | {split} | {row['cases']} | " + " | ".join(fmt(row[m]) for m in ("precision", "precision_ceiling", "recall", "reciprocal_rank", "ndcg")) + " |")
    p, c = report["policy_summary"], report["claim_summary"]
    contract = report["render_contract_summary"]
    lines += ["", f"Roadmap expectations passed: {p['passed']}/{p['cases']}.",
        f"Citation-integrity expectations matched: {c['integrity_expectations_matched']}/{c['authored_probes']} authored probes.",
        f"Authored unsupported/contradicted claims admitted by citation checks: {c['unsupported_claims_admitted_by_reference_checks']}.",
        "Claim verdicts are supplied review labels. Citation acceptance does not infer factual support.", "",
        "## Application-owned explanation contract", "",
        f"Contract: `{contract['answer_contract']}`. Unsupported reviewed claims admitted: {contract['unsupported_reviewed_claims_admitted']}.",
        f"Canonical statement controls accepted: {contract['canonical_controls']['accepted']}/{contract['canonical_controls']['attempted']}.",
        f"Legacy authored answers accepted: {contract['legacy_authored_answers_accepted']}/{c['authored_probes']}.",
        "This contract also rejects true paraphrases that are outside the application-owned wording. It does not classify unrestricted prose entailment.",
        "Controls are authored offline selections, not live model accuracy or recommendation-quality measurements.", "",
        f"Embedding origin: {report['embedding']['origin'] or 'none'}. Generation calls: {report['generation_calls']}. Source refresh calls: {report['source_refresh_calls']}.",
        "Local ranking times exclude network, generation, source refresh, and interface rendering.", "", "## Missed relevant evidence", ""]
    misses = [row for row in report["retrieval_cases"] if row["metrics"]["recall"] is not None and row["metrics"]["recall"] < 1]
    lines.extend(f"- `{row['case_id']}` ({row['method']}): recall {fmt(row['metrics']['recall'])}." for row in misses)
    if not misses:
        lines.append("No misses in this small reference set.")
    return "\n".join(lines) + "\n"
