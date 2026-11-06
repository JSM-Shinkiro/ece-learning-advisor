# Bounded opportunity request recovery

Implemented and verified November 6, 2026 (MST). Public employer metadata and selected-posting checks now use the shared bounded transport. This follows the all-source timeouts recorded in the paging unit; those earlier observations remain unchanged.

## Request policy

Each configured public source gets at most two GET attempts. The same endpoint and headers are used on retry, without credentials, profile/search text, redirects, or provider fallback. A successful metadata search still needs valid employer/posting records; a successful detail check still needs the exact selected identity and visible description. Fresh search/detail actions remain explicit. Widget rerenders, page navigation, and explicit matching-result reuse make no new requests.

| Failure | Behavior |
| --- | --- |
| Connect/read/write timeout or error; remote protocol error | One retry if time and decoded-byte budget remain |
| HTTP 502/503/504 without Retry-After | One retry within the same guards |
| HTTP 429, any Retry-After response, other HTTP errors, redirects | Stop; do not follow or repeat |
| Pool timeout, proxy error, local protocol error | Stop |
| Invalid media, encoding, JSON, identity, source link, or description | Stop; no content-validation retry |
| Exhausted time/download guard or second failed attempt | Stop; retain safe failure history |

The retry delay is 0.25 seconds. Both attempts share the existing **12-second cooperative elapsed guard** and **3 MB decoded-byte limit per source**. The existing phase limits remain 6 seconds read/write and 4 seconds connect/pool, clipped at attempt start to the remaining elapsed guard. A failed partial body is discarded; its bytes remain charged to the shared limit. This is not a hard cancellation deadline for synchronous I/O or the whole search. HTTPX documents [phase timeouts](https://www.python-httpx.org/advanced/timeouts/); its [built-in transport retries](https://www.python-httpx.org/advanced/transports/) cover connection failures. The application's shared loop implements the additional bounded read/write/status policy.

There are still three configured boards and at most three workers. One search can therefore make up to six board GET attempts. A separately selected posting can make up to two detail attempts. No background job, content database, timeout widening, model call, or automatic provider substitution is added. A persistent content database, if introduced later, still requires scheduled refresh alongside on-use checks.

## Transport and content are separate

`src/source_http.py` now supplies `read_public_json` alongside the existing HTML reader. JSON requires HTTP 200 and an exact application/json media type, allowing parameters such as charset. HTTP 304 is rejected for these unconditional JSON requests. Duplicate keys and nonstandard NaN/Infinity tokens are rejected. JSON parsing and employer/posting validation occur outside the transport retry loop. Consequently, a transport attempt may succeed with HTTP 200 while the source check remains unavailable because its content is invalid.

The shared reader also checks elapsed time after an empty stream ends. A controlled test caught this missing boundary during implementation; the fix applies to both HTML and JSON. Existing academic conditional requests and approved resource redirects retain their behavior. Academic rule interpretations, frozen corpus/evaluation inputs, and model settings are unchanged.

Board and posting checks expose `attempts`, `retry_count`, and `transport_seconds`. Each attempt records only outcome, HTTP status when known, duration, and whether it was the retry. No raw exceptions, bodies, credentials, request headers, addresses, or redirected targets enter those records. The interface displays board attempt rows in source checks and a separate posting-attempt table. A failed check still has no successful check time or old description.

## Verification

The full suite passes **1,136 tests**, including **42 new recovery cases**, the existing 52 academic transport cases, and **61 Streamlit interactions** (two added here). Controlled checks cover retryable failures/statuses, no third attempt, Retry-After/rate-limit handling, pool/proxy/local errors, partial/compressed body limits, shrinking phase timeouts, late empty streams, strict JSON, post-validation failures, safe diagnostics, and UI rerender boundaries. Earlier posting tests now expect two attempts for eligible transport failures; their nonretryable cases remain single attempts. All eight production-runtime checks pass, including loopback liveness and the offline preview.

The [November 6 evidence](evidence/opportunity_recovery_2026-11-06.json) separates these actual observations:

| Observation | Result |
| --- | --- |
| Single Samsara probe before the transport change | Passed under unchanged limits; 305 raw records; roughly 5.15 seconds waiting for proxy response headers before TLS setup |
| Current embedded all-level search | Three boards verified: 305 Samsara, 94 Nuro, and 2,593 Anduril records; no rejected records |
| Matching/retained results | 262 matches; first 200 retained across 20 pages with the cap visibly represented |
| Local traversal | Exact retained order, no duplicates, unchanged retrieval times, and no additional HTTP requests |
| Page-two posting | Anduril posting `4797357007` verified; 7,047 extracted characters; no shortening or metadata change |
| Explicit matching-result reuse | Reused the original timestamp, reset to page one, cleared checked details, and made no source request |

The current integration check made three metadata GETs and one selected-detail GET. **Every live attempt succeeded first time.** Retry behavior is verified with controlled failures, not a spontaneous live recovery. The pre-change successful probe and later successful search show that connectivity varied; they do not prove the retry caused success, identify a root cause, or establish permanent availability. No credentials, embedding calls, or generation calls were used. Full descriptions are omitted from the evidence; lengths and hashes are retained.

This verifies the previously blocked paging/detail path for the later snapshot. Earlier failures are preserved, and wider employer/provider coverage, geography-aware search, independent student judgments, and public hosting remain open.

Reproduce the explicit public check in PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts/check_opportunities.py --career embedded --page 2 --check-first-detail
```

Each invocation starts a new search. Inspect its source and posting-attempt records alongside the overall outcome; a retry or HTTP 200 alone is not proof of valid content or qualification fit.
