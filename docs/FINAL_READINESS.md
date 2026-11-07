# Final submission readiness

Team P07 · Updated November 7, 2026 · Final presentation/submission: December 11 · Planned feature freeze: December 4.

## Current estimate

The app is approximately **92%** of the planned final version. The complete submission is approximately **70%** ready. These are engineering planning judgments against the current scope, not measured accuracy, test-count percentages, instructor grades, or a guarantee of acceptance. No final-specific rubric was located in the reviewed project files; revise these gates when final instructions are available.

Core features are close to complete. The largest remaining work is independent evaluation, a small voluntary student pilot, browser-visible performance evidence, and the final report, slides, and recorded demo. Public hosting is a planned pilot option; the reviewed midproject guidance also allows reproducible local access. It is not established as a mandatory final requirement.

| Acceptance gate | Status | Evidence or remaining work |
| --- | --- | --- |
| Student profile → grounded roadmap → current/completed progress | Implemented | Preview and Gemini paths, JSON portability, conservative academic checks, bounded AI work |
| Course/resource coverage and provenance | Implemented with limits | 20 courses, eight resources, 34 chunks; four reviewed CS conditions; 15 ECE conditions and CSC372 remain unknown |
| Opportunity workflow | Implemented with limits | Three public boards, filters, detail checks, paging and recovery; optional Adzuna/OpenRouter remain outside the verified final core |
| Reproducible runtime | Verified | Pinned setup, production launcher, Linux/Windows CI, nine readiness checks |
| Actual browser workflow and concurrent sessions | Verified locally in CI | Ten Chromium gates pass, including independent inspector open/close: stage history, real export/import, persistent completion edits, two isolated profiles and bidirectional WebSockets through the production launcher |
| Request feedback and timing | Verified with limits | Actual attempted stages are visible and timed; observer failure is isolated; timing excludes provider cleanup and browser rendering |
| Repeated source work and hidden rendering | Verified with limits | Recent public checks are reused for up to five minutes; explicit rechecks bypass reuse; closed inspection content is omitted and opens in a fragment. Cold HTTP/AI requests remain synchronous. |
| Usable plan while AI runs | Verified with controlled AI | Source plan appears before AI finishes; profile edits/completion supersede old work; explicit keep-plan action rejects late output; four in-process workers; five real-browser gates. |
| Review entry and resume workflow | Verified tooling | Local human-review workspace supports explicit grades, notes, resumable drafts and validated completed exports; actual independent judgments remain open |
| Hosted access | Open / optional path | No selected public host has been validated; local browser success will not imply TLS/proxy/remote success |
| Independent retrieval/claim evaluation | Open | Prepared 12-question/34-chunk development bundle has 408 blank grades; a local review workspace supports entry/resume, but genuine independent judgments and separately identified held-out cases remain |
| Performance evidence | Partial | Real source-only fresh/reused-cache observations are recorded; broader cold/warm and browser-visible measurements on the frozen final revision, including AI, remain |
| Student pilot | Open | Run 3–5 voluntary tasks, record failures and feedback without inventing participants or results |
| Final report, slides, new demo | Open | Prepare separately from preserved midproject artifacts; explain scope, evaluation, math/inspection, responsiveness and limitations |
| Submission release and final instructions | Open | Reconcile final guidance, freeze/tag a reproducible revision, verify all final links and artifacts |

## Current development step

[Progressive AI requests](49_PROGRESSIVE_AI_REQUESTS.md) keep the page interactive while source/AI work runs. A source plan appears after source checks, before optional AI completion. A newer profile invalidates the older request; **Keep source plan** retains the source plan and rejects later AI output. The default synchronous controller API and no-AI source workflow remain available.

The app estimate moves to approximately **92%** by closing the interactive-request gate. The full-submission estimate remains **70%**: independent evaluation, voluntary student feedback, final real-AI/browser performance measurements and the final report/slides/demo remain open. All 408 saved template grades remain blank.

All 1,600 tests and nine runtime checks pass on Linux and Windows; ten production-preview, six reviewer and five controlled progressive-AI browser gates pass in [run 42407079140](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/42407079140). Verified application revision: `44cd1c1055be8a4c81e8a34a969c1d9d5890ae92`. The new browser controls deliberately block generation while checking source-plan use, unsent draft retention, newer-profile precedence and explicit cancellation. They establish UI behavior, not real-provider latency or independent recommendation quality.

## Next steps toward the submission

1. Gather independent judgments and voluntary student feedback; automated controls cannot replace these.
2. Freeze the scoped feature set, collect final latency/quality evidence, and address material misses.
3. Write the final report, prepare slides/demo, and verify the submission package against the final instructions.

Every development update should state the gate closed by that step, the app/submission readiness estimate, and the most consequential remaining gap. Estimates move when acceptance gates close, not when the test count grows.
