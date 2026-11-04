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

The baseline provides five courses, two learning resources, two career mappings, profile export/import, academic-rule checks, keyword/semantic/hybrid ranking, Gemini generation, source references, PCA and cosine inspection, and request traces. The development backend checks the relevant configured course and resource pages plus CSC120's reviewed program-requirement section on a submitted roadmap, then adds up to three validated course descriptions from configured foundation sections. It tracks source IDs for fetched fields, validates identity/edition, keeps separate freshness timestamps, handles source/cache failures, and reuses unchanged document embeddings. Prerequisite statements have separate citation chunks; changed or failed checks make the affected academic result unknown. Resource excerpts retain published versions separately from academic catalog years. See [runtime source checks](14_RUNTIME_SOURCES.md), [prerequisite evidence](15_PREREQUISITE_EVIDENCE.md), [bounded discovery](16_COURSE_DISCOVERY.md), and [resource checks](17_RESOURCE_SOURCES.md).

Adzuna live verification and OpenRouter integration remain unfinished. The original source repository passed 80 tests before this development work; historical measurements retain their dates and scope.

Citation membership does not establish claim accuracy. The starter collection's four unresolved ECE conditions and all discovered-course conditions stay unknown. Learning stages are preparation suggestions, not semester assignments or a complete degree audit.

## Backend priorities

Work across the app as needed, with backend correctness and source handling first. Individual ownership does not constrain the development order.

| Priority | Deliverable | Status |
| --- | --- | --- |
| 1 | Official-source checks in the submitted roadmap pipeline | Configured courses and bounded foundation-course discovery implemented; full-catalog coverage remains |
| 2 | More academic-rule evidence and catalog-edition coverage | CSC120 provenance and live revalidation implemented; four ECE conditions and other editions remain unresolved |
| 3 | Broader course/resource coverage with source provenance | Bounded foundation discovery and both configured resource checks implemented; wider coverage remains |
| 4 | Actual opportunity results and failure handling | Adapter exists; live Adzuna verification remains |
| 5 | Retrieval/claim evaluation, performance, and deployment | Frozen development suite and offline baseline implemented; semantic/generation review and independent evaluation remain |

The current automated suite passes 316 tests, including 16 Streamlit interactions. The [offline development baseline](18_REVIEWED_EVALUATION.md) covers 16 fully judged queries, 18 roadmap scenarios, and 16 authored answer probes. Keyword Recall@5 is 0.8229 across the small reference set; all roadmap expectations pass. Nine authored unsupported/contradicted claims still pass the current citation checks. These are assistant-authored development references, not independent student or generated-model results.

The earlier exploring-profile discovery check added CSC110, ECE201, and ECE220. Later resource checks received HTTP 304 from both resource hosts on repeat. These public-source observations keep their original dates and scope. The next backend unit is factual-answer validation, followed by opt-in semantic/hybrid comparison and review of actual generated answers. Keep paraphrase/coverage-guard behavior under review, and do not translate older department descriptions or Engineering advanced-standing language into current enrollment approval.

Continue the report's weekly roadmap: live opportunities November 9–15; source revalidation and coverage November 16–22; reviewed retrieval/answer evaluation and a small voluntary pilot November 23–29; fixes and deployment stability November 30–December 6, with a December 4 feature freeze; final artifacts and rehearsal December 7–11.

Prefer official-source retrieval or revalidation when a student submits a request, with visible last-checked dates and a rebuildable cache. If a persistent content database is introduced, it must also refresh automatically on a configurable schedule. Preserve catalog editions and unknown academic conditions when evidence is incomplete.

Use local environment configuration for credentials. Any future OpenRouter integration is limited to free models. Keep evaluation results and live provider checks separate from planned work.
