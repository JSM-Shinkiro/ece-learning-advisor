# Published undergraduate ECE catalog

Team P07 · November 8, 2026 MST · Development revision `d93fc8e6b137dab44c9e990b92701031c899216e`.

## Result and scope

The app can browse **all 78 undergraduate ECE courses returned by the official 2026–2027 published course list**, up from 15 saved ECE advisor records. The completed/current-course pickers include these entries. An explicit code question or **Explore … in my roadmap** adds up to three requested catalog courses to the current advisor request. Newly imported courses appear under **Explore requested courses**. Their preparation level, career connection and enrollment conditions remain unreviewed.

| Coverage | Current implementation |
| --- | --- |
| Published undergraduate ECE inventory | 78 courses, including independent study, honors, internships and variable-credit entries |
| Default advisor corpus | Unchanged: 15 ECE + five CSC courses, eight resources, two career records, 34 chunks |
| Additional ECE descriptions reachable on request | 63; each has an offline request-to-context regression case |
| Existing reviewed prerequisite interpretations | Four CS conditions; all ECE conditions and CSC372 remain unknown |
| Career guidance | AI/ML and embedded directions; new inventory entries receive no automatic career mapping or course-sequence claim |
| Graduate and supporting curriculum coverage | 108 non-undergraduate ECE entries excluded; complete mathematics/science/general-education/support inventory remains open |

A published catalog entry does not establish an available section, term offering, degree applicability, credit equivalency or enrollment clearance. Research, special topics and independent study can need individual arrangements. Catalog-wide prerequisite interpretation, broader electrical-engineering career directions and complete degree auditing remain open.

## Data and provenance

The [official catalog course list](https://catalog.arizona.edu/courses) identifies edition 2026–2027 and catalog ID `Xljz5tlVNVzrbyreNRaI`. Its configured effective-date range is **January 13, 2027 through January 13, 2027**. The import follows that published setting rather than substituting the retrieval date. The snapshot was retrieved November 8, 2026 UTC; it is not a statement that every entry is offered in the current semester.

The public list uses a read-only Coursedog search POST. The endpoint, filter shape and date encoding were observed in the catalog's public client modules. Two pages return 100 and 86 entries with a stable total of 186. Filtering the published ECE result by undergraduate career yields 78 entries; the remaining 108 are graduate-level entries. No hidden freeform requisite field is imported as an academic rule.

The [saved inventory](../data/catalog/undergraduate_ece_2026_2027.json) preserves code, seven-digit course identity, official long title, normalized description, credit minimum/maximum, opaque requirement reference, effective start, metadata hashes, page offsets/hashes and retrieval time. It saves no raw administrative/user metadata from the search response. Independent official-page samples for ECE101, ECE413 and variable-credit ECE493 match identity, edition, title, description and credit bounds. These are source cross-checks, not independent academic review of all 78 descriptions or rules.

Run `python scripts/sync_course_directory.py` explicitly to refresh the snapshot and restart the app. The importer validates contiguous pagination, stable total, unique identities, subject/career, publication status, numeric credit bounds and edition metadata before replacing the previous file. UI interactions never run this importer.

## Responsive interaction and trust boundaries

- Search, level filters and pagination run locally in the collection fragment. At most 15 course panels render per page; closed panels omit descriptions and links. Browsing does not call the advisor, provider or external HTTP.
- The process reuses the validated directory snapshot. It does not embed all 78 entries at startup or on each form edit.
- Only explicitly requested codes enter an advisor overlay, at most three additions. Already saved, completed/current and different-edition courses do not become new entries. The original catalog object and archived review inputs remain unchanged.
- Promoted descriptions share the existing maximum of eight course checks. The two program/two resource budgets remain unchanged. More requested additions produce a visible limit message.
- Fixed credits stay numeric. Variable credits retain their published range in the directory and request evidence; no midpoint or fabricated fixed value is used. Unsupported live variable-credit parsing leaves dated saved evidence with a failed-check label.
- Unmapped courses use an explicit `unreviewed` preparation state and a bounded, source-bound exploration statement. They receive neither an inferred prerequisite tree nor a suggested academic sequence from their number.

## Verification

Local verification passes all **1,744 tests**, nine production-readiness checks and dependency consistency. Tests cover every additional ECE code, incomplete/drifting/overlapping/duplicate inventory, different editions, recorded-course exclusion, credit ranges, request budgets, local pagination, profile completion/portability and an actual catalog-to-roadmap action. The production preflight validates the directory together with the unchanged advisor corpus.

The first full local run had three failures because the historical five-course UI fixture also loaded the new directory, changing its discovery statuses and ECE499 coverage. That fixture now explicitly retains its original collection; separate new interaction cases enable the full directory. No archived corpus, question, packet or blank rating was edited. The initial pagination implementation also failed under AppTest's full rerun; callback-based paging now supports both full and fragment reruns.

At the development revision above, [CI run 42531556423](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/42531556423) passes all **1,744 tests and nine runtime checks on each of Linux and Windows**, **29 Chromium gates** (ten student, six reviewer, thirteen controlled AI/browsing), and both five-session preview timing cohorts. The three new catalog browser gates pass on their first hosted run. Exact hosted CI outcomes, source sample hashes, local run outcomes and the eight preserved input hashes are recorded in [the development evidence](evidence/undergraduate_ece_directory_2026-11-08.json). Browser checks include local paging/lazy panels, exact spaced-code variable-credit search at 390 pixels and a controlled-AI catalog-to-roadmap action. Existing preview, reviewer, AI/posting and repeated timing checks remain distinct. Automated checks do not add real-AI quality, participant feedback or independent relevance grades.

## Readiness decision

Rebaseline the app to approximately **85%** and the complete submission to approximately **75%** for the broader undergraduate ECE goal. These are engineering planning judgments, not measured quality, rubric grades or test percentages. The earlier 95% app estimate described the narrower AI/ML-and-embedded prototype and overstated readiness for the broader curriculum goal. This step closes published undergraduate ECE browsing and bounded description access. Prerequisite evidence, broader mappings/supporting courses, genuine evaluation/pilot observations, final-release measurements and final presentation/package remain the consequential gaps.
