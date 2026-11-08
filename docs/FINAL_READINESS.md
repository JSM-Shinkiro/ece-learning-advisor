# Final submission readiness

Team P07 · Updated November 8, 2026 · Final presentation/submission: December 11 · Planned feature freeze: December 4.

## Current estimate

The app is approximately **95%** of the planned final version. The complete submission is approximately **76%** ready. These are engineering planning judgments against the current scope, not measured accuracy, test-count percentages, instructor grades, or a guarantee of acceptance. No final-specific rubric was located in the reviewed project files; revise these gates when final instructions are available.

Core features are close to complete. A written report draft and evidence/demo/pilot materials are prepared. The largest remaining work is genuine independent evaluation, student sessions, real-AI/frozen-release performance evidence, final figures/formatting, slides and a new recorded demo. Public hosting is a planned pilot option; the reviewed midproject guidance also allows reproducible local access. It is not established as a mandatory final requirement.

| Acceptance gate | Status | Evidence or remaining work |
| --- | --- | --- |
| Student profile → grounded roadmap → current/completed progress | Implemented | Preview and Gemini paths, JSON portability, conservative academic checks, bounded AI work |
| Course/resource coverage and provenance | Implemented with limits | 20 courses, eight resources, 34 chunks; four reviewed CS conditions; 15 ECE conditions and CSC372 remain unknown |
| Opportunity workflow | Implemented with limits | Three public boards, filters, detail checks, paging and recovery; optional Adzuna/OpenRouter remain outside the verified final core |
| Reproducible runtime | Verified | Pinned setup, production launcher, explicit Ubuntu 26.04 release/Windows CI, nine readiness checks and per-report browser/timing summary |
| Actual browser workflow and concurrent sessions | Verified locally in CI | Ten Chromium gates pass, including independent inspector open/close: stage history, real export/import, persistent completion edits, two isolated profiles and bidirectional WebSockets through the production launcher |
| Request feedback and timing | Verified with limits | Actual attempted stages are visible and timed; observer failure is isolated; timing excludes provider cleanup and browser rendering |
| Repeated source work and hidden rendering | Verified with limits | Recent public checks are reused for up to five minutes; explicit rechecks bypass reuse; closed inspection content is omitted and opens in a fragment. Cold no-AI source updates and posting HTTP calls still wait for the network. |
| Usable plan while AI runs | Verified with controlled AI | Source plan appears before AI finishes; profile edits/completion supersede old work; explicit keep-plan action rejects late output; four in-process workers; five real-browser gates. |
| Collection and posting interactions | Verified with controlled sources | Local search/type/direction filters and reset; lazy source details; 390-pixel phone checks; listing-level progress; stale intent/return rejection and failed-recheck search retention. |
| Review entry and resume workflow | Verified tooling | Local human-review workspace supports explicit grades, notes, resumable drafts and validated completed exports; actual independent judgments remain open |
| Hosted access | Open / optional path | No selected public host has been validated; local browser success will not imply TLS/proxy/remote success |
| Independent retrieval/claim evaluation | Open | Prepared 12-question/34-chunk development bundle has 408 blank grades; a local review workspace supports entry/resume, but genuine independent judgments and separately identified held-out cases remain |
| Performance evidence | Partial | Two five-session cohorts use the same v2 collector on one runner: inspector first opening median 1,608.4 ms baseline → 686.7 ms native; native reopening 307.8 ms. Source-only observations remain separate; real-AI, hosted/mobile timing and final-revision cache cohorts remain |
| Student pilot | Prepared / execution open | Five-task protocol, timing/assistance rules and blank session sheet are ready for 3–5 voluntary students; no actual observations have been supplied |
| Final report, slides, new demo | Draft prepared / partial | Separate written report, evidence map/manifest and demo runbook are ready; final instructions/figures/results/formatting, slides and recording remain |
| Submission release and final instructions | Open | Reconcile final guidance, freeze/tag a reproducible revision, verify all final links and artifacts |

## Current development step

[Final submission preparation](54_FINAL_SUBMISSION_DRAFT.md) creates a separate substantive report draft covering the architecture, algorithms, partial academic checks, bounded explanation contract, measured results and limitations. Its evidence map/manifest keeps the ten-chunk authored benchmark, 34-chunk integration, software checks and offline preview timings distinct. A production-entrypoint demo runbook and five-task pilot protocol/blank observation sheet are ready for use.

The new instructions pass eight offline AppTest walkthrough checks and all seven production-launcher preflight checks. The report's eight metric-table rows match the retained JSON; final-workspace links and source/input hashes are checked. These are documentation checks, with HTTP/model work blocked in the walkthrough and no employer search. No new real-AI, browser-latency or human result is added. Application code/data are unchanged; [run 42458364808](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/42458364808), at `19b8c9c193192779a8333df6f050f0fea5662105`, remains the runtime verification: 1,661 tests/nine runtime checks per OS, 26 browser gates and two complete five-session preview cohorts. Its original results/dates are retained rather than rerunning the suite for documentation changes.

App readiness remains approximately **95%**; full-submission readiness rises to approximately **76%** for the concrete written draft and preparation materials. This is partial progress on final artifacts, not a completed submission or measured quality improvement. All 408 template grades remain blank and all eight frozen/review input hashes are unchanged. Genuine judgments/pilot sessions, real-AI/final-release measurements, final figures/formatting, slides, recording and frozen packaging remain open.

## Next steps toward the submission

1. Gather independent judgments and voluntary student feedback; automated controls cannot replace these.
2. Measure real-AI/source/cache cohorts, address material misses, then repeat final evidence on the frozen revision.
3. Complete the report with actual findings and final figures/formatting, prepare slides/recording, and verify the frozen package against the final instructions.

Every development update should state the gate closed by that step, the app/submission readiness estimate, and the most consequential remaining gap. Estimates move when acceptance gates close, not when the test count grows.
