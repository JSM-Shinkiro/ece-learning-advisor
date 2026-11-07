# Final submission readiness

Team P07 · Updated November 7, 2026 · Final presentation/submission: December 11 · Planned feature freeze: December 4.

## Current estimate

The app is approximately **85–90%** of the planned final version. The complete submission is approximately **65–70%** ready. These are engineering planning judgments against the current scope, not measured accuracy, test-count percentages, instructor grades, or a guarantee of acceptance. No final-specific rubric was located in the reviewed project files; revise these gates when final instructions are available.

Core features are close to complete. The largest remaining work is independent evaluation, a small voluntary student pilot, browser-visible performance evidence, and the final report, slides, and recorded demo. Public hosting is a planned pilot option; the reviewed midproject guidance also allows reproducible local access. It is not established as a mandatory final requirement.

| Acceptance gate | Status | Evidence or remaining work |
| --- | --- | --- |
| Student profile → grounded roadmap → current/completed progress | Implemented | Preview and Gemini paths, JSON portability, conservative academic checks, bounded AI work |
| Course/resource coverage and provenance | Implemented with limits | 20 courses, eight resources, 34 chunks; four reviewed CS conditions; 15 ECE conditions and CSC372 remain unknown |
| Opportunity workflow | Implemented with limits | Three public boards, filters, detail checks, paging and recovery; optional Adzuna/OpenRouter remain outside the verified final core |
| Reproducible runtime | Verified | Pinned setup, production launcher, Linux/Windows CI, nine readiness checks |
| Actual browser workflow and concurrent sessions | In verification | New Chromium acceptance flow; a passing real-browser run is required before marking this verified |
| Hosted access | Open / optional path | No selected public host has been validated; local browser success will not imply TLS/proxy/remote success |
| Independent retrieval/claim evaluation | Open | Prepared 12-question/34-chunk development review bundle has 408 blank grades; obtain genuine independent judgments and separately identify held-out cases |
| Performance evidence | Partial | Earlier runtime observations exist; measure cold/warm and browser-visible paths on the frozen final revision, distinguish source work from AI time |
| Student pilot | Open | Run 3–5 voluntary tasks, record failures and feedback without inventing participants or results |
| Final report, slides, new demo | Open | Prepare separately from preserved midproject artifacts; explain scope, evaluation, math/inspection, responsiveness and limitations |
| Submission release and final instructions | Open | Reconcile final guidance, freeze/tag a reproducible revision, verify all final links and artifacts |

## Current development step

The browser step adds an optional real Chromium workflow through the production launcher at a URL prefix. It covers current-course filtering, completion with unknown grades, real download/upload restore, two isolated Streamlit sessions, unsupported-request clarification, and bidirectional WebSocket activity. The local environment blocks Chromium startup, so the Linux CI browser job is the acceptance environment. Until that job passes, this gate remains in verification.

## Next steps toward the submission

1. Complete the browser acceptance run and resolve actual workflow failures.
2. Gather independent judgments and voluntary student feedback; automated controls cannot replace these.
3. Freeze the scoped feature set, collect final latency/quality evidence, and address material misses.
4. Write the final report, prepare slides/demo, and verify the submission package against the final instructions.

Every development update should state the gate closed by that step, the app/submission readiness estimate, and the most consequential remaining gap. Estimates move when acceptance gates close, not when the test count grows.
