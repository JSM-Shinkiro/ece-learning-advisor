# Voluntary student usability pilot

Prepared November 8, 2026. This is a protocol and blank observation sheet. **No participant sessions or outcomes have been collected in this file.** The planned sample is 3–5 voluntary students, as in the project testing notes. This pilot measures usability; relevance grading is a separate workflow.

## Operator setup

Use the production application and a recorded Git revision. Follow [the demo setup](DEMO_RUNBOOK.md), select either preview or actual-AI mode for a session, and record it. Each participant starts in a fresh browser session with fictional interests/coursework. Participants may stop at any time. Explain the task sequence without teaching the navigation in advance.

Record an alias rather than a name. Identify project contributors separately; contributor practice sessions do not become independent student results. Repeated sessions by one person remain repeated sessions, not new participants. Model/source cache conditions and network availability can differ; keep those conditions with the observations.

Use neutral prompts such as “What would you try next?” Count every operator hint. Start a task clock after reading the task; stop at completion, abandonment or an external block. These are task-completion times, distinct from server phases and browser-request latency. If AI mode is used, the operator supplies the configured service; participants do not need their own API credentials.

## Participant tasks

| Task | Read to the participant | Observe without supplying the answer |
| --- | --- | --- |
| T1: starting point | “Use an incoming student's fictional background and an embedded-systems interest. Find one practical activity to start with.” | Find profile controls, submit, locate a suggestion, describe its purpose |
| T2: evidence and uncertainty | “Find the source behind one suggestion. Explain the academic/preparation status the app shows.” | Source/detail discovery; interpretation of dated evidence and unknown conditions |
| T3: progress and portability | “For this fictional history, mark a course as currently taking, then completed. Save the profile so it can be used later.” | Explicit submissions, next-step exclusion, completion transition, download discovery |
| T4: change direction | “Switch the fictional student toward AI/machine learning and find how the suggested path changes.” | Goal control, submission, retained progress, ability to explain the changed plan |
| T5: opportunity search | “Search the available employer sources and inspect a relevant listing and its source details if a listing is returned.” | Search/filter discovery, source scope, detail loading and understanding of actual empty/error messages |

Use the same task wording across sessions. Give participants access to the controls without showing a solution first. T2 asks what is shown; it does not establish that the underlying academic interpretation is correct. T5's live outcomes depend on the source/network. A search with no listing is not a completed listing-inspection task: record **Blocked** or **Not completed**, while separately noting whether the person understood the message. Preserve that outcome rather than supplying a fixture listing.

After each task, ask “What, if anything, was confusing?” After T4, ask whether any wording appeared to guarantee enrollment. After T5, ask what sources the participant believes were searched. Record responses in the participant's words; do not infer understanding from a click alone.

## Outcome definitions

| Status | Meaning |
| --- | --- |
| Completed unaided | Participant reaches the task endpoint and explains what was found, without navigation hints |
| Completed with help | Endpoint reached after one or more counted operator hints |
| Not completed | Participant stops, cannot reach the endpoint, or reaches only part of the task |
| Blocked externally | Network/provider/source prevents the endpoint; keep the attempted workflow and message notes |
| Skipped | Task was not attempted; record the reason |

Counts reflect actual sessions only. Preserve failures and blocked tasks in the denominator/report; do not convert them to successful outcomes. Summarize mode and assistance separately. With 3–5 students, report counts and descriptive ranges/medians where meaningful; do not claim population-level effectiveness or significance.

## Unfilled session sheet

Copy this sheet once per real session. Dashes and empty fields below mean **not recorded**, not zero or success.

Participant alias: ______  
Date/time and timezone: ______  
Application revision: ______  
Preview or actual-AI mode: ______  
Device/browser and viewport: ______  
Project contributor? ______  
Source/model cache state and network conditions: ______  
Operator alias: ______

| Task | Status | Elapsed task seconds | Hint count | Confusion, partial result or blocking message |
| --- | --- | --- | --- | --- |
| T1 | — | — | — | — |
| T2 | — | — | — | — |
| T3 | — | — | — | — |
| T4 | — | — | — | — |
| T5 | — | — | — | — |

Participant's explanation of one source/status: ______  
What changed after the new direction: ______  
Whether any wording seemed to guarantee enrollment, and why: ______  
Opportunity listing found? ______; source/message understanding: ______  
Most confusing part, in the participant's words: ______  
Suggested improvement: ______

Optional perceived clarity rating, **1 = not clear, 5 = very clear**: ______  
Optional perceived responsiveness rating, **1 = very slow, 5 = very responsive**: ______  
Additional comments: ______

These ratings describe perception, not correctness or measured request latency. Retain the actual mode, revision and task outcomes with any summary.

## Independent relevance review remains separate

The [reviewer workspace](../47_REVIEW_WORKSPACE.md) loads twelve development questions and 34 saved chunks. A complete form requires 408 explicit 0–3 grades; unchosen grades stay null. Copy a blank form or begin a fresh workspace for each reviewer, declare contributor status, and save actual drafts/exports outside the immutable packet directory. Judge saved excerpts, not a changed live page.

An independent judgment on development questions does not make those questions held out. For a held-out comparison, archive separately authored questions/labels before tuning and score against the exact matching catalog snapshot. Keep the app/query treatment fixed while collecting a given review set. Do not fill missing judgments, infer grades from usability comments or treat contributor/assistant-authored labels as independently collected results.

Add observed findings to a separately dated results file only after sessions occur. Update the report, evidence map and [readiness](../FINAL_READINESS.md) with the actual participant count, modes, task outcomes, assistance and limitations.
