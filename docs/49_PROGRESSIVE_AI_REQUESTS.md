# Usable plans while AI assistance runs

Team P07 · November 7, 2026 · ECE Learning Advisor

AI-enabled submissions now return control of the page while source checks and optional AI work run. Once the source checks finish, a keyword-based source plan appears. The student can read source links, mark successful course completion, edit/submit a new profile, or choose **Keep source plan** while the optional AI work continues.

The final validated AI result can refine rankings and add supported explanations. The early source plan is clearly labeled; it does not claim that AI has finished or that unresolved enrollment requirements are satisfied. With live source checks disabled, the existing dated-snapshot labels remain visible.

## Student behavior

| Situation | Result |
| --- | --- |
| AI is enabled and a submitted request starts | Source/AI work runs outside the UI thread; the page shows actual stage feedback |
| Selected source checks finish | The current profile gets an immediately usable source plan while AI continues |
| AI finishes successfully | Only the matching current request can replace that source plan with the validated result |
| A newer profile, restore, direction or completion replaces the request | The old job is cancelled and cannot apply a late result |
| Keep source plan | The source plan remains usable; further output from that AI request is discarded |
| Expected provider failure/time budget | Existing source-bound fallback and explanation-validation behavior still applies |
| Unexpected worker failure | A generic notice preserves an available early source plan; raw errors and credentials are not shown |
| Four background workflows are already running | No request queue is added; the app falls back to a source-only plan and suggests trying AI again on a later submission |

The no-AI preview path retains its existing submitted source-check behavior. Expensive source downloads can still take time before an AI request's early source plan appears. The earlier five-minute public-source reuse and explicit recheck action still apply.

## Ownership and cancellation

Each job belongs to one browser session and carries a unique request ID and a fingerprint of the submitted profile. The UI checks the current job identity and current profile before accepting a result. Workers never read or write Streamlit session state and never call Streamlit UI methods. Provider clients are created/closed on the worker path; keys are captured only by the running call and are excluded from job metadata, notices and progress labels.

Jobs are transient, in-process session state containing synchronization objects; they are not exported as profiles or durable across restarts. This uses Streamlit's default in-memory session-state mode rather than enforced serialization. A process-wide semaphore permits at most four active workflows. There is no global map of personal results and no unbounded queue. Source catalog and profile inputs are copied for each request. Public source/embedding caches retain their existing policies; personal queries, profiles and explanations are not added to those public caches.

Cancellation is cooperative. It prevents starting further phases and provider calls, and rejects the return of an in-flight provider call. It cannot forcibly interrupt a synchronous HTTP request already underway. A cancelled worker keeps its admission slot until it actually exits, so repeated edits cannot bypass the concurrency limit. Normal source limits and the 45-second AI budget still bound their respective work; disconnecting a browser is not a guaranteed cancellation signal.

A Streamlit fragment polls session-owned job state every half second while work is pending. It applies early/final results on the UI thread and then stops polling once the completed state has been rendered. The inspector remains a separate on-demand fragment. UI polling never repeats a source/model request by itself.

The controller's synchronous API remains available for command-line verification and existing callers. Its optional early-plan observer gets a separate result before provider work starts. An observer error is recorded safely and does not retry source/model work. The early progress snapshot remains independent of the final trace, which also records early-plan readiness time. No fake percentage progress is shown.

This design follows Streamlit's documented [worker/UI separation](https://docs.streamlit.io/develop/concepts/design/multithreading) and [fragment polling](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment). Compatibility is checked against the pinned Streamlit version and in the actual browser workflow.

## Verification and limits

Deterministic event-based checks hold a provider call open while inspecting the early plan, replace a profile before releasing old work, stop AI without losing the source plan, exercise course completion and unexpected errors, and test bounded admission/cleanup. Existing budget, grounding, source and no-AI flows remain regression checks.

The optional browser command runs the same `app.py` UI through a test-only local entrypoint with a deliberately blocked provider:

```bash
python scripts/check_progressive_browser.py --output output/progressive-browser-first.json
```

Install `requirements-browser.txt` and Chromium as described in [browser acceptance](45_BROWSER_ACCEPTANCE.md). Use a new output path each time. This checker accepts no running-host URL. Its isolated process has placeholder credentials, disabled source refresh, and all server-side HTTP calls blocked. The production app/launcher imports no controlled provider. It complements the existing production-launcher preview checks and separate reviewer checks.

Verified application revision: `44cd1c1055be8a4c81e8a34a969c1d9d5890ae92` in [successful CI run 42407079140](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/42407079140).

- **1,600 tests** and **nine runtime checks** pass on Linux and Windows. Twenty new regression cases include six additional student UI scenarios, bringing the Streamlit total to 93 (87 student, six reviewer).
- **Ten production-preview, six reviewer and five controlled progressive-AI browser gates** pass in real Chromium. The progressive checks observe an early source plan, retained unsent form text, a newer profile completing before old work is released, explicit keep-plan cancellation and healthy WebSocket/fragment updates.
- The scripted early-plan gate took 1.594 seconds in one controlled run while the provider was deliberately blocked. Its server HTTP calls were disabled. This is not a real-model/network performance measurement or a guaranteed response time.
- The initial controlled browser runs failed first at checkbox interaction and then at a synthetic prompt correctly rejected by the coverage guard. The checker now uses the visible checkbox label and supported saved-course prompts. Both failed artifacts and the successful follow-up are retained in the evidence.
- All eight frozen/review input hashes match; all 408 actual template grades remain blank.

These controls demonstrate asynchronous UI behavior and stale-result rejection. They do not measure real AI latency or relevance, establish public hosting, or provide independent student feedback. The frozen review/evaluation files remain unchanged.

Verification results and revision identifiers are recorded in [the dated evidence record](evidence/progressive_ai_2026-11-07.json). The app planning estimate is now approximately **92%**, with the full submission still approximately **70%**. This closes the interactive-request gate; genuine evaluation, a student pilot, final real-AI performance evidence and the report/slides/demo remain open.
