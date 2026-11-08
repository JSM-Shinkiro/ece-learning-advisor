# Final submission readiness

Team P07 · Updated November 8, 2026 · Final presentation/submission: December 11 · Planned feature freeze: December 4.

## Current estimate

The app is approximately **95%** of the planned final version. The complete submission is approximately **72%** ready. These are engineering planning judgments against the current scope, not measured accuracy, test-count percentages, instructor grades, or a guarantee of acceptance. No final-specific rubric was located in the reviewed project files; revise these gates when final instructions are available.

Core features are close to complete. The largest remaining work is independent evaluation, a small voluntary student pilot, real-AI/frozen-release performance evidence, and the final report, slides, and recorded demo. Public hosting is a planned pilot option; the reviewed midproject guidance also allows reproducible local access. It is not established as a mandatory final requirement.

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
| Student pilot | Open | Run 3–5 voluntary tasks, record failures and feedback without inventing participants or results |
| Final report, slides, new demo | Open | Prepare separately from preserved midproject artifacts; explain scope, evaluation, math/inspection, responsiveness and limitations |
| Submission release and final instructions | Open | Reconcile final guidance, freeze/tag a reproducible revision, verify all final links and artifacts |

## Current development step

[CI status and runner diagnostics](53_CI_STATUS_AND_RUNNER.md) identify the reported screenshot as an older run whose two timing commands failed at reopening. The subsequent collector fix already passed both complete timing cohorts. The failed and successful runs both used Ubuntu 26.04; Linux jobs now explicitly select that tested release. A new GitHub summary separates the three UI acceptance workflows from the two offline timing cohorts, with actual counts, fixed failed-stage names and the current commit/run link. Missing, malformed or contradictory reports cannot produce a passing summary.

All 1,661 tests and nine runtime checks pass on Linux and Windows, plus all 26 browser acceptance gates and five complete timing sessions per version in [fresh run 42458364808](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/42458364808). Verified revision: `19b8c9c193192779a8333df6f050f0fea5662105`. Both Linux jobs report Ubuntu 26.04. The attached/saved summary has five PASS rows with this commit and run; the browser artifact was downloaded and SHA-256 verified. The student app, source data, ranking, profiles and academic rules are unchanged by this step. Earlier failed runs retain their original conclusions.

App/full-submission readiness remain approximately **95% / 72%**. This unit improves CI reproducibility and diagnostics; independent evaluation, student feedback, real-AI/final-release timing and report/slides/demo remain open. All 408 template grades and eight frozen/review input hashes are unchanged. The inspector comparison and its corrected reopening measurements remain documented separately; no new live-AI, physical-paint, quality or participant result is claimed.

## Next steps toward the submission

1. Gather independent judgments and voluntary student feedback; automated controls cannot replace these.
2. Measure real-AI/source/cache cohorts, address material misses, then repeat final evidence on the frozen revision.
3. Write the final report, prepare slides/demo, and verify the submission package against the final instructions.

Every development update should state the gate closed by that step, the app/submission readiness estimate, and the most consequential remaining gap. Estimates move when acceptance gates close, not when the test count grows.
