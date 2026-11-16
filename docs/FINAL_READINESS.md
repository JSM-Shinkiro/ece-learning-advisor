# Final submission readiness

Team P07 · Updated November 15, 2026 MST · Final presentation and submission December 11 · Planned feature freeze December 4.

## Current estimate

The app is approximately **95%** complete with eight career directions, selectable specializations, undergraduate ECE browsing and a self-guided learning experience. The complete submission is approximately **72%** ready. Both percentages are planning estimates.

The specialization expansion adds Photonics & Electro-Optics, Power & Energy Systems, and Biomedical Instrumentation & Sensors. The eight paths expose 17 choices with preparation courses and exercises. The combined collection has 47 courses and 16 resources. Independent evaluation of the new roadmaps and a student walkthrough remain open. [Career directions](59_CAREER_DIRECTIONS.md)

The November 15 live Hybrid rehearsal passed all 11 checks for the carried question. Gemini selected ECE425 and produced the seven-record embedding comparison. The official catalog refreshed ECE425 and its enrollment status stayed unknown. The live browser capture and team recording remain open. [Live rehearsal evidence](evidence/live_demo_rehearsal_2026-11-15.json) · [Demo runbook](final/DEMO_RUNBOOK.md#one-request-rehearsal)

The catalog repair revalidates the published CSC110, CSC120, CSC144 and CSC210 statements. A source-only request with a fictional B in ECE101 satisfies the reviewed CSC120 prerequisite. Program course-list discovery uses saved references because the separate payloads were unavailable. [Catalog verification](evidence/rendered_program_statements_2026-11-15.json)

The four demo courses now show dated department references and a direct class search. The directory exposes its effective-date filter, retrieval time and course record dates. The source checker can refresh published course fields even when the catalog omits inline course metadata. ECE eligibility remains unknown. [Enrollment source review](evidence/focused_ece_enrollment_2026-11-13.json)

The Advisor now shows a dated saved-data plan before official source checks finish in both preview and AI modes. The learner can inspect the plan, submit a profile update, or keep the current plan. The live source-only probe built the first plan on the server in 19.5 ms while empty-cache checks took 16.82 s. The source run updated two records and retained nine bundled fallbacks. [Roadmap verification](evidence/saved_data_roadmap_2026-11-13.json)

The November 13 development step addresses the audit's lesson gaps. Presets, methods, and drafts persist across stages. Advanced supports the reported custom questions and checks the selected record's rank change before saving the explanation. The evaluated question opens in the Advisor as a draft, and its inspector compares topic counts with the embeddings from a semantic or hybrid request. [Audit](58_FINAL_VERSION_AUDIT.md) · [Verification](evidence/lesson_continuity_2026-11-13.json)

The midproject review gives explicit direction for the final recording and learning experience. Confirm final timing, formatting, duration and packaging instructions in D2L. The supported delivery uses reproducible local access and portable JSON profiles.

The report draft now links five captioned Chromium captures from the verified revision. The embedding comparison uses test vectors, and the saved-data roadmap uses a controlled source delay. The passing live rehearsal advances the app and evaluation estimates. The November 8 audit weights give approximately 72% submission completion. [Application figures](final/FIGURES.md) · [Planning weights](56_FINAL_READINESS_AUDIT.md)

| Component | Weight | Progress estimate |
| --- | ---: | ---: |
| Application and focused academic data | 50% | 95% |
| Evaluation and performance evidence | 15% | 45% |
| Final technical report | 20% | 70% |
| Presentation and recording | 10% | 20% |
| Release and delivery | 5% | 40% |

| Acceptance gate | Status | Evidence or remaining work |
| --- | --- | --- |
| Self-guided learning and developer view | Verified in controlled workflows | Chromium checks the draft round trip, explanation export, and Advisor comparison download using test vectors. Capture the live neural example and observe students completing the lesson. |
| Student profile → grounded roadmap → current/completed progress | Verified | The live rehearsal verifies the Hybrid explanation and interim plans. CI verifies saved profiles, conservatively checked academic conditions and progress changes. |
| Course/resource coverage and provenance | Focused source review complete | Eight career directions, 47 curated courses, 16 resources and a 78-entry ECE directory. Ten outside-ECE elective candidates need advisor approval. The Mathematics minor card links the published requirements. The archived review uses 34 chunks. |
| Opportunity workflow | Implemented with limits | Three public boards, filters, detail checks, paging and recovery; optional Adzuna/OpenRouter remain outside the verified final core |
| Reproducible runtime | Verified | Ubuntu 26.04 and Windows each pass 1,813 tests and nine readiness checks. [Passing run](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/43784349217) |
| Browser workflow and concurrent sessions | Verified in CI | All 39 Chromium checks pass, including switching Photonics branches and opening Biomedical Imaging, elective and minor guidance at 390 pixels. The carried-question case exports comparison rows from controlled vectors. |
| Request feedback and timing | Verified with limits | Actual attempted stages are visible and timed; observer failure is isolated; timing excludes provider cleanup and browser rendering |
| Repeated source work and hidden rendering | Verified with limits | Recent successful checks are reused for five minutes. Explicit rechecks bypass reuse. The inspector opens in a fragment. Source checks and posting details still depend on their network response times. |
| Usable plan during source checks and AI | Verified with controlled delays | The saved-data plan appears before sources finish. The updated source plan can appear before AI finishes. Open evidence panels persist. Keeping either plan or submitting a newer profile rejects late results. |
| Collection and posting interactions | Verified with controlled sources | Focused filters and full ECE local paging/search, lazy details and exact variable-credit display at 390 pixels; explicit catalog-to-roadmap action; listing progress and stale/failure recovery. |
| Review entry and resume workflow | Verified tooling | Local human-review workspace supports explicit grades, notes, resumable drafts and validated completed exports; actual independent judgments remain open |
| Hosted access | Open / optional path | No selected public host has been validated; local browser success will not imply TLS/proxy/remote success |
| Independent retrieval/claim evaluation | Open | Prepared 12-question/34-chunk development bundle has 408 blank grades; a local review workspace supports entry/resume, but genuine independent judgments and separately identified held-out cases remain |
| Performance evidence | Partial | In one live cold-index rehearsal, the dated plan was ready on the server in 18.3 ms and the full request took 33.18 s. Repeated live and browser measurements remain open. [Live timings](evidence/live_demo_rehearsal_2026-11-15.json) |
| Student pilot | Prepared / execution open | Self-guided lesson, five advisor tasks, timing and assistance rules, and a blank session sheet for 3–5 voluntary students. |
| Final report, slides and recording | Partial | The report has five captioned captures and an evidence map. Live neural and opportunity captures, report formatting, slides and the three-member recording remain. |
| Submission release and final instructions | Open | Reconcile final guidance, freeze/tag a reproducible revision, verify all final links and artifacts |

## Rendered catalog requirement verification

The expected program, 2026–27 edition and exact requirement sections bind the rendered text to the existing reviewed rules. The warm-index Hybrid follow-up passed all 11 assertions and produced the seven-record comparison. [Verification](evidence/rendered_program_statements_2026-11-15.json)

## Live Gemini rehearsal

The Hybrid request used 34 document embeddings, one query embedding and one generation. Eight course records and two resources refreshed. Two program checks used their saved references. All 11 checks passed. [Evidence](evidence/live_demo_rehearsal_2026-11-15.json)

## Report figure verification and earlier preflight

Each draft figure matches an image from passing run 43688855340. The evidence record identifies the browser check, viewport and image hash. The initial November 15 preflight stopped before any model request because a local Gemini credential was missing. [Figures](final/FIGURES.md) · [Verification](evidence/report_figures_2026-11-15.json)

## Career specialization verification

The regression suite exercises each specialization. Eight source-only requests refreshed the 16 added catalog records. A separate Biomedical Imaging request refreshed both course anchors and retained unknown enrollment status for BME416. [Evidence](evidence/career_specializations_2026-11-14.json) · [Passing run](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/43688855340)

## November 14 semiconductor and Mathematics verification

Design and fabrication questions produce different study routes. Both requested elective candidates can enter the same roadmap, with enrollment unverified. Three source-only requests refreshed the five new course descriptions. The hosted follow-up checked both candidate links and the phone-width Mathematics minor card. [Evidence](evidence/semiconductors_and_math_minor_2026-11-14.json) · [Passing run](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/43683226351)

## November 13 demo rehearsal verification

The one-request verifier passes with controlled saved and refreshed sources. A separate live source-only probe with the same profile refreshed ECE425 and kept its enrollment status unknown. Source checks took 13.15 s and the first saved-data plan took 11.3 ms to assemble on the server. The live model path still needs a local operator credential. [Passing CI](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/43498957696) · [Verification evidence](evidence/final_demo_rehearsal_2026-11-13.json)

## November 13 enrollment verification

Four live, AI-disabled requests refreshed ECE101, ECE369A, ECE372A and ECE425 from the published catalog pages. All four enrollment states stayed unknown. Linux, Windows and Chromium passed the new revision. [Passing run](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/43494092036) · [Source review and email diagnosis](evidence/focused_ece_enrollment_2026-11-13.json)

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

1. Capture the live browser path from the rehearsal in the team demo. Show ECE425 and its section lookup, then the two rankings for the same seven records.
2. Complete independent relevance review and student sessions. Record repeated live source/model/cache observations and address material findings.
3. Finish report figures, results, bibliography, PDF and slides. Rehearse, capture and stitch all three narrated segments.
4. Confirm final D2L instructions, freeze/tag the release, verify setup and access, and assemble the package.

Every development update should state the gate closed by that step, the app/submission readiness estimate, and the most consequential remaining gap. Estimates move when acceptance gates close, not when the test count grows.

## Future releases

Later proposals include Pima transfer tracks, broader career search, instructor ratings, and additional UArizona departments. [Future development notes](FUTURE_DEVELOPMENT.md)
