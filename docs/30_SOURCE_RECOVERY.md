# Bounded public-source recovery

Implemented and verified November 5, 2026. Course, program, and learning-resource GET checks now share a bounded recovery layer. A transient failure can receive one retry; the trace keeps the first outcome even when the second attempt succeeds. This improves recovery for intermittent failures without interpreting unknown prerequisites or treating an unsuccessful check as current.

## Retry policy

| Condition | Action |
| --- | --- |
| Connect/read/write errors or timeouts; remote protocol errors | Retry once if the elapsed/size guards permit |
| HTTP 502, 503, or 504 without `Retry-After` | Retry once if the guards permit |
| A selected server-error response containing `Retry-After` | No automatic retry or wait; return the existing labeled fallback |
| HTTP 429, other unselected responses, pool timeout, proxy error, local protocol error | No retry |
| Unsupported content type, invalid UTF-8, oversize content, parser/identity/edition failure | No retry |
| Redirect | Existing adapter rules apply; only the existing single approved CS50 hop is supported |

There is a 0.25-second pause before the retry. Failed responses close first. Both attempts use the same public GET URL and conditional request headers. A partial document is discarded; a retry starts a new response and cannot combine old and new text. The one-retry allowance is shared across a resource's canonical URL and its approved redirect, so it cannot reset after a hop.

The existing logical limits remain eight course checks, two program sources, two resources, three new discoveries, and three workers. Those are **source counts, not wire-attempt counts**. A course, program, or PyTorch job can use up to two HTTP attempts. CS50 can use up to three when one approved redirect and one retry are involved. Unsupported redirect destinations, additional hops, and URLs inferred from user text remain prohibited.

This layer applies only to configured public academic/resource GETs. Model calls, opportunity providers, credentials, and their quota behavior are unchanged. No new dependency, database, scheduled task, or background request is introduced.

## Elapsed and size guards

Each source job shares a 12-second elapsed guard and a 3 MB decoded-size guard across attempts and the allowed redirect. Retry eligibility requires enough remaining time for the pause. New attempts, received headers, and body chunks check the guard; a late response is rejected. HTTPX phase timeouts retain their existing maxima of four seconds for connect/pool and six seconds for read/write, clipped to the remaining guard when an attempt begins.

This is a **cooperative elapsed guard**, not hard cancellation of synchronous I/O or a guaranteed 12-second total for the submitted roadmap. HTTPX timeouts apply to individual blocking phases, and queued source work is separate. The [official timeout documentation](https://www.python-httpx.org/advanced/timeouts/) explains that distinction. The [transport documentation](https://www.python-httpx.org/advanced/transports/) describes HTTPX's built-in connect retries; this application layer also handles the explicitly selected read/write/server cases without enabling retries on model transports.

Decoded bytes from failed partial reads count toward the same size guard. Advertised lengths larger than the remaining allowance, negative/invalid lengths, and decoded chunks exceeding the guard stop the check. Only the final complete response proceeds to normal document parsing and cache writes.

## Freshness and diagnostics

Every `SourceCheck` now carries:

| Field | Meaning |
| --- | --- |
| `attempts` | Ordered transport outcomes, response statuses when received, elapsed seconds, and whether the attempt was a retry |
| `retry_count` | Number of retry attempts actually started, zero or one |
| `transport_seconds` | Time from the first attempt through the final transport outcome, including any retry pause |

An HTTP transport success does not establish source identity or academic correctness. Existing parsers, catalog editions, course-code bindings, requirement fingerprints, and cache identities still have to pass. A repeated failure retains stale/bundled evidence with the last successful timestamps. Changed or unavailable prerequisite evidence still cannot approve a condition. A recovered 304 needs a matching validated cache and advances the check date while preserving the original content-download date.

The inspector summarizes how many source checks retried and recovered, with attempt details in the request trace. The source-check CLI prints attempt/retry counts alongside final statuses. Raw exception messages, headers, response bodies, and credentials are absent from attempt metadata. Widget rerenders do not initiate another request. Source cache schemas are unchanged; attempt histories belong to request traces rather than cached content.

## Verification

The complete suite passes **942 tests**, including **52 transport/recovery cases** and **43 Streamlit interactions**. Checks cover retryable and nonretryable failures, cooldown headers, response closure, partial-body disposal, cumulative size, elapsed expiry and timeout clipping, conditional cache reuse, changed rule statements, shared redirect/retry allowances, unsafe redirects, redacted diagnostics, and interface rerenders. Discovery-budget tests distinguish six distinct course URLs from a permitted repeat of the failed target; no substitute course is fetched.

The [November 5 evidence](evidence/source_recovery_2026-11-05.json) retains two actual public-source requests under the new policy:

- A normal AI/ML roadmap request checked ten sources using fourteen HTTP attempts. COSCBS, ECEBSECE, ECE101, and PyTorch each timed out once, then succeeded on their single retry. All ten final source/rule/discovery checks passed; ECE310/ECE320A/ECE373 were added in the requested phrase order.
- A separate source-only request with a controlled completed-foundation history passed all seven checks on their first attempts. It skipped ECE201/ECE220/ECE274A and discovered ECE310/ECE311/ECE320A, with intermediate preparation stages and unknown academic conditions. This verifies that routing for the recorded test history and source snapshot, not an authenticated transcript or enrollment decision.

The first run took about 18.2 seconds and the second about 6.6 seconds in this environment. These are single observations, not an uptime or latency benchmark. They demonstrate recovery in those requests; they do not establish the cause of earlier failures or guarantee future connectivity. The [earlier failed completion/resource observations](29_ECE_CORE_COVERAGE.md) and their evidence remain unchanged.

All eight production-environment local readiness checks also passed, including real loopback server health and the offline roadmap preview. No source or model requests occur in that readiness smoke test. Neither live source request used credentials, embeddings, or generation. Frozen evaluation inputs, earlier metrics, and submitted midproject artifacts remain unchanged.

Use the existing commands in PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts/check_sources.py --career ai_ml --question "eigenvalues, circuit theory, and class hierarchies"
.\.venv\Scripts\python.exe scripts/check_deployment.py --smoke
```

The source command still exits unsuccessfully if a requested source or its bound interpretation cannot be verified after the permitted recovery. Exact ECE prerequisite/edition evidence, independent reviewer judgments, broader source coverage, and public hosting remain open.
