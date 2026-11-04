"""One submitted provider request with a current-profile fallback."""
from pathlib import Path
import time

import httpx

from .planning import coverage_message
from .providers import GeminiProvider, ProviderError
from .service import recommend
from .sources import refresh_catalog
from .discovery import load_discovery_plans


def run_advisor(catalog, profile, *, api_key="", use_ai=False, method="hybrid",
                embedding_model="gemini-embedding-2", generation_model="gemini-3.5-flash-lite",
                dimensions=768, cache_dir=Path(".cache/embeddings"), provider_factory=None,
                refresh_sources=True, source_cache_dir=Path(".cache/sources"), source_refresher=None):
    started = time.perf_counter()
    source_trace = {"enabled": False, "reason": "disabled"}
    source_issues, source_elapsed = [], 0.0
    if refresh_sources and not coverage_message(catalog, profile, profile.question, allow_course_discovery=True):
        before = time.perf_counter()
        try:
            if source_refresher is not None:
                refreshed = source_refresher(catalog, profile, cache_dir=source_cache_dir)
            else:
                refreshed = refresh_catalog(catalog, profile, cache_dir=source_cache_dir,
                                            discovery_plans=load_discovery_plans(), resource_checks=True)
            catalog = refreshed.catalog
            source_trace, source_issues = refreshed.trace(), refreshed.issues
        except (httpx.HTTPError, OSError, ValueError):
            catalog = catalog.model_copy(deep=True)
            for source in catalog.sources:
                if source.source_id.startswith(("catalog:", "resource:")):
                    source.verification_status = "stale"
            for record in catalog.records:
                if record.rule_reviewed or record.rule_evidence:
                    record.rule_verification = "unavailable"
            source_trace = {"enabled": True, "error": "unavailable", "checks": []}
            source_issues = ["Official-source checks are unavailable. Showing dated saved evidence."]
        source_elapsed = time.perf_counter() - before
    elif refresh_sources:
        source_trace = {"enabled": False, "reason": "outside_supported_collection"}
    else:
        catalog = catalog.model_copy(deep=True)
        for source in catalog.sources:
            source.verification_status = "snapshot"
        for record in catalog.records:
            if record.rule_verification == "verified":
                record.rule_verification = "snapshot"
            for proof in record.rule_evidence:
                if proof.verification_status == "verified":
                    proof.verification_status = "snapshot"
        source_issues = ["Official-source checks are disabled. Showing dated saved evidence."]
    provider, issue = None, None
    if use_ai and api_key:
        try:
            provider = (provider_factory or GeminiProvider)(api_key, embedding_model=embedding_model,
                generation_model=generation_model, dimensions=dimensions)
        except (ProviderError, ImportError, ValueError):
            issue = "AI could not start. This updated plan uses the available source information."
    try:
        result = recommend(catalog, profile, provider=provider,
                           method=method if provider else "keyword", cache_dir=cache_dir)
        if issue:
            result.issues.append(issue)
        result.issues.extend(source_issues)
        result.timings = {"source_refresh": source_elapsed, **result.timings}
        result.timings["total"] = time.perf_counter() - started
        result.trace["source_refresh"] = source_trace
        result.trace["timings_seconds"] = result.timings
        return result
    finally:
        if provider is not None:
            provider.close()
