# Expanded runtime provider verification

Implemented and observed November 6, 2026 MST. UTC timestamps cross into November 7. The app still has twenty courses, eight resources, and 34 saved evidence chunks. The submitted midproject snapshot, frozen benchmark, prepared reviewer bundle, academic interpretations, and application fallback behavior remain unchanged.

The new `scripts/verify_runtime.py` runs authored integration scenarios through the same `run_advisor` controller as the app. It verifies requested retrieval modes, application-owned statement selections, question focus, completed-course filtering, unknown academic conditions, and optionally a current source overlay. `verify_live.py` retains its original smaller collection and measurements.

## Run locally

Configure the existing Gemini environment settings, then choose a new report path:

```powershell
.\.venv\Scripts\python.exe scripts/verify_runtime.py --live-models --output .cache/runtime_provider_check.json
.\.venv\Scripts\python.exe scripts/verify_runtime.py --live-models --with-sources --output .cache/runtime_provider_sources.json
```

`--live-models` is required before configuration or credential reads. These requests use real provider quota. `--with-sources` adds one source-refresh scenario; the other supported cases use saved snapshots. Cache locations and model IDs use the same validated settings as the app. Existing report paths are rejected before provider use, and writable output is reserved before spending quota. Exit 0 means every requested scenario passed, 1 retains a report with failed/not-run checks, and 2 indicates opt-in, configuration, or output problems.

Each run caps adapter attempts at **64 document embeddings, eight query embeddings, and eight generations**. Library callers may reduce these limits; they cannot increase them. A provider/initialization/close failure stops later scenarios. A failed embedding also blocks the same case's generation fallback inside the verifier. The app's ordinary fallback remains unchanged. Error evidence includes only operation, exception class, and numeric HTTP status when available; raw exception text, headers, and credentials are excluded. Successful clients close through the controller.

The source scenario retains the existing eight-course/two-program/two-resource limits and three-worker pool. An unavailable source keeps its dated fallback and fails the verification's current-source expectation even if the model answers. Expected budget omissions remain snapshots. A model request that falls back to another retrieval method cannot pass its originally requested semantic/hybrid check.

## Real observations

Python 3.12.14, `google-genai==2.33.0`, `gemini-embedding-2`, 768 dimensions, `gemini-3.5-flash-lite`, and the existing statement-selection contract were used with an authorized credential supplied through hidden transient input. No credential was written to environment files, source files, or evidence. OpenRouter and opportunity providers were not used.

An initial single generation preflight selected ECE101 and CS50 and passed statement validation. The suite then verified these authored controls:

| Scenario | Observation | Cache | Seconds |
| --- | --- | --- | ---: |
| Unsupported marine-biology question | Coverage guard; no provider initialization, model calls, or source requests | Not used | 0.005 |
| ECE101 keyword question | ECE101 and CS50 selected; canonical statement selection passed | Not used | 6.895 |
| CSC372 semantic question | CSC372 selected; actual 34 × 768 index built | Miss | 13.094 |
| ECE381A hybrid question | ECE381A selected; canonical selection passed | Hit | 6.866 |
| MIT resource comparison, initial | Query embedding hit a ProxyError; generation was blocked and later scenarios were not run | Hit | 0.022 |
| MIT resource comparison, bounded follow-up | Both MIT 6.006 and 6.004 selected | Hit | 6.637 |
| ECE101 completed, ECE372A question, follow-up | ECE372A selected; completed ECE101 excluded from allowed recommendations | Hit | 4.188 |
| ECE352/MIT 6.004 with source checks, follow-up | Both selected; all eleven selected public-source checks passed | Refreshed index | 19.033 |

The initial suite remains unsuccessful in [the evidence](evidence/runtime_provider_2026-11-06.json). One bounded follow-up ran only the resource comparison and the two scenarios left unrun. It passed all three, using the existing cached document vectors. Every authored expectation was observed across the initial and follow-up runs; this does not relabel the first run as successful or establish a proxy root cause/reliability fix.

The source case checked eight course pages, one ECE program page, and two resource pages in eleven HTTP attempts, all successful first attempts. It embedded only ten changed evidence chunks, reusing the rest of the saved index. Its total time includes 10.390 seconds of source work, 6.829 of embeddings, and 1.804 of generation. Other records retained dated snapshots. ECE352 and other checked unresolved ECE conditions remained unknown. MIT's original teaching-term label remained separate from its current check date.

Across suite and follow-up there were 44 document-embedding, six query-embedding, and six generation attempts. One query attempt failed. The separate preflight adds one generation, making seven generation attempts overall. The verifier blocked one generation after the query failure; blocked calls were not sent to the adapter. These are request counts, not billed-cost figures. Report envelopes identify the initial saved catalog; each case records its actual context, source freshness, and trace, including a changed corpus hash for the fresh overlay.

Answers were materialized from the application-owned registry and passed its wording, ownership, citation, and context checks. This establishes the bounded output contract for these observations. It does not independently verify every source, unrestricted prose entailment, relevance quality, or complete enrollment eligibility. The unsupported case is an application guard, not measured model abstention. Times are single observations, not a performance benchmark.

## Automated and production checks

All **1,374 tests pass**, including thirty new runtime-verifier cases and the existing 62 Streamlit interactions. New tests cover all scenarios with controlled adapters, vector reuse, source limits/failures, no-call coverage guards, initialized/closed clients, quota bounds, failure stopping, blocked fallback calls, safe error metadata, irrelevant/invalid selections, opt-in, existing files, output errors, and persisted failed reports. Controls exercise the real controller and grounding code without public model calls.

All eight production-runtime readiness checks pass. A separate production-only CLI check, without pytest installed and with HTTP clients blocked, verifies explicit opt-in, successful saved-catalog export, existing-report preservation before quota, and retention of a sanitized failed-provider report. Those adapter calls are controlled fixtures and remain separate from the real observations above.

Independent judgments, held-out evaluation, wider source/edition evidence, a hosted pilot, and final-report updates remain open. The prepared 408 review grades stay blank. No new enrollment rule, relevance score, hallucination rate, or public-deployment claim is added by this verification step.
