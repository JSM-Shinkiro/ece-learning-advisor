# Final submission readiness

Team P07 · Updated November 13, 2026 MST · Final presentation and submission December 11 · Planned feature freeze December 4.

## Current estimate

The app is approximately **92%** complete for the agreed final scope of two career directions, broader undergraduate ECE browsing and a self-guided learning experience. The complete submission is approximately **69%** ready. Both percentages are planning estimates.

The Advisor now shows a dated saved-data plan before official source checks finish in both preview and AI modes. The learner can inspect the plan, submit a profile update, or keep the current plan. The live source-only probe built the first plan on the server in 19.5 ms while empty-cache checks took 16.82 s. The source run updated two records and retained nine bundled fallbacks. [Roadmap verification](evidence/saved_data_roadmap_2026-11-13.json)

The November 13 development step addresses the audit's lesson gaps. Presets, methods, and drafts persist across stages. Advanced supports the reported custom questions and checks the selected record's rank change before saving the explanation. The evaluated question opens in the Advisor as a draft, and its inspector compares topic counts with the embeddings from a semantic or hybrid request. [Audit](58_FINAL_VERSION_AUDIT.md) · [Verification](evidence/lesson_continuity_2026-11-13.json)

The midproject review gives explicit direction for the final recording and learning experience. Confirm final timing, formatting, duration and packaging instructions in D2L. The supported delivery uses reproducible local access and portable JSON profiles.

The November 8 audit weights give 69% submission completion. [Planning weights](56_FINAL_READINESS_AUDIT.md)

| Component | Weight | Progress estimate |
| --- | ---: | ---: |
| Application and focused academic data | 50% | 92% |
| Evaluation and performance evidence | 15% | 40% |
| Final technical report | 20% | 65% |
| Presentation and recording | 10% | 20% |
| Release and delivery | 5% | 40% |

| Acceptance gate | Status | Evidence or remaining work |
| --- | --- | --- |
| Self-guided learning and developer view | Verified in controlled workflows | Chromium checks the draft round trip, explanation export and Advisor comparison using test vectors. Capture the live neural example and observe students completing the lesson. |
| Student profile → grounded roadmap → current/completed progress | Implemented | Preview and Gemini paths, JSON portability, conservative academic checks, bounded AI work |
| Course/resource coverage and provenance | Broader inventory implemented; advising partial | 78 published undergraduate ECE descriptions; default 20-course/eight-resource/34-chunk advisor covers two directions. Up to three requested catalog additions; unknown preparation/conditions remain explicit. Focus on a defensible ECE demo chain; universal mappings/supporting-subject coverage are extensions. |
| Opportunity workflow | Implemented with limits | Three public boards, filters, detail checks, paging and recovery; optional Adzuna/OpenRouter remain outside the verified final core |
| Reproducible runtime | Verified | Ubuntu 26.04 and Windows each pass 1,760 tests and nine readiness checks. |
| Browser workflow and concurrent sessions | Verified in CI | All 36 Chromium checks pass across student preview, the reviewer workspace, lessons, and controlled source, AI and browsing workflows. |
| Request feedback and timing | Verified with limits | Actual attempted stages are visible and timed; observer failure is isolated; timing excludes provider cleanup and browser rendering |
| Repeated source work and hidden rendering | Verified with limits | Recent successful checks are reused for five minutes. Explicit rechecks bypass reuse. The inspector opens in a fragment. Source checks and posting details still depend on their network response times. |
| Usable plan during source checks and AI | Verified with controlled delays | The saved-data plan appears before sources finish. The updated source plan can appear before AI finishes. Open evidence panels persist. Keeping either plan or submitting a newer profile rejects late results. |
| Collection and posting interactions | Verified with controlled sources | Focused filters and full ECE local paging/search, lazy details and exact variable-credit display at 390 pixels; explicit catalog-to-roadmap action; listing progress and stale/failure recovery. |
| Review entry and resume workflow | Verified tooling | Local human-review workspace supports explicit grades, notes, resumable drafts and validated completed exports; actual independent judgments remain open |
| Hosted access | Open / optional path | No selected public host has been validated; local browser success will not imply TLS/proxy/remote success |
| Independent retrieval/claim evaluation | Open | Prepared 12-question/34-chunk development bundle has 408 blank grades; a local review workspace supports entry/resume, but genuine independent judgments and separately identified held-out cases remain |
| Performance evidence | Partial | In the November 13 source-only probe, first-plan server time was 19.5 ms with an empty cache and 6.3 ms on immediate repeat. Source checks took 16.82 s and 4.08 s, respectively. Repeated live measurements remain open. |
| Student pilot | Prepared / execution open | Self-guided lesson, five advisor tasks, timing and assistance rules, and a blank session sheet for 3–5 voluntary students. |
| Final report, slides and recording | Partial | Report draft and evidence map updated. The three-member runbook specifies private app-only capture and planned transitions. Final figures, report formatting, slides and the recording remain. |
| Submission release and final instructions | Open | Reconcile final guidance, freeze/tag a reproducible revision, verify all final links and artifacts |

## November 13 roadmap verification

The initial Windows run lost open evidence panels during an intermediate redraw. Persisting their state fixed both failures. The Chromium follow-ups verified continued access to the open inspector and started the separate phone opening check with the panel closed. The final run passed on both OSes and in Chromium. [Passing run](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/43488614300) · [Run history and observations](evidence/saved_data_roadmap_2026-11-13.json)

## November 13 lesson verification

The initial Chromium run passed the Advanced export and timed out locating the stage switcher. The follow-up selects the visible stage label, verifies the round trip and passes all 34 browser checks. Both platforms pass the complete backend suite. The embedding comparison uses controlled provider vectors in this run. [Initial run](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/43396473239) · [Passing follow-up](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/43397328386)

## November 13 audit

The audit reads the instructor guidelines, original concept, current code and final materials, confirms the passing CI revision and exercises less scripted lesson navigation. It records seven groups of offline observations, verifies all eight archived input hashes and confirms 408 unfilled review grades. The detailed report defines the intended final journey, priorities, completion checks and schedule. [Audit](58_FINAL_VERSION_AUDIT.md) · [Evidence](evidence/final_version_audit_2026-11-13.json)

## November 12 verification

The first Chromium run timed out submitting the Advanced form after selecting ECE425. The browser check now closes the dropdown and submits with the keyboard. The follow-up passed all three lesson gates and verified the exported observation. Both runs, screenshot hashes and the scope of the offline checks are recorded in [the verification evidence](evidence/midproject_feedback_2026-11-12.json). [Passing CI run](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/43361506460)

## November 8 audit

[The November 8 final-readiness audit](56_FINAL_READINESS_AUDIT.md) checks the current repository/CI, the supplied instructor guidelines and original project archive, final materials, actual public-source/opportunity paths and preserved evaluation inputs. Main is clean at audit base `ccbd7c27c6c449fc0b758b9bafb414758007aa53`; its application code matches the successful `d93fc8e6b137dab44c9e990b92701031c899216e` verification. The prior 1,744 tests/nine runtime checks per OS and 29 browser gates remain dated to [run 42531556423](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/42531556423); no redundant full suite is claimed.

Nine fresh production-readiness checks pass. One real ECE413 request successfully checks eight courses, one program and two resources, includes the requested course and retains unknown enrollment status. All three public employer boards and a displayed posting detail verify successfully; six embedded internship matches are returned. No model credentials or generation are used. Fresh source/job waiting remains a material responsiveness gap: the first source-only check takes 21.664 seconds with recovered timeouts, a disk-cache/new-process check 13.191 seconds and an immediate same-process reuse 0.066 seconds. These are individual server observations, not distributions or browser/AI timings.

The audit recorded **85% app / approximately 65% complete submission** and corrected the report’s attribution of the historical browser timing. All eight frozen inputs still match their archived hashes, and all 408 review grades remain unfilled. [November 8 audit evidence](evidence/final_readiness_audit_2026-11-08.json)

## Next steps toward the submission

1. Review the applicable academic evidence for the focused ECE demonstration.
2. Rehearse the carried question with a configured Gemini provider and capture the neural comparison.
3. Complete independent relevance review and student sessions. Record repeated live source/model/cache observations and address material findings.
4. Finish report figures, results, bibliography, PDF and slides. Rehearse, capture and stitch all three narrated segments.
5. Confirm final D2L instructions, freeze/tag the release, verify setup and access, and assemble the package.

Every development update should state the gate closed by that step, the app/submission readiness estimate, and the most consequential remaining gap. Estimates move when acceptance gates close, not when the test count grows.
