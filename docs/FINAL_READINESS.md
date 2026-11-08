# Final submission readiness

Team P07 · Updated November 7, 2026 · Final presentation/submission: December 11 · Planned feature freeze: December 4.

## Current estimate

The app is approximately **94%** of the planned final version. The complete submission is approximately **70%** ready. These are engineering planning judgments against the current scope, not measured accuracy, test-count percentages, instructor grades, or a guarantee of acceptance. No final-specific rubric was located in the reviewed project files; revise these gates when final instructions are available.

Core features are close to complete. The largest remaining work is independent evaluation, a small voluntary student pilot, browser-visible performance evidence, and the final report, slides, and recorded demo. Public hosting is a planned pilot option; the reviewed midproject guidance also allows reproducible local access. It is not established as a mandatory final requirement.

| Acceptance gate | Status | Evidence or remaining work |
| --- | --- | --- |
| Student profile → grounded roadmap → current/completed progress | Implemented | Preview and Gemini paths, JSON portability, conservative academic checks, bounded AI work |
| Course/resource coverage and provenance | Implemented with limits | 20 courses, eight resources, 34 chunks; four reviewed CS conditions; 15 ECE conditions and CSC372 remain unknown |
| Opportunity workflow | Implemented with limits | Three public boards, filters, detail checks, paging and recovery; optional Adzuna/OpenRouter remain outside the verified final core |
| Reproducible runtime | Verified | Pinned setup, production launcher, Linux/Windows CI, nine readiness checks |
| Actual browser workflow and concurrent sessions | Verified locally in CI | Ten Chromium gates pass, including independent inspector open/close: stage history, real export/import, persistent completion edits, two isolated profiles and bidirectional WebSockets through the production launcher |
| Request feedback and timing | Verified with limits | Actual attempted stages are visible and timed; observer failure is isolated; timing excludes provider cleanup and browser rendering |
| Repeated source work and hidden rendering | Verified with limits | Recent public checks are reused for up to five minutes; explicit rechecks bypass reuse; closed inspection content is omitted and opens in a fragment. Cold no-AI source updates and posting HTTP calls still wait for the network. |
| Usable plan while AI runs | Verified with controlled AI | Source plan appears before AI finishes; profile edits/completion supersede old work; explicit keep-plan action rejects late output; four in-process workers; five real-browser gates. |
| Collection and posting interactions | Verified with controlled sources | Local search/type/direction filters and reset; lazy source details; 390-pixel phone checks; listing-level progress; stale intent/return rejection and failed-recheck search retention. |
| Review entry and resume workflow | Verified tooling | Local human-review workspace supports explicit grades, notes, resumable drafts and validated completed exports; actual independent judgments remain open |
| Hosted access | Open / optional path | No selected public host has been validated; local browser success will not imply TLS/proxy/remote success |
| Independent retrieval/claim evaluation | Open | Prepared 12-question/34-chunk development bundle has 408 blank grades; a local review workspace supports entry/resume, but genuine independent judgments and separately identified held-out cases remain |
| Performance evidence | Partial | Real source-only fresh/reused-cache observations are recorded; broader cold/warm and browser-visible measurements on the frozen final revision, including AI, remain |
| Student pilot | Open | Run 3–5 voluntary tasks, record failures and feedback without inventing participants or results |
| Final report, slides, new demo | Open | Prepare separately from preserved midproject artifacts; explain scope, evaluation, math/inspection, responsiveness and limitations |
| Submission release and final instructions | Open | Reconcile final guidance, freeze/tag a reproducible revision, verify all final links and artifacts |

## Current development step

[Collection browsing and posting feedback](50_COLLECTION_AND_POSTING_UX.md) add local course/resource search, type/direction filters, empty/reset states and lazy source details. The opportunities fragment shows progress beside the selected posting. Search/page/profile changes discard queued and late checks; a failed detail recheck retains the saved search and removes older verified content.

All 1,612 tests and nine runtime checks pass on Linux and Windows, plus ten production-preview, six reviewer and nine controlled AI/browsing gates in [run 42409330351](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/42409330351). Verified application revision: `d1de020a22637963abbcb15c9b79a788ef21b535`. The added browser controls verify local-only interactions, preserved draft text, phone-width layout and visible deliberately delayed posting feedback. They do not establish live employer availability or real-network performance.

The app estimate rises to approximately **94%** by closing these interaction gaps. Full-submission readiness remains **70%**: independent evaluation, voluntary student feedback, final real-AI/browser performance measurements and the report/slides/demo remain open. All 408 saved template grades remain blank.

## Next steps toward the submission

1. Gather independent judgments and voluntary student feedback; automated controls cannot replace these.
2. Freeze the scoped feature set, collect final latency/quality evidence, and address material misses.
3. Write the final report, prepare slides/demo, and verify the submission package against the final instructions.

Every development update should state the gate closed by that step, the app/submission readiness estimate, and the most consequential remaining gap. Estimates move when acceptance gates close, not when the test count grows.
