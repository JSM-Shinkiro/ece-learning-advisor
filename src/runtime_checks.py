"""Bounded provider-integration checks, separate from relevance evaluation."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import re

from .catalog import build_evidence, code_lookup, corpus_hash
from .controller import run_advisor
from .evaluation import catalog_snapshot_hash
from .learning_lab import PRESETS, RECORDS, advisor_embedding_comparison, build_lab_index, compare_ranks, run_experiment
from .models import Completion, StudentProfile
from .providers import GeminiProvider, ProviderError

DEMO_PRESET = "Program a sensor"
DEMO_QUESTION = PRESETS["Learn image classification"]
DEMO_COURSE = "ECE425"
REFRESHED_SOURCES = frozenset({"updated", "unchanged", "not_modified"})


@dataclass(frozen=True)
class CallBudget:
    document_embeddings: int = 64
    query_embeddings: int = 8
    generations: int = 8

    def __post_init__(self):
        for name, maximum in (("document_embeddings", 64), ("query_embeddings", 8), ("generations", 8)):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError("Verification budgets must be positive integers within the fixed limits")


@dataclass(frozen=True)
class RuntimeCase:
    case_id: str
    method: str
    profile: StudentProfile
    expected_record_ids: tuple[str, ...] = ()
    unknown_codes: tuple[str, ...] = ()
    guard: bool = False
    refresh_sources: bool = False
    final_demo: bool = False


def final_demo_case(catalog, with_sources=False):
    course = code_lookup(catalog)[DEMO_COURSE]
    profile = StudentProfile(catalog_version=catalog.catalog_version,
                             programming_background="experienced", question=DEMO_QUESTION)
    return RuntimeCase("final_demo", "hybrid", profile, (course.record_id,), (DEMO_COURSE,),
                       refresh_sources=with_sources, final_demo=True)


def _final_demo_lesson(catalog):
    index = build_lab_index(catalog.model_dump_json())
    before = run_experiment(index, PRESETS[DEMO_PRESET], "semantic")
    after = run_experiment(index, DEMO_QUESTION, "semantic")
    course = code_lookup(catalog)[DEMO_COURSE]
    ranks = next(row for row in compare_ranks(before, after) if row["Record"] == course.record_id)
    return {
        "preset": DEMO_PRESET, "preset_question": before.query, "question": after.query,
        "method": after.method, "record_id": course.record_id,
        "preset_rank": ranks["Preset rank"], "variation_rank": ranks["Your rank"],
        "record_ids": [doc.record_id for doc in index.retriever.evidence],
    }


def _final_demo_checks(lesson, result, interim, case):
    comparison = advisor_embedding_comparison(result)
    rank = lesson["variation_rank"]
    expected_records = set(lesson["record_ids"])
    early_statuses = [plan.trace["source_refresh"].get("reason") for plan in interim]
    expected_statuses = ["pending", None] if case.refresh_sources else ["disabled"]
    return {
        "lesson_rank_change": lesson["preset_rank"] is None and rank is not None and rank <= 3,
        "shared_overviews": (
            comparison is not None and comparison["question"] == DEMO_QUESTION
            and len(expected_records) == len(RECORDS)
            and len(comparison["rows"]) == len(expected_records)
            and {row["Record ID"] for row in comparison["rows"]} == expected_records
        ),
        "usable_interim_plans": (
            early_statuses == expected_statuses
            and all(set(case.expected_record_ids) <= set(plan.context.allowed_record_ids) for plan in interim)
        ),
    }, {"lesson": lesson, "embedding_comparison": comparison}


def runtime_cases(with_sources=False):
    def course(code): return "uofa:" + code + ":2026-2027"
    cases = [
        RuntimeCase("coverage_guard", "hybrid", StudentProfile(question="marine biology dolphin migration"),
                    guard=True, refresh_sources=with_sources),
        RuntimeCase("ai_keyword", "keyword", StudentProfile(question="How should I begin programming with ECE101?"),
                    (course("ECE101"),), ("ECE101",)),
        RuntimeCase("ai_semantic", "semantic", StudentProfile(programming_background="experienced",
                    question="How can I compare programming languages in CSC372?"), (course("CSC372"),), ("CSC372",)),
        RuntimeCase("embedded_hybrid", "hybrid", StudentProfile(career_id="embedded", programming_background="experienced",
                    question="How can I study electromagnetic fields in ECE381A?"), (course("ECE381A"),), ("ECE381A",)),
        RuntimeCase("resource_comparison", "hybrid", StudentProfile(programming_background="experienced",
                    question="Compare MIT 6.006 and MIT 6.004 as learning resources."),
                    ("resource:mit_algorithms", "resource:mit_structures")),
        RuntimeCase("completed_course", "hybrid", StudentProfile(career_id="embedded", programming_background="experienced",
                    question="How does ECE372A help me learn microcontrollers?", completed=[Completion(course_code="ECE101", grade="B")]),
                    (course("ECE372A"),), ("ECE372A",)),
    ]
    if with_sources:
        cases.append(RuntimeCase("source_checked", "hybrid", StudentProfile(career_id="embedded", programming_background="experienced",
                     question="How can ECE352 and MIT 6.004 help me study hardware?"),
                     (course("ECE352"), "resource:mit_structures"), ("ECE352",), refresh_sources=True))
    return cases


def _safe_error(error, operation):
    """Keep only operation, exception class, and numeric status; never messages."""
    status, name, seen = None, "provider_error", set()
    for _ in range(5):
        if error is None or id(error) in seen:
            break
        seen.add(id(error))
        candidate = type(error).__name__
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,79}", candidate):
            name = candidate
        code = getattr(error, "code", None)
        if type(code) is int and 100 <= code <= 599:
            status = code
        error = error.__cause__
    return {"operation": operation, "error_type": name, "http_status": status}


class _CountedProvider:
    def __init__(self, provider, counts, budget):
        self.provider, self.counts, self.budget = provider, counts, budget
        self.embedding_model = provider.embedding_model
        self.generation_model = provider.generation_model
        self.dimensions = provider.dimensions

    def _call(self, operation, value, method):
        if self.counts["errors"]:
            self.counts["blocked_calls"][operation] += 1
            raise ProviderError("Verification stopped after an earlier provider failure.")
        if self.counts[operation] >= getattr(self.budget, operation):
            self.counts["blocked_calls"][operation] += 1
            self.counts["errors"].append({"operation": operation, "error_type": "call_budget", "http_status": None})
            raise ProviderError("The verification call budget was reached.")
        self.counts[operation] += 1
        try:
            return method(value)
        except Exception as error:
            self.counts["errors"].append(_safe_error(error, operation))
            raise ProviderError("Verification provider operation failed.") from None

    def embed_document(self, chunk):
        return self._call("document_embeddings", chunk, self.provider.embed_document)

    def embed_query(self, query):
        return self._call("query_embeddings", query, self.provider.embed_query)

    def generate(self, context):
        return self._call("generations", context, self.provider.generate)

    def set_request_budget(self, budget):
        configure = getattr(self.provider, "set_request_budget", None)
        if callable(configure):
            configure(budget)

    def close(self):
        try:
            self.provider.close()
            self.counts["providers_closed"] += 1
        except Exception as error:
            self.counts["errors"].append(_safe_error(error, "close"))
            raise ProviderError("Verification provider close failed.") from None


def verify_runtime(catalog, api_key, *, embedding_model="gemini-embedding-2", generation_model="gemini-3.5-flash-lite",
                   dimensions=768, cache_dir=Path(".cache/embeddings"), source_cache_dir=Path(".cache/sources"),
                   with_sources=False, provider_factory=None, source_refresher=None, budget=None, cases=None, progress=None,
                   ai_time_budget_seconds=45):
    """Make opt-in integration requests; never interpret these as quality grades."""
    budget = CallBudget() if budget is None else budget
    cases = list(runtime_cases(with_sources) if cases is None else cases)
    ids = {record.record_id for record in catalog.records}
    if (not isinstance(api_key, str) or not api_key or type(with_sources) is not bool
            or not isinstance(budget, CallBudget) or not 1 <= len(cases) <= 8
            or type(ai_time_budget_seconds) is not int or not 5 <= ai_time_budget_seconds <= 120
            or any(not isinstance(case, RuntimeCase) for case in cases)
            or len({case.case_id for case in cases}) != len(cases)
            or any(case.method not in {"keyword", "semantic", "hybrid"} or not set(case.expected_record_ids) <= ids
                   or (case.refresh_sources and not with_sources) for case in cases)):
        raise ValueError("Verification cases, credential, or budget are invalid")
    counts = {name: 0 for name in ("document_embeddings", "query_embeddings", "generations", "providers_started", "providers_closed")}
    counts.update(errors=[], blocked_calls={name: 0 for name in asdict(budget)})

    def factory(*args, **kwargs):
        try:
            provider = (provider_factory or GeminiProvider)(*args, **kwargs)
            counted = _CountedProvider(provider, counts, budget)
            counts["providers_started"] += 1
            return counted
        except Exception as error:
            counts["errors"].append(_safe_error(error, "initialization"))
            raise ProviderError("Verification provider initialization failed.") from None

    demo_lesson = _final_demo_lesson(catalog) if any(case.final_demo for case in cases) else None
    rows = []
    for case in cases:
        if counts["errors"]:
            rows.append({"case_id": case.case_id, "status": "not_run", "reason": "earlier_provider_failure"})
            continue
        before = {key: counts[key] for key in asdict(budget)}
        providers_before = counts["providers_started"]
        try:
            interim = []
            result = run_advisor(catalog, case.profile, api_key=api_key, use_ai=True, method=case.method,
                embedding_model=embedding_model, generation_model=generation_model, dimensions=dimensions,
                cache_dir=cache_dir, source_cache_dir=source_cache_dir, provider_factory=factory,
                refresh_sources=case.refresh_sources, source_refresher=source_refresher,
                ai_time_budget_seconds=ai_time_budget_seconds, source_reuse_seconds=0,
                on_plan=interim.append if case.final_demo else None)
            delta = {key: counts[key] - before[key] for key in before}
            selected = [item.record_id for item in result.answer.recommendations] if result.answer else []
            checks = result.trace.get("source_refresh", {}).get("checks", [])
            attempted = [check for check in checks if check.get("attempts")]
            if case.guard:
                expectations = {"coverage_guard": bool(result.coverage_notice) and result.generation_status == "insufficient_evidence",
                                "no_model_calls": not any(delta.values()),
                                "no_provider_initialization": counts["providers_started"] == providers_before,
                                "no_source_calls": not attempted and not result.trace.get("source_refresh", {}).get("enabled", False)}
            else:
                completed = {record.record_id for record in catalog.records if record.code in {c.course_code for c in case.profile.completed}}
                unknown = {"uofa:" + code + ":" + catalog.catalog_version for code in case.unknown_codes}
                expectations = {"answered": result.generation_complete, "requested_retrieval": result.retrieval_mode == case.method,
                    "statement_contract": result.statement_validation_passed is True,
                    "focus_selected": set(case.expected_record_ids) <= set(selected),
                    "completed_not_recommended": not completed.intersection(selected + result.context.allowed_record_ids),
                    "academic_unknowns_preserved": all(rid in result.context.rule_results and result.context.rule_results[rid].status == "unknown" for rid in unknown)}
                if case.refresh_sources:
                    if case.final_demo:
                        expectations["demo_course_source_verified"] = any(
                            check["kind"] == "course" and check["code"] == DEMO_COURSE
                            and check["status"] in REFRESHED_SOURCES for check in attempted)
                    else:
                        expectations["selected_sources_verified"] = bool(attempted) and all(
                            check["status"] in REFRESHED_SOURCES and check.get("rule_status") in {None, "verified"}
                            and check.get("discovery_status") in {None, "verified"} for check in attempted)
                    expectations["source_limits"] = (sum(c["kind"] == "course" for c in attempted) <= 8
                        and sum(c["kind"] in {"rule", "discovery"} for c in attempted) <= 2
                        and sum(c["kind"] == "resource" for c in attempted) <= 2)
            demo = {}
            if case.final_demo:
                checks, demo = _final_demo_checks(demo_lesson, result, interim, case)
                expectations.update(checks)
            rows.append({"case_id": case.case_id, "status": "passed" if all(expectations.values()) and not counts["errors"] else "failed",
                "requested_retrieval": case.method, "expectations": expectations, "expected_record_ids": case.expected_record_ids,
                "call_counts": delta, "context": result.context.model_dump(mode="json"),
                "answer": result.answer.model_dump(mode="json") if result.answer else None,
                "trace": result.trace, "issues": result.issues, **demo})
        except Exception as error:
            counts["errors"].append(_safe_error(error, "verification"))
            rows.append({"case_id": case.case_id, "status": "failed", "error": _safe_error(error, "verification")})
        if progress:
            progress({"case_id": case.case_id, "status": rows[-1]["status"]})
    return {"schema_version": 1, "checked_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Assistant-authored integration scenarios, not relevance judgments, general answer accuracy, or complete enrollment approval.",
        "data_version": catalog.version, "catalog_snapshot_hash": catalog_snapshot_hash(catalog), "corpus_hash": corpus_hash(catalog),
        "catalog": {"courses": sum(r.kind == "course" for r in catalog.records), "resources": sum(r.kind == "resource" for r in catalog.records), "chunks": len(build_evidence(catalog))},
        "requested_provider": {"embedding_model": embedding_model, "generation_model": generation_model, "dimensions": dimensions},
        "source_case_requested": with_sources, "ai_time_budget_seconds": ai_time_budget_seconds,
        "call_budget": asdict(budget), "call_counts": counts,
        "cases": rows, "all_checks_passed": all(row["status"] == "passed" for row in rows),
        "manual_source_review_required": True, "provider_provenance": "operator_supplied_unverified",
        "limitations": "Counts are adapter attempts, not billed costs. Saved-case sources are snapshots. Source observations and latency are dated; independent grading and provider provenance are not authenticated."}
