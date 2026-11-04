# ECE Learning Advisor — Final Project Development

Team P07 · November 3, 2026 · Final presentation and submission: December 11.

## Repositories and baseline

| Purpose | Repository or revision |
| --- | --- |
| Midproject repository supplied with the package | `JSM-Shinkiro/ai-degree-planner` |
| Exact copied baseline | `3fdbf78079834adb4b1cf73dd4bffd74b2fe4be9` |
| Preserved file snapshot in this GitHub repository | Branch `midproject-2026-11-01` |
| Continued implementation | `JSM-Shinkiro/ece-learning-advisor` |
| App and project name | ECE Learning Advisor |
| Technical report title | ECE Learning Advisor: An Inspectable RAG System |

The GitHub development repository starts from an imported file snapshot. The complete original Git history and the `midproject-2026-11-01` tag remain in the saved `ECE_Learning_Advisor_Development.zip` bundle. The snapshot branch has its own commit IDs; its files match source commit `3fdbf78079834adb4b1cf73dd4bffd74b2fe4be9`. Do not push development changes, rename files, or change the default branch in the midproject repository. Keep the packaged midproject report, figures, links, and video as the historical deliverables. Prepare final-report revisions separately.

The snapshot branch preserves the copied midproject files; it does not assert that a later final-project feature was implemented for midterm. Earlier verification records retain their actual dates and results.

## Current implementation

The baseline provides five courses, two learning resources, two career mappings, profile export/import, academic-rule checks, keyword/semantic/hybrid ranking, Gemini generation, source references, PCA and cosine inspection, and request traces. The development backend checks the relevant configured official course pages and CSC120's reviewed program-requirement section on a submitted roadmap, then adds up to three validated course descriptions from configured foundation sections. It tracks source IDs for fetched fields, validates identity/edition, keeps separate freshness timestamps, handles source/cache failures, and reuses unchanged document embeddings. Prerequisite statements have separate citation chunks; changed or failed checks make the affected academic result unknown. Resources still use dated snapshots. See [runtime source checks](14_RUNTIME_SOURCES.md), [prerequisite evidence](15_PREREQUISITE_EVIDENCE.md), and [bounded discovery](16_COURSE_DISCOVERY.md).

Adzuna live verification and OpenRouter integration remain unfinished. The original source repository passed 80 tests before this development work; historical measurements retain their dates and scope.

Citation membership does not establish claim accuracy. Four ECE academic rules remain unresolved. Learning stages are preparation suggestions, not semester assignments or a complete degree audit.

## Backend priorities

Work across the app as needed, with backend correctness and source handling first. Individual ownership does not constrain the development order.

| Priority | Deliverable | Status |
| --- | --- | --- |
| 1 | Official-source checks in the submitted roadmap pipeline | Configured courses and bounded foundation-course discovery implemented; full-catalog coverage remains |
| 2 | More academic-rule evidence and catalog-edition coverage | CSC120 provenance and live revalidation implemented; four ECE conditions and other editions remain unresolved |
| 3 | Broader course/resource coverage with source provenance | Up to three linked foundation courses per request implemented; resource-page checks are next |
| 4 | Actual opportunity results and failure handling | Adapter exists; live Adzuna verification remains |
| 5 | Retrieval/claim evaluation, performance, and deployment | Reviewed cases and repeated measurements remain planned |

The current suite passes 212 tests, including 15 Streamlit interactions. The real exploring-profile discovery check added CSC110, ECE201, and ECE220; a final CLI check verified internal course IDs for all eight selected course pages. These checks made no model calls and are not a latency benchmark. Earlier prerequisite observations retain their partial failure and later success. The next backend unit is resource-page revalidation, followed by reviewed retrieval and claim-support cases. Do not translate older department descriptions or Engineering advanced-standing language into current enrollment approval.

Continue the report's weekly roadmap: live opportunities November 9–15; source revalidation and coverage November 16–22; reviewed retrieval/answer evaluation and a small voluntary pilot November 23–29; fixes and deployment stability November 30–December 6, with a December 4 feature freeze; final artifacts and rehearsal December 7–11.

Prefer official-source retrieval or revalidation when a student submits a request, with visible last-checked dates and a rebuildable cache. If a persistent content database is introduced, it must also refresh automatically on a configurable schedule. Preserve catalog editions and unknown academic conditions when evidence is incomplete.

Use local environment configuration for credentials. Any future OpenRouter integration is limited to free models. Keep evaluation results and live provider checks separate from planned work.
