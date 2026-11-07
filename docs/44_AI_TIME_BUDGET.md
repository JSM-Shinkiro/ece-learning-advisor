# Shared AI time budget

Implemented November 7, 2026 MST. Submitted roadmap requests now share one AI-phase time budget across document embeddings, query embedding, cache coordination, generation, and final answer validation. Previously, separate per-call timeouts could accumulate across the 34-chunk runtime collection. Source checking still runs first and has its own existing limits.

## Request behavior

The default budget is **45 seconds**, starting after official-source checking and before provider initialization. A host can set `AI_TIME_BUDGET_SECONDS` to an integer from **5 through 120**. Invalid settings stop startup with a sanitized message naming the variable. The app and opt-in runtime verifier use the same configured value. Preview and unsupported requests do not initialize an AI budget or provider.

The Gemini adapter limits each embedding request to the smaller of 30 seconds and the remaining allowance, expressed in milliseconds for `EmbedContentConfig.http_options`. Generation uses the same remaining allowance in the SDK's seconds-based `timeout` parameter. The existing one-attempt retry configuration, statement-selection schema, output limit, and `store=False` remain in place. The installed Google GenAI 2.33.0 adapter is checked through an HTTPX mock transport so the actual request timeouts, rather than just constructed arguments, are exercised.

The budget also caps cache-lock waits. A request checks its allowance before and after model operations, after acquiring locks, and before publishing the validated explanation. Expiry stops later provider calls and rejects late selections. In particular, an expired embedding phase cannot trigger another generation request through the ordinary keyword fallback.

The app then shows the current source-based roadmap with **“AI time limit reached. Showing the updated plan from available sources.”** The trace records `generation_status: time_budget_exceeded` and an `ai_budget` object containing the limit, elapsed time, exhausted status, and phase scope. A timeout does not falsely report a citation or format-validation failure. Source provenance, academic conditions, current/completed coursework, and the submitted profile remain available. The inspector shows AI time separately from source-check time.

Ordinary embedding failures can still use keyword retrieval and generation when time remains. A new submission gets its own budget. Valid public document vectors completed before expiry remain reusable; partial indexes and late vectors are not accepted as complete indexes. Provider cleanup and lock release run on both successful and expired paths. Time budgets and student state are not added to public cache manifests.

## Scope of the limit

This is a cooperative application deadline with shorter SDK transport timeouts. It does not forcibly terminate threads or promise that the entire browser interaction returns within exactly 45 seconds. Source downloads, browser rendering, cleanup, operating-system scheduling/DNS, and transport timeout behavior can extend wall time. A synchronous call that returns late is rejected before another model call or explanation publication. No background inference worker is left running by an application timeout wrapper.

Direct historical verification and index-building utilities retain their separately documented behavior; the shared allowance applies to `run_advisor` and the current runtime verifier. Independent source/embedding identity, cache formats, question expansion, retrieval scoring, and academic interpretations are unchanged.

## Verification

The local Python 3.12.14 suite passes **1,511 tests**, including **38 new cases**: 34 backend cases and four Streamlit interactions. There are now **73 Streamlit interactions overall**. Existing shared-cache concurrency, provider verification, source handling, and current-coursework checks also pass.

New controls cover cold/partial caches, warm query expiry, late generation and validation, capped cache waits and released locks, independent request recovery, ordinary-error fallback, source work preceding the budget, skipped preview/coverage requests, provider cleanup, host validation, CLI propagation, SDK timeout units, actual mock-transport timeout settings, and visible timeout/recovery behavior in the app. No real model calls or credentials were used in this unit.

[Dated evidence](evidence/ai_time_budget_2026-11-07.json) includes a standalone controller probe with HTTP clients blocked and model durations simulated by an injected clock:

| Controlled case | Document / query / generation calls | Outcome |
| --- | --- | --- |
| Previous behavior, cold 34-chunk collection | 34 / 1 / 1 | Completed after 36 simulated model seconds; no shared deadline |
| New cold request, five-second allowance | 5 / 0 / 0 | Expired at the fifth simulated second; four completed public vectors retained |
| New request with a fresh 45-second allowance | 30 / 1 / 1 | Reused those four vectors; completed in 32 simulated model seconds |
| Warm request, five-second allowance | 0 / 1 / 1 | Completed in two simulated model seconds |
| Warm query returning after its allowance | 0 / 1 / 0 | Source roadmap retained; no generation started |
| Keyword generation returning late | 0 / 0 / 1 | Selection rejected; source roadmap retained |

These are controlled deadline/call-reuse observations, not measured Gemini latency, a speedup benchmark, billed savings, or independent answer-quality results. The SDK transport control observes four-second embedding and three-second generation timeouts, with no actual network requests. The existing real-provider timings retain their original dates and scope.

## Configuration and reproduction

```text
AI_TIME_BUDGET_SECONDS=45
```

```bash
python -m pytest -q tests/test_ai_budget.py tests/test_ai_budget_app.py
python scripts/check_deployment.py --smoke
```

Runtime verification still requires explicit `--live-models` opt-in and configured credentials. It records `ai_time_budget_seconds` and each request's budget trace, separately from its existing call-count limits. Use the hosted workflow for Linux/Windows results at the implementation revision.

Relevant primary references: the [Google GenAI SDK](https://googleapis.github.io/python-genai/) and [Interactions request interface](https://github.com/googleapis/python-genai/blob/main/google/genai/_gaos/interactions.py). This implementation also inspects and tests the locally installed pinned SDK; documentation transport failure was not treated as a live model result.

Exact ECE/edition evidence, genuine independent grades, remote browser/WebSocket validation, public hosting, and a student pilot remain open. Frozen inputs, prepared blank reviewer forms, historical evidence, and midproject artifacts remain preserved.
