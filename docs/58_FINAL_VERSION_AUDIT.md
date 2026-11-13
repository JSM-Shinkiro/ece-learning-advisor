# ECE Learning Advisor final-version audit

Team P07 · November 13, 2026 MST · Audited revision `192f1fc80801d3cd283ea4e888b8805dc3ebe60f`

**The application has a substantial working core. The remaining work must make it a coherent teaching experience, demonstrate the actual neural path, and supply the evaluation and finished deliverables.** Current planning readiness is approximately **85% for the app and 65% for the complete submission**. This audit revises the earlier 90% / 70% estimate after reproducing gaps in navigation, custom questions and lesson state.

The midproject feedback identifies the learning experience, visual presentation and recording as priorities. A criterion-by-criterion score breakdown and final-specific rubric are unavailable in the reviewed material. The estimates below describe work remaining. The final grade will depend on the instructor's assessment.

The audit reviewed the instructor's four-page midproject guidelines, the original brainstorming and system-flow documents, the current repository, the final preparation files and the latest successful CI run. Additional offline AppTest probes exercised less scripted navigation and questions. The recorded browser screenshots were inspected, including the 390-pixel landing view. The existing CI results remain attached to their original revision and date. [Audit evidence](evidence/final_version_audit_2026-11-13.json)

The course guidance establishes December 11 for final presentation and submission. The midproject feedback adds the three Bloom stages, visualization-code access and final recording directions. The final report format, duration, submission time and package rules still need confirmation in D2L. The midpoint's page limit and two-minute demo apply to that earlier deliverable. [Instructor guidelines](https://chatgpt.com/library?file_id=libfile_0faf3b2c20dc8191a9acae08d7bdda29&account_id=personal)

The final product should let a prospective or current ECE student learn how evidence becomes a recommendation, test that process, and apply it to their own preparation. AI/ML and embedded systems remain the two supported advising directions. The 78-course undergraduate directory supports broader exploration. A clear landing-page promise would be “Learn how AI finds relevant ECE courses, then use it to plan your next step.”

| Final experience | What the learner should accomplish | Current status |
| --- | --- | --- |
| Beginner | Explain the two supported directions, identify a source, describe an embedding in ordinary language, and distinguish relevance from prerequisite evidence | Illustrated introduction, flowchart, roadmap and one prerequisite question work. Embeddings, cosine, projection and RAG need a short worked example. |
| Intermediate | Predict a result, run one preset, switch retrieval method, inspect evidence and explain a rank change | Local ranking controls work. Evidence is buried inside the developer panel, and the check only asks which record ranks first. |
| Advanced | Modify the same experiment, choose evaluation criteria, compare outcomes and justify a decision using source evidence | Custom comparison and export work. Navigation resets inputs, common questions can miss the topic vocabulary, and any nonempty observation completes the activity. |
| Advisor | Carry a chosen question into the personal workflow, adjust background, see changed recommendations and inspect the neural calculation | Profile editing, retrieval and inspection work. The lesson question is dropped when opening Advisor. The neural path needs an explicit teaching handoff. |
| Return visit | Restore a profile and resume the intended work with clear saved-state feedback | JSON profile portability works. Lesson drafts and results have inconsistent retention across navigation, and lesson progress is session-local. |
| Final demonstration | Show a real neural request, input-driven visual changes, the mathematical inspection and useful planning behavior | Runbook prepared. The final clips, edited video, slides and rehearsal remain open. |

Bloom's alignment should be assessed through the learner's actions and explanations. Remember/understand supports the vocabulary, apply/analyze supports a controlled comparison, and evaluate/create supports a justified variation. The proposed completion criteria above make those outcomes observable. [University of Arkansas guidance](https://tips.uark.edu/using-blooms-taxonomy/)

The strongest completed work is the underlying integration. The latest verified application passed 1,745 tests and nine production checks on each of Linux and Windows, plus 32 Chromium gates. Those gates cover the scripted lessons, profile portability, coursework changes, isolated sessions, reviewer entry and controlled AI/source behavior. The final recording still needs actual provider output. [Passing CI run](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/43361506460)

| Area | Verified capability | Remaining final-version gap |
| --- | --- | --- |
| Retrieval | BM25, cosine, reciprocal rank fusion, cached public embeddings and source-bound explanations | Make the relationship between the teaching representation and pretrained embeddings explicit and usable. |
| G1 structural overview | Actual-vector PCA in neural Advisor mode and a four-feature teaching plot | Show the same question and documents through the teaching and neural views. |
| G2 mathematical drill-down | Full-dimensional cosine, dot product, norms and vector components in the Advisor | Add a small numeric example and explain how a projection can lose information. |
| G3 meaningful manipulation | Questions, methods, profile history and course completion change results | Preserve experiment settings between stages and show a clear before/after comparison. |
| G4 responsiveness | Fast local browsing, lazy inspection, source reuse and background AI jobs | Produce a useful saved-data plan before fresh source checks finish, and verify real request timings. |
| Academic catalog | 78 undergraduate ECE entries and a 20-course/eight-resource advisor corpus | Review a focused ECE preparation chain and display the directory's effective date. |
| Progress | Current/completed coursework and JSON profile import/export | Explain portability clearly and preserve lesson drafts during navigation. |
| Opportunities | Three public employer boards, filters, detail checks and recovery | Retain a real final-demo outcome and its date. |
| Visual presentation | Two illustrations, icons, responsive flowchart, stage cards, charts and collapsible details | Improve the lesson evidence view, phone entry point and explanation of chart changes. |
| Evaluation | Archived benchmarks and a working human review tool | Complete independent relevance judgments and student observations. |
| Delivery | Pinned dependencies, launcher, report draft and team runbook | Final figures/PDF, slides, recording, release, access check and package. |

The audit reproduced the following issues through normal lesson controls. These findings are the immediate repair list.

| Finding | Reproduction and impact | Proposed fix and completion check |
| --- | --- | --- |
| F1. Stage handoff resets the experiment | Select image classification and Topic cosine in Intermediate, then choose Create your variation. Advanced opens with the sensor preset and Hybrid. The comparison changes without the learner choosing it. | Carry the selected preset and method forward. A change made explicitly in Advanced should remain there on return. Verify all three presets and methods through navigation. |
| F2. Returning shows inconsistent state | Run and save a comparison, open Advisor, then return to Advanced. The old comparison and saved observation remain while the question field and expected-record selector are blank. | Store the editable experiment independently of temporary widget state and restore all relevant fields. Keep draft and last-run result clearly identified if they differ. |
| F3. Familiar custom questions fail | The default Hybrid lesson rejects “How do I build a robot?”, “I want to learn computer vision” and “How do I program in C?” because all four topic counts are zero. The landing page invites related interests. | Offer meaningful recovery for supported language, show recognized topics and connect to neural matching. Verify these questions plus paraphrases and truly unrelated input. |
| F4. The question is dropped on entering Advisor | The image-classification comparison opens an Advisor profile with an empty question. The student must reconstruct their experiment. | Provide an explicit Use this question in Advisor action that fills a draft while retaining the student's coursework. Applying the draft should remain an intentional action. |
| F5. Saved text is credited as completion | Saving the single character “x” marks Advanced completed. The app checks presence, with no feedback about the reasoning. | Ask for a claim, a referenced record and an explanation of the change. Provide a short self-check and feedback tied to visible evidence. Define completion as finishing the exercise. Assess understanding in the pilot. |

The successful scripted example remains useful. With Hybrid selected, changing the sensor question to image classification moves ECE425 from sixth to second and changes the selected-record top-three count from 0 of 1 to 1 of 1. The audit found that the surrounding journey needs the fixes above. [Lesson source](../src/learning_ui.py) · [Probe observations](evidence/final_version_audit_2026-11-13.json)

**The highest-impact design improvement is one continuous experiment from a simple explanation to the actual neural calculation.** The current lesson vectors contain four counts of distinct listed terms. This representation is inspectable, and its limited vocabulary explains the custom-question failures. The Advisor uses pretrained embeddings when configured. Show both representations with clear labels, using the same documents and question wherever possible. Explain why their ranks can differ and keep PCA's approximation visible. [Teaching features](../src/learning_lab.py) · [Advisor inspection](../src/inspector.py)

For reliable self-guided access, a small recorded preset generated by the real embedding model could supply the initial neural example. It would need its model ID, dimensions, source fingerprint and generation date, plus an explicit recorded-preset label. Arbitrary new neural queries would use the configured provider. Keep those availability states understandable. A student should know which representation produced the displayed result.

Move source excerpts and the selected-record explanation into a learner-facing Inspect evidence control. They currently appear after the feature tables and source code inside Developer view. Let the developer control expose the implementation separately. Add a compact “Why did this move?” comparison using the actual matched terms, score components and rank change. A second preset should demonstrate a limitation or tradeoff, giving learners something to evaluate beyond a successful example. [Evidence placement](../src/learning_ui.py)

The Advanced export currently includes the preset name, question, method, expected-record labels, ranks and observation. Add a schema version, stable record IDs, source fingerprint, representation/model identifier and actual scores so a comparison remains interpretable after the catalog changes. A later import/resume control would improve continuity. An account database is optional for this bounded final version because the existing profile download/restore workflow already supports portability. [Current export](../src/learning_ui.py) · [Profile format](../src/profiles.py)

**Fresh network work remains the main responsiveness concern.** Source checks occur before the early plan is published. With AI disabled, the request uses the synchronous route. Enabling AI moves work to a background job, but the first useful plan still waits for source refresh. The current 45-second budget begins after source checks. [Request ordering](../src/controller.py) · [UI dispatch](../app.py)

Historical measurements show the consequence. The November 8 source-only observations were 21.664 seconds with an empty cache, 13.191 seconds with a disk cache in a new process and 0.066 seconds for immediate reuse. These are individual observations. The November 12 browser repeat measured a 683.3 ms median first inspector opening and 321.3 ms reopening across five offline sessions. This audit made additional offline workflow probes. Fresh provider/network measurements remain to be collected for the release. [Source observations](evidence/final_readiness_audit_2026-11-08.json) · [Browser repeat](evidence/midproject_feedback_2026-11-12.json)

Recommended behavior is to build a dated saved-data plan immediately, refresh sources in a bounded background job, then update the result only if it still belongs to the current profile and request. Verified academic status must come from the applicable source checks. Preserve the existing cancellation and superseded-request rules when extending this behavior to preview mode. A user should be able to continue inspecting the available plan while the source and optional model stages report progress.

Proposed performance targets for planning are a first saved-data plan within one second on the documented test machine, immediate visible acknowledgment of network work and median local filter/selection response below 300 ms. Verify these with the same observable boundaries before accepting them. Record repeated cold and warm source/model/browser observations, include failures, and show sample counts and ranges. These targets are team choices for the next iteration.

The catalog has broad descriptive coverage and limited interpreted academic rules. Four CS course conditions have reviewed interpretations. All fifteen ECE conditions in the default advisor and CSC372 remain unreviewed. For the final demo, prioritize the exact official conditions for a small chain such as ECE101, ECE369A, ECE372A and ECE425. Confirm applicable catalog year, alternatives, grades and concurrency where the source specifies them. Keep unresolved conditions visible and pair them with a concrete source-check action. [Reviewed data](../data/reviewed/catalog.json) · [Runtime extension](../data/reviewed/runtime_extension.json)

The 78-course inventory was retrieved November 8 using the published list's January 13, 2027 effective-date filter. The directory UI displays catalog year and retrieval time but omits that effective date. Display all three and keep semester availability tied to the appropriate current source. The final report should describe this as the saved inventory's coverage. [Inventory metadata](../data/catalog/undergraduate_ece_2026_2027.json) · [Directory UI](../src/directory_ui.py)

The original brainstorming also proposed cost/time resource filters, resource completion, a compact local neural baseline, graph-based prerequisite ordering and SQLite. The implementation has explicit learning-stage rules, course progress, JSON portability and hosted pretrained embeddings. Reconcile these design choices in the final report with reasons, tradeoffs and any deferred work. Additional infrastructure has lower priority than the learning flow, reviewed demo data and evaluation. [Original brainstorming](https://chatgpt.com/library?file_id=libfile_3c6228a58634819198a3f8623a9de518&account_id=personal)

**Evaluation and final artifacts are the largest share of the unfinished submission.** All 408 relevance fields in the twelve-question/34-chunk review packet are blank. The sixteen-query historical benchmark is authored development evidence. The new lesson's learner-selected top-three count measures one exercise criterion. The next evaluation should collect explicit reviewer judgments, compare methods on identical archived inputs and identify the reviewer role. Any held-out claim needs questions fixed before tuning. [Review packet](../data/reviews/runtime_v1/review_template.json) · [Review workflow](47_REVIEW_WORKSPACE.md)

Run the planned 3–5 student sessions after the navigation fixes. Include the new lesson sequence and existing advisor tasks. Record whether students can explain an embedding, a rank change, uncertainty about preparation and a source's role. Keep task success, operator help, confusion and failures. The existing protocol is ready to use. [Student pilot](final/STUDENT_PILOT.md)

| Submission item | Available now | Work to finish |
| --- | --- | --- |
| Report | Markdown draft with architecture, equations, historical measurements and limitations | Add final UI figures, actual evaluation, proposal-to-implementation decisions, relevant sample-paper discussion and compiled PDF in the confirmed format. |
| Figures | CI screenshots of the three stages and phone landing | Capture annotated final-revision figures including the actual neural view and before/after result. |
| Slides | No final deck located in the audited repository | Prepare a concise problem, interaction, method, result, limitation and conclusion sequence. |
| Recording | Three-member runbook and transitions | Each member narrates and demonstrates a segment. Capture only app content, exclude names/faces/Zoom, match handoffs, stitch and review the complete export. |
| Evaluation | Reviewer tool, blank packet, pilot protocol and historical comparisons | Collect the planned observations and judgments, then report what they establish. |
| Release | Runnable main, pinned dependencies and passing CI | Freeze the chosen revision, test setup on a teammate's machine, verify grader access and links, then create the release/package. |
| Final requirements | December 11 date and midproject feedback | Confirm D2L's final time, format, durations, filenames and individual/team submission rules. |

A complete final recording should include an actual successful neural request and visual/mathematical inspection. The current runbook makes that segment conditional on availability, so arranging credentials, access and a rehearsed request is an open completion task. Reuse the new lesson sequence for the narrative and make the Advisor transition explicit. Every member should both narrate and demonstrate their portion. [Recording plan](final/DEMO_RUNBOOK.md)

The next changes should follow this order. Priorities reflect the expected effect on the final experience and evidence, using the currently available guidance.

| Priority | Development step | Completion evidence |
| --- | --- | --- |
| P0 | Repair F1–F4 and make supported custom questions recover usefully | Same example, method and draft survive navigation. Advisor receives the chosen question through an explicit action. The reproduced cases pass. |
| P0 | Connect the simple lesson to real neural retrieval and add evidence-based reasoning prompts | A newcomer can compare the same question, explain one rank change and inspect its calculation/source without an operator. |
| P1 | Show a saved-data plan before fresh checks finish in both modes | A controlled slow-source run leaves the interface useful. New profiles reject stale output. Repeated real observations meet the agreed target or identify the remaining delay. |
| P1 | Review the focused ECE demo data and expose effective-date metadata | Every claimed academic condition has applicable evidence and exercised positive, negative and unknown cases. |
| P1 | Execute the relevance review and student pilot | Actual dated forms, observations, summaries and retained failures are available. |
| P1 | Finish report figures, slides and the team recording | Every demonstrated claim matches a visible result and the final artifact passes a complete review. |
| P2 | Improve export provenance, phone layout and developer explanations | Reopening a saved comparison is understandable. Pointer, keyboard and touch interactions are checked. |
| P2 | Simplify setup and current documentation | A short grader quickstart succeeds from a clean checkout, with the expected mode clear. |

The phone screenshot shows a large title and long introduction before the first practice action. Stage navigation is accessible at the top. Reduce the title/hero footprint and place a clear practice action near the introductory summary. Check chart labels, long record titles, visible focus, zoom and touch interactions. The successful Advanced CI path currently submits by keyboard after closing the dropdown, so mouse/touch submission deserves an explicit check during the next UI pass.

The repository has extensive dated development documentation and a long README. Give graders a compact starting route with one tested setup command, mode explanation, demonstration task and links to the current report and evidence. Keep the detailed history reachable from that route. Update the app summary with the new learning pages and make the current readiness page authoritative.

Suggested team ownership is one lead for the learning interface and continuity fixes, one for data/retrieval/evaluation, and one for report/slides/video integration. All three review the final demonstration and record their own segment. These are proposed work assignments for the team to distribute.

| Planned window, MST | Intended outcome |
| --- | --- |
| November 13–17 | Fix continuity and custom input recovery. Establish the simple-to-neural teaching example. |
| November 18–22 | Improve first-plan responsiveness and focused ECE evidence. Prepare evaluation inputs and final-demo access. |
| November 23–29 | Complete reviewer/student sessions and repeated live/cache measurements. Turn results into figures and findings. |
| November 30–December 4 | Resolve observed issues and freeze the feature set. |
| December 5–10 | Finish PDF/slides, record and stitch all members, verify setup/access and package. |
| December 11 | Present and submit under the confirmed course rules. |

The revised planning calculation uses the earlier audit's weights. Application progress is 85%, evaluation/performance 40%, report 65%, presentation/recording 20% and release/delivery 40%. Weighted completion is **65.5%**, rounded to about **65%**. The earlier 90% / 70% assessment credited the three screens as a completed learning path before these continuity and pedagogical gaps were examined. [Current readiness](FINAL_READINESS.md)

The final release should demonstrate a complete student journey, explain the real neural method, show a responsive useful plan, support its academic statements, include observed evaluation results and ship the finished report, slides and private team recording. Closing these acceptance points is the basis for the next readiness increase.
