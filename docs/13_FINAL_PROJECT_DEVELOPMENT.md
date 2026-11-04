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

The copied baseline provides five courses, two learning resources, two career mappings, profile export/import, academic-rule checks, keyword/semantic/hybrid ranking, Gemini generation, source references, PCA and cosine inspection, and request traces. Runtime official-source retrieval is still planned. Adzuna live verification and OpenRouter integration remain unfinished. The source repository's last clean test run passed 80 tests; this copy's initial changes only rename project metadata and update documentation.

Citation membership does not establish claim accuracy. Four ECE academic rules remain unresolved. Learning stages are preparation suggestions, not semester assignments or a complete degree audit.

## Owners and next work

| Owner | Responsibility | First deliverable, November 2–8 |
| --- | --- | --- |
| Jose Salinas Meza | RAG, integration, performance, release | One live catalog-fetch path and a passing pipeline trace |
| Andrew Song | Academic sources, data, rules, reviewed evaluation cases | Pilot source audit with verified fields and review candidates |
| Julio Luzania | Interface, plots, student pilot, documentation, demo | Revised roadmap/inspector and annotated browser captures |

Continue the report's weekly roadmap: live opportunities November 9–15; source revalidation and coverage November 16–22; reviewed retrieval/answer evaluation and a small voluntary pilot November 23–29; fixes and deployment stability November 30–December 6, with a December 4 feature freeze; final artifacts and rehearsal December 7–11.

Prefer official-source retrieval or revalidation when a student submits a request, with visible last-checked dates and a rebuildable cache. If a persistent content database is introduced, it must also refresh automatically on a configurable schedule. Preserve catalog editions and unknown academic conditions when evidence is incomplete.

Use local environment configuration for credentials. Any future OpenRouter integration is limited to free models. Keep evaluation results and live provider checks separate from planned work.
