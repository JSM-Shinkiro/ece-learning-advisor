# Request progress and phase timings

Implemented November 7, 2026. Submitted roadmaps now show the work being attempted: checking the learning goal, checking official sources or using snapshots, preparing source search, finding options, checking recorded preparation, and preparing/validating AI explanations when requested. The completed status can be expanded to read the stage history. Unsupported requests and model abstention finish with “More detail needed”; a failed request has an error status.

## Behavior and boundaries

`run_advisor(..., progress=callback)` accepts an optional callback receiving a fixed phase ID and label. Each request owns a new `RequestProgress`; no callback, profile, timeline or answer is stored globally. Phase changes happen on the request thread. Source-download workers and shared embedding-cache builders do not call Streamlit UI methods.

Preview requests report snapshot/source search and preparation work without claiming AI generation. Keyword AI skips the embedding stage. A failed embedding can still lead to keyword ranking and generation when the existing budget allows it. Budget expiry skips later AI stages; a generation failure does not claim validation happened. Existing warnings and source-based fallbacks remain visible. “Learning plan ready” describes the returned learning suggestions, not academic enrollment approval or guaranteed AI success.

The observer receives no user-entered text, source content, URLs, credentials or model output. An ordinary callback exception disables that observer and sets `observer_failed=true` in the report; it cannot fail an otherwise successful request or retry provider/source work. Framework control-flow exceptions still propagate normally. A slow callback consumes server time and is not isolated in a background thread. Existing provider timeouts and the shared AI budget retain their scope.

The UI uses the installed Streamlit 1.66.1 status API with explicit completion/error updates. The [official API documentation](https://docs.streamlit.io/develop/api-reference/status/st.status) describes the expandable status container and its update method. Pinned production dependencies are unchanged.

## Trace and inspector

Request traces add `request_phases`, version `p07-request-phases-v1`, containing each attempted phase's fixed label, start offset and duration, the total observed duration, and the observer-failure flag. Snapshots are independent copies. The inspector displays a stage-duration table, and the existing trace download includes it.

Phase durations are sequential server intervals through result assembly, before provider cleanup and browser rendering. They include callback work. They are separate from the older timing categories: do not add the phase table to embedding/retrieval/generation/source totals. This is neither a fake completion percentage nor a hard deadline for the whole browser interaction. The existing AI budget still starts after source checking.

## Verification

All **1,539 local tests** pass, including 15 new cases: eleven backend cases and four Streamlit interactions. There are now 77 Streamlit interactions overall. All nine local readiness checks and dependency consistency pass. New controls cover actual-call ordering, skipped AI phases, source failure, budget fallback, generation failure/abstention, observer failures, sanitized reports, independent concurrent requests, measured callback time, immutable snapshots, and UI completion/clarification/error states.

The real-browser check adds a ninth gate: the completed preview status is visible and can be expanded to read the snapshot stage without claiming AI explanations. Linux/Windows backend and Linux Chromium CI verification will be recorded after the actual run.

A real source-only embedded-profile probe makes two submitted requests with the same synthetic question and a temporary source cache:

| Observation | Backend wall time | Selected checks | Budget omissions |
| --- | --- | --- | --- |
| Fresh source cache | 13.924 s | 11 updated | 10 skipped |
| Reused source cache | 10.693 s | Nine unchanged, two HTTP 304/not-modified | 10 skipped |

Both observe `request → sources → ranking → requirements`. No AI provider or AI budget is initialized. The returned ECE101/ECE369A/ECE372A academic states remain unknown. These two observations include public-network variability and conditional source requests; they do not establish a speedup, final latency distribution, AI responsiveness, or independent answer quality. The source cache is reused, not used to bypass on-use checks.

[Dated evidence](evidence/request_progress_2026-11-07.json) retains local results, the real-source observations, and the eight unchanged frozen/review input hashes. All 408 independent review grades remain blank. App/submission readiness remains approximately 90%/70%; final evaluation, a voluntary pilot, final-revision performance measurements and the presentation package remain open.
