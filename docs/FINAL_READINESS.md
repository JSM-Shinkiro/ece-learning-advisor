# Final submission readiness

Team P07 · Updated November 8, 2026 · Final presentation/submission: December 11 · Planned feature freeze: December 4.

## Current estimate

The app is approximately **85%** complete for the agreed final core: two initial career directions with broader undergraduate ECE browsing. The complete final submission is approximately **65%** ready, with a planning range of **60–70%** while final-only instructions remain unconfirmed. These are engineering planning judgments, not measured accuracy, test percentages, instructor grades or a guarantee of acceptance.

The [current readiness audit](56_FINAL_READINESS_AUDIT.md) keeps the app estimate at 85% and corrects the earlier 75% submission estimate. Prepared review/pilot tooling and a Markdown report draft were credited too generously; actual judgments, participant observations, final figures/PDF, slides, recording and final packaging remain open. A transparent planning model gives 63.5%, rounded to about 65%. The earlier 95% app estimate described a narrower prototype; that historical estimate is not reused.

The supplied instructor guidance establishes December 11 for presentation/submission but is a midpoint document. Its page limit, two-minute demo, filename and weights are not established final rules. No later final-specific rubric or final-report folder was found in the reviewed sources. Final time, formatting, duration and packaging rules remain to be reconciled with D2L. Public hosting, automatic accounts, universal career mappings and graduate/degree-audit expansion are not established mandatory final requirements; reproducible local access and portable JSON profiles remain the supported core.

| Acceptance gate | Status | Evidence or remaining work |
| --- | --- | --- |
| Student profile → grounded roadmap → current/completed progress | Implemented | Preview and Gemini paths, JSON portability, conservative academic checks, bounded AI work |
| Course/resource coverage and provenance | Broader inventory implemented; advising partial | 78 published undergraduate ECE descriptions; default 20-course/eight-resource/34-chunk advisor covers two directions. Up to three requested catalog additions; unknown preparation/conditions remain explicit. Focus on a defensible ECE demo chain; universal mappings/supporting-subject coverage are extensions. |
| Opportunity workflow | Implemented with limits | Three public boards, filters, detail checks, paging and recovery; optional Adzuna/OpenRouter remain outside the verified final core |
| Reproducible runtime | Verified | Pinned setup, production launcher, explicit Ubuntu 26.04 release/Windows CI, nine readiness checks and per-report browser/timing summary |
| Actual browser workflow and concurrent sessions | Verified locally in CI | Ten Chromium gates pass, including independent inspector open/close: stage history, real export/import, persistent completion edits, two isolated profiles and bidirectional WebSockets through the production launcher |
| Request feedback and timing | Verified with limits | Actual attempted stages are visible and timed; observer failure is isolated; timing excludes provider cleanup and browser rendering |
| Repeated source work and hidden rendering | Verified with limits | Recent public checks are reused for up to five minutes; explicit rechecks bypass reuse; closed inspection content is omitted and opens in a fragment. Cold no-AI source updates and posting HTTP calls still wait for the network. |
| Usable plan while AI runs | Verified with controlled AI | Source plan appears before AI finishes; profile edits/completion supersede old work; explicit keep-plan action rejects late output; four in-process workers; five real-browser gates. |
| Collection and posting interactions | Verified with controlled sources | Focused filters and full ECE local paging/search, lazy details and exact variable-credit display at 390 pixels; explicit catalog-to-roadmap action; listing progress and stale/failure recovery. |
| Review entry and resume workflow | Verified tooling | Local human-review workspace supports explicit grades, notes, resumable drafts and validated completed exports; actual independent judgments remain open |
| Hosted access | Open / optional path | No selected public host has been validated; local browser success will not imply TLS/proxy/remote success |
| Independent retrieval/claim evaluation | Open | Prepared 12-question/34-chunk development bundle has 408 blank grades; a local review workspace supports entry/resume, but genuine independent judgments and separately identified held-out cases remain |
| Performance evidence | Partial | Historical paired inspector medians remain 1,608.4 → 686.7 ms. Latest CI repeat is separately 1,714.0 → 683.7 ms. Fresh audit source-only observations: 21.664 s empty cache, 13.191 s disk cache/new process, 0.066 s immediate reuse; recovered timeouts included. Repeated final-release live-AI/source/cache/browser evidence remains. |
| Student pilot | Prepared / execution open | Five-task protocol, timing/assistance rules and blank session sheet are ready for 3–5 voluntary students; no actual observations have been supplied |
| Final report, slides, new demo | Draft prepared / partial | Separate written report, evidence map/manifest and demo runbook are ready; final instructions/figures/results/formatting, slides and recording remain |
| Submission release and final instructions | Open | Reconcile final guidance, freeze/tag a reproducible revision, verify all final links and artifacts |

## Current audit

[The November 8 final-readiness audit](56_FINAL_READINESS_AUDIT.md) checks the current repository/CI, the supplied instructor guidelines and original project archive, final materials, actual public-source/opportunity paths and preserved evaluation inputs. Main is clean at audit base `ccbd7c27c6c449fc0b758b9bafb414758007aa53`; its application code matches the successful `d93fc8e6b137dab44c9e990b92701031c899216e` verification. The prior 1,744 tests/nine runtime checks per OS and 29 browser gates remain dated to [run 42531556423](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/42531556423); no redundant full suite is claimed.

Nine fresh production-readiness checks pass. One real ECE413 request successfully checks eight courses, one program and two resources, includes the requested course and retains unknown enrollment status. All three public employer boards and a displayed posting detail verify successfully; six embedded internship matches are returned. No model credentials or generation are used. Fresh source/job waiting remains a material responsiveness gap: the first source-only check takes 21.664 seconds with recovered timeouts, a disk-cache/new-process check 13.191 seconds and an immediate same-process reuse 0.066 seconds. These are individual server observations, not distributions or browser/AI timings.

The report's latest-repeat timing sentence is corrected to the actual cited CI medians; the original optimization experiment is preserved. All eight frozen/review input hashes still match and 408 review grades remain null. No participant result is added. The audit changes documentation/evidence only. It resolves the requirement/scope classification and reporting mismatch; **85% app / approximately 65% complete submission** is the current planning estimate. See [audit evidence](evidence/final_readiness_audit_2026-11-08.json) and the audit's explicit remaining-deliverable matrix.

## Next steps toward the submission

1. Reconcile final-only instructions and freeze the core scope; start genuine reviewer/student sessions early.
2. Resolve authoritative conditions for the focused ECE demo and improve fresh-source waiting; retain unknowns where evidence is unavailable.
3. Collect repeated actual-AI/source/cache observations on the release, retain failures and address material misses.
4. Finish current report figures/results/bibliography/PDF, slides, rehearsal and a new neural-mode recording.
5. Freeze/tag, check reproducibility/access/links and assemble the final package under the actual final rules.

Every development update should state the gate closed by that step, the app/submission readiness estimate, and the most consequential remaining gap. Estimates move when acceptance gates close, not when the test count grows.
