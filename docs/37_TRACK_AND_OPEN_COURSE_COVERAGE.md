# Track courses and archived open-course resources

Implemented November 6, 2026 MST in the development repository, following [runtime collection expansion](36_RUNTIME_CATALOG_EXPANSION.md). Historical evaluation inputs, measurements, and submitted midproject artifacts remain unchanged.

The runtime collection now contains **20 courses, eight resources, two career mappings, and 34 evidence chunks**. This meets the lower end of the original 20–30-course/8–12-resource ambition. It does not complete academic-rule coverage or independently validate the recommendations. Initial corpus hash: `bdd87ede10f6c020b1833f4d43653e62207ab372f912bde81691c829f0db13f7`.

## Added coverage

| Course | Official ID | Program section | Preparation label |
| --- | --- | --- | --- |
| ECE352 — Device Electronics | 0121181 | R15487/L30 | Intermediate |
| ECE381A — Introductory Electromagnetics | 0375981 | R15487/L30 | Intermediate |
| CSC372 — Comparative Programming Languages | 0098011 | R15487/L20 | Intermediate |

Exact source IDs, 2026–2027 catalog identity, fixed units, current descriptions, and visible program links were checked before adding paraphrased snapshots to the runtime extension. Topics, direction connections, preparation stages, and activities remain team annotations. No prerequisite interpretation was added. There are now fifteen unresolved ECE conditions plus the unreviewed CSC372 condition; four existing CS interpretations retain their prior evidence and limitations.

Eight program sections are configured across the same two programs. The new sections are Computer Engineering Courses II (`R15487/L20`) and Electrical Engineering Courses I (`R15487/L30`). The former contains fourteen explicit course IDs, only one of which is added as a reviewed runtime snapshot in this step. An inspected CSC337 page was not added. The separate Electrical Engineering Courses II section uses a course-set reference rather than an explicit ID list and remains unsupported by discovery. No course-set expansion or catalog-wide crawler was introduced.

Discovery policy `p07-course-request-priority-v4` adds bounded `section_stages`, valid only for configured sections. New unfamiliar links from Computer Engineering II receive an advanced preparation label; Electrical Engineering I links receive intermediate. If several annotated sections contain the same candidate, the most advanced label wins. Exact reviewed/per-course annotations take precedence, allowing CSC372's reviewed intermediate preparation label. Existing foundation defaults and course order remain covered by tests. These labels never satisfy an enrollment condition or assign a semester.

| Resource | Official source | Published offering | Preparation |
| --- | --- | --- | --- |
| MIT 6.006 — Introduction to Algorithms | [Syllabus](https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/pages/syllabus/) | Spring 2020 | Python programming and discrete mathematics |
| MIT 6.004 — Computation Structures | [Syllabus](https://ocw.mit.edu/courses/6-004-computation-structures-spring-2017/pages/syllabus/) | Spring 2017 | Programming concepts and electrical fundamentals; consult syllabus prerequisites |

Both resources are archived offerings. Checking their currently served pages does not make their teaching terms current or establish Arizona course equivalency, credit, or enrollment availability. Published teaching terms remain separate from catalog years and successful-check dates.

The connector requires an exact allowlisted syllabus URL, document title, visible course-banner title, course number, teaching term, undergraduate level, unique main-content root, and unique Course Description heading. Navigation, hidden content, prerequisite paragraphs, and later syllabus sections cannot supply the description. Wrong offerings, missing/duplicate identities, unsupported layouts, canonical drift, and failed checks retain dated evidence. Conditional cache checks, field provenance, version labels, and failure handling use the existing resource adapter.

## On-use behavior

The source limits remain eight course pages, two program pages, two resources, and three workers. Existing explicit code/phrase priority applies to the added saved courses. MIT names/numbers share the existing resource preference function between checking and context selection. Expected budget omissions now produce one clear resource-limit notice; unsupported identities and actual source failures remain distinct. Strict source-CLI exits still count budget skips as unverified.

```powershell
.\.venv\Scripts\python.exe scripts/check_sources.py --collection runtime --career ai_ml --question "CSC372 with MIT 6.006 and MIT 6.004"
.\.venv\Scripts\python.exe scripts/check_sources.py --collection runtime --career embedded --question "ECE381A with MIT 6.004 and MIT 6.006"
```

## ECE prerequisite investigation

The inspected catalog course objects expose internal enrollment references without structured conditions. Department pages supply useful leads but do not establish matching 2026–2027 interpretations: the [ECE369A page](https://ecse.engineering.arizona.edu/undergrad-programs/courses/ECE369A) identifies 2021–2022 catalog data and a 2022 syllabus update, while [ECE201](https://ecse.engineering.arizona.edu/undergrad-programs/courses/ECE201) reports a 2024 syllabus update. A 2026 site footer does not establish the condition's catalog edition. No department prose was promoted into current verified enrollment approval, and Engineering advanced standing remains distinct from a student's year in school.

## Verification

All **1,305 tests pass**, including 44 new track/open-course cases and the existing 62 Streamlit interactions. New checks cover exact offering identity, visible section boundaries, teaching terms, cache/304/failure dates, course/source provenance, unknown academic results, phrase routing, section-stage precedence, source limits, shared resource/context selection, and consolidated budget notices. Historical core fixtures now describe the added track sections explicitly rather than duplicating foundation IDs into every section. Existing novice defaults still pass. All eight production-only local readiness checks pass, including loopback health and an offline roadmap with external HTTP blocked.

[Dated evidence](evidence/track_coverage_2026-11-06.json) retains these source-only observations:

| Observation | Result |
| --- | --- |
| Initial program/resource inspection | All passed; the program request recovered one initial timeout |
| AI/ML: CSC372, ECE352, both MIT resources | All twelve selected checks passed; three sources recovered initial timeouts; both requested resources appeared verified in context |
| Embedded: ECE381A, both MIT resources | All nine academic checks passed; both MIT checks timed out twice and retained bundled snapshots; the request is recorded as unsuccessful overall |
| One bounded recheck of the failed MIT resources | Both passed; academic pages were not requested again |

These requests used no credentials, embeddings, or generation. Earlier failed observations remain unchanged. The successful recheck does not establish a root cause or permanent availability improvement. Skipped records remain snapshots. No new independent judgments, expanded-corpus quality metric, general accuracy claim, new enrollment approval, or public deployment is claimed.

Next priorities are exact ECE/edition evidence, separately bound review/evaluation of the larger corpus, and a hosted student pilot. Historical baseline scores and the baseline-only reviewer CLI do not measure the expanded collection. No persistent content database was added; scheduled refresh plus on-use checks remain required if one is introduced.
