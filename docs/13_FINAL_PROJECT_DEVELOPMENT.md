# ECE Learning Advisor — Final Project Development

Team P07 · Updated November 4, 2026 · Final presentation and submission: December 11.

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

[Live opportunities](23_LIVE_OPPORTUNITIES.md) now check two configured public employer boards on an explicit search, with validated source links, separate provider dates, local title/location filters, and visible failures. This path uses no credentials or model calls. Adzuna live verification and OpenRouter integration remain unfinished. The original source repository passed 80 tests before this development work; historical measurements retain their dates and scope.

Citation membership does not establish claim accuracy. Production now limits the provider to [selecting application-owned statements](19_GROUNDED_EXPLANATIONS.md), with exact wording, type, citation, ownership, and context validation. It cannot insert arbitrary prose by calling a fact a recommendation. The four unresolved ECE conditions stay unknown. [Reviewed discovery](21_DISCOVERED_COURSE_RULES.md) binds CSC110's mathematics condition to exact current source/course identities; the [CS expansion](24_CS_FOUNDATION_COVERAGE.md) adds CSC144 and CSC210 conditions. Placement branches remain unknown and other discovered conditions remain unreviewed. Learning stages are preparation suggestions, not semester assignments or a complete degree audit.

The [query-interpretation follow-up](20_QUERY_INTERPRETATION.md) adds bounded domain aliases shared by coverage gates and retrieval. Specific questions can retain a directly relevant course without losing novice foundations or changing academic results. Unsupported requests skip source requests and provider initialization. Added search terms and question preferences are inspectable.

[Requested-course discovery](25_REQUESTED_COURSE_DISCOVERY.md) now prioritizes explicit course-code mentions before choosing which three new descriptions to download. It uses reviewed code/ID routing only within freshly verified selected sections, validates the downloaded identity, and exposes final outcomes in the inspector. Remaining slots keep source order; no catalog-wide search or new academic interpretation is implied.

## Backend priorities

Work across the app as needed, with backend correctness and source handling first. Individual ownership does not constrain the development order.

| Priority | Deliverable | Status |
| --- | --- | --- |
| 1 | Official-source checks in the submitted roadmap pipeline | Configured courses and bounded foundation-course discovery implemented; full-catalog coverage remains |
| 2 | More academic-rule evidence and catalog-edition coverage | CSC120 provenance plus bound CSC110/CSC144/CSC210 discovery conditions implemented; four ECE conditions, placement verification, and other editions remain unresolved |
| 3 | Broader course/resource coverage with source provenance | Four discovery sections, explicit course-code priority, and both resource checks implemented; broader discovery and resource availability remain |
| 4 | Actual opportunity results and failure handling | Public Samsara/Nuro boards verified; explicit filters, recent-result reuse, and partial/all-source failures implemented; wider coverage and live Adzuna remain |
| 5 | Retrieval/claim evaluation, performance, and deployment | Frozen baseline, bounded explanations, live selections, and real embedding comparison implemented; broader independent evaluation and deployment remain |

The current automated suite passes 678 tests, including 36 discovery-priority cases, 51 CS coverage cases, 96 opportunity cases, and 33 Streamlit interactions. The [offline development baseline](18_REVIEWED_EVALUATION.md) covers 16 fully judged queries, 18 roadmap scenarios, and 16 authored answer probes. Raw-query Keyword Recall@5 remains 0.8229; explicitly expanded queries reach 0.9479 on those same references. This is development tuning after known misses, not held-out validation. All roadmap expectations pass. The earlier checker still admits the same nine authored unsupported/contradicted claims for comparison. The [explanation follow-up](19_GROUNDED_EXPLANATIONS.md) admits zero unsupported reviewed claims and accepts 82/82 canonical statement controls. It also rejects true unlisted paraphrases: this validates a bounded contract, not general entailment or live model accuracy. References remain assistant-authored, without independent student review.

The earlier exploring-profile discovery check added CSC110, ECE201, and ECE220. Later resource checks received HTTP 304 from both resource hosts on repeat. These public-source observations keep their original dates and scope. The user has now authorized a supplied credential for development, and the [current Gemini checks](22_CURRENT_GEMINI_VERIFICATION.md) pass all seven integration expectations with the new format. Six actual answers selected the expected focus records; the seventh case is the application coverage guard. The credential was used only in transient process memory and is not saved in repository files or evidence. Next, broaden unresolved ECE/edition evidence and course coverage, obtain independent selection/paraphrase review, expand opportunity coverage, and prepare deployment. Do not translate older department descriptions or Engineering advanced-standing language into current enrollment approval.

The later November 4 academic-rule unit verifies CSC110's source-bound math condition during discovery and preserves unknown placement. Production checks now take prerequisite wording from unique visible program sections. Program caches advance to schema 3 and rebuild older entries. Scoped real-source observations confirm a grade-B coursework branch as satisfied and a missing grade as unknown, without any model calls. Broader ECE/edition coverage remains open.

The subsequent real-embedding comparison reuses the actual 10 × 768 Gemini document index and makes 16 query-embedding calls, with no generation or source refresh in that evaluation. On the same expanded development references, semantic/hybrid Recall@5 is 1.0 versus keyword 0.9479. These small assistant-authored, development-tuned references do not establish held-out quality. Actual provider integration is now verified; independent accuracy evaluation remains open. The application code and 482-test result are unchanged by this verification unit.

The following opportunity unit adds public Greenhouse metadata checks for Samsara and Nuro. Five of six initial live filter cases succeeded; the initial AI all-location request failed without per-source diagnostics. That failure is retained. After adding safe source-status reporting, one bounded recheck succeeded with 41 AI matches; the other cases observed 11 embedded matches, one AI internship, two embedded internships, zero literal Tucson matches, and 14 AI listings updated within seven days. These are dated observations from two employers, not market coverage or qualification measurements. Fresh requests are the default; explicit matching-result reuse is limited to 20 minutes and retains its original timestamp. No persistent job database or scheduled refresh was introduced.

The next coverage unit adds exact CSC144 and CSC210 conditions from the 2026–2027 CS program, without guessing the unresolved ECE requirements. A real scoped refresh verifies the CS program, three configured course descriptions, and three discoveries (CSC110/CSC144/CSC210). Five controlled histories evaluated against that one captured catalog produce the expected grade, placement, and prior-completion outcomes. No model calls were made. The unchanged discovery cap means AI/ML and exploring now prioritize these three CS courses; embedded requests retain the ECE foundation section. More balanced or question-aware candidate allocation remains future work. Frozen evaluation records and earlier measurements remain unchanged.

The following discovery-priority unit implements the explicit-code allocation step. A real normal source-check request discovered ECE274A, ECE201, and ECE220 in the requested order while verifying all six course pages and both programs. Both resource checks timed out and used labeled bundled fallbacks; one bounded recheck of those two resources also timed out. The overall source-check exit remains unsuccessful in the evidence, while academic-source selection passed. No timeout result was relabeled as success. Next, broaden candidate routing beyond literal codes, review deployment/network reliability, obtain independent selection/source-interpretation review, and seek edition-bound ECE evidence.

Continue the report's weekly roadmap: live opportunities November 9–15; source revalidation and coverage November 16–22; reviewed retrieval/answer evaluation and a small voluntary pilot November 23–29; fixes and deployment stability November 30–December 6, with a December 4 feature freeze; final artifacts and rehearsal December 7–11.

Prefer official-source retrieval or revalidation when a student submits a request, with visible last-checked dates and a rebuildable cache. If a persistent content database is introduced, it must also refresh automatically on a configurable schedule. Preserve catalog editions and unknown academic conditions when evidence is incomplete.

Use local environment configuration for credentials. Any future OpenRouter integration is limited to free models. Keep evaluation results and live provider checks separate from planned work.
