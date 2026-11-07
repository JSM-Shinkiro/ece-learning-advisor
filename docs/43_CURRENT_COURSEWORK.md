# Current coursework and successful completion

Implemented November 7, 2026 MST in the development repository. A restored profile could already contain `current_enrollment`, but the form could not edit it and the roadmap could recommend those courses again. The app now lets students record current coursework, keeps it out of next-step recommendations, and moves it to completed coursework after successful completion.

## Student workflow

1. Select courses under **Currently taking (optional)**. Use **Other current course codes** under Optional details for courses outside the loaded collection.
2. Select **Update my roadmap**. The submitted profile records those courses separately from successful completions. Ordinary form edits do not request a new plan.
3. The roadmap lists current courses and offers **Mark completed** beside each one. That action moves the course to completed coursework and refreshes the plan.
4. Add any required grade under Optional details. Marking a course completed does not invent a grade; a grade-dependent prerequisite remains unknown until the grade is supplied.

For example, taking ECE101 keeps it out of the next-step cards. It does not satisfy CSC120's reviewed prior-course/grade condition. After recording successful ECE101 completion, the missing grade still leaves that condition unknown; entering B satisfies that coursework branch in the reviewed snapshot. The result retains its existing source/edition limitations.

Current courses survive JSON export/import, career changes, and other profile edits. Removing a current course through the form makes it available for subsequent suggestions again. A current course outside the collection remains a recorded code; it does not create a source URL or grant credit/equivalency.

## Academic and recommendation behavior

`StudentProfile` retains schema version 1 and the existing `current_enrollment` field. Current codes use the same normalized course-code format as completed coursework, with at most 100 entries. Duplicate codes and a course listed in both states are rejected. An older profile without the field still loads with an empty list; an ambiguous legacy profile needs its course status corrected before it can be restored. Retake history is outside this two-state workflow.

Course selection excludes both completed and current courses across keyword, semantic, hybrid, beginner, experienced, exploring, and explicit-focus paths. Current-course descriptions can remain supporting evidence for another course. The provider receives the submitted current-course list, but current courses are excluded from allowed recommendation IDs and application-owned explanation statements.

The existing academic evaluator remains authoritative. Current enrollment can satisfy only a rule explicitly allowing concurrent study. It does not substitute for prior completion, a minimum grade, math placement, permission, or Engineering Advanced Standing. Current programming study alone does not establish completed programming foundations. All fifteen ECE conditions and CSC372 remain unknown.

Completion actions normalize the code, remove it from current enrollment, preserve other profile fields, clear previous roadmap/opportunity results, and reset visible widgets before refresh. Invalid form submissions or restores retain the previous valid profile and results.

## Bounded source selection

Discovery policy advances to `p07-course-request-priority-v5`. Default discovery skips known course-ID bindings recorded as currently taking, preserving download slots for other courses. An explicit code or reviewed phrase can still request a current course's descriptive source. Its discovery status remains `added`/`stale_added`/`in_collection` as appropriate, with a separate `coursework_status: in_progress` label. Discovery alone does not make that course a next-step recommendation.

The inspector shows current-course omissions alongside completed-course omissions. Saved-course check selection advances to `p07-saved-course-checks-v2`: explicit requests and reviewed-rule evidence retain priority, while current/completed records follow other tied candidates. The request trace records current enrollment; personal course state is not written into public source caches. Limits remain eight course pages, two program pages, two resource pages, and at most three new descriptions.

## Verification

The local Python 3.12.14 suite passes **1,473 tests**, including **35 new cases**: 28 backend cases and seven Streamlit interactions. There are now **69 Streamlit interactions overall**. All nine runtime readiness checks pass, including loopback server liveness and an offline preview roadmap with external HTTP blocked.

Coverage includes normalized and invalid imports, legacy profile defaults, conflicting states, current-to-completed transitions, retained unknown grades, explicit concurrent conditions, all retrieval modes with a controlled provider, exploring/beginner paths, retained dependency evidence, source budgets, explicit current-course descriptions, form submission, widget restoration, invalid-form recovery, and inspector output.

Two pre-change controls fail: a current ECE101 is recommended again, and a course can occupy both profile states. The first full implementation check also exposes a preserved behavior requirement: explicit current-course questions must still receive descriptive discovery. That path is retained before final verification. Earlier evidence and failures are not rewritten.

[Dated evidence](evidence/current_coursework_2026-11-07.json) records two controlled student profiles using actual public sources:

| Observation | Result |
| --- | --- |
| Expanded runtime collection; ECE101/ECE201/ECE220/ECE274A current; question about ECE310, Pico, and MIT 6.004 | Zero current-course recommendations; all eleven selected checks updated; ten additional checks remained budget skips/snapshots |
| Baseline collection; ECE201/MATH129 current; explicit ECE201 question | ECE201 description discovered with `in_progress` metadata; excluded from allowed recommendations; all eight source checks updated |

These requests used no credentials or real model calls. They establish source-selection and coursework behavior for the recorded inputs. They do not supply independent relevance grades, a student-learning result, or public hosting. Frozen/runtime data and all four files in the prepared blank reviewer bundle retain their original bytes. No dependency is added.

The prerequisite investigation also rechecked [ECE101's current catalog page](https://catalog.arizona.edu/courses/0432351): its public metadata identifies the 2026–2027 course and still supplies enrollment-reference `019404` without a resolved condition. The [department page](https://ecse.engineering.arizona.edu/undergrad-programs/courses/ECE101) has a 2024 syllabus update; that does not establish an exact 2026–2027 interpretation. A direct fetch of the planning PDF failed and was not promoted into rule evidence. No new ECE interpretation is claimed.

To reproduce local controls:

```bash
python -m pytest -q tests/test_current_coursework.py tests/test_current_coursework_app.py
python scripts/check_deployment.py --smoke
```

The hosted workflow linked from the README records Linux/Windows results by implementation revision. Remote browser/WebSocket validation, a selected public host, genuine reviewer grades, and exact ECE/edition evidence remain the next priorities.
