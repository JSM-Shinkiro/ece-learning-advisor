# CS foundation coverage

Later November 4: [requested-course discovery](25_REQUESTED_COURSE_DISCOVERY.md) now implements literal course-code priority. The source-order defaults, counts, and source-only observations below describe this earlier coverage unit.

Implemented and checked November 4, 2026. Runtime discovery now includes CSC144 and CSC210 with explicitly reviewed, source-bound conditions. The saved five-course corpus, frozen evaluation references, earlier measurements, and submitted midproject deliverables remain unchanged.

## Source and interpretation

The [2026–2027 Computer Science BS requirements](https://catalog.arizona.edu/programs/COSCBS/program-requirements-a1nCj) provide explicit prior-coursework statements in the same visible requirements tree already used for CSC110 and CSC120. The individual course pages confirm identity, units, description, and enrollment reference. Opaque references are compared as identities, not decoded into prerequisites.

| Course | Official course identity | Program section | Enrollment reference | Stored condition |
| --- | --- | --- | --- | --- |
| [CSC144](https://catalog.arizona.edu/courses/0420001) | `0420001` | `R1299/L50` | `018647` | Introductory programming alternative with minimum grade C, AND a mathematics alternative |
| [CSC210](https://catalog.arizona.edu/courses/0393711) | `0393711` | `R1299/L70` | `017084` | Prior CSC120 completion with minimum grade C |

CSC144's programming branch accepts CSC110, ECE101, ECE175, or ISTA130 with a confirmed grade of C or higher. Its mathematics branch preserves the alternatives: unverified appropriate placement, MATH112 with minimum grade C, or completion of MATH113, MATH116, MATH120R, MATH122A, MATH122B, or MATH125. The local statement does not give the latter six a minimum letter grade; this interpretation does not invent one. It evaluates this stored coursework condition, not all university/program policies or complete eligibility. The separate degree-credit restriction in that section remains source text rather than an implemented degree audit.

Placement stays unknown. Senior standing, a generic consent label, or a missing mathematics course cannot establish placement. An unfulfilled programming branch can make the AND unsatisfied even while placement remains unknown. Missing grades or pass-only grades cannot establish a C threshold. Concurrent enrollment does not satisfy a prior-completion requirement. CSC210 does not acquire unlisted equivalencies, consent, or concurrency alternatives.

Each interpretation is bound to the exact course ID/code, edition, enrollment reference, program/source/section, normalized statement hash, rule-tree hash, and proof ID in `data/connectors/course_discovery.json`. The implementation assistant reviewed these functional interpretations against fetched official evidence; there is no independent advisor approval. Fingerprints prove consistency with that reviewed configuration, not general semantic correctness.

The four ECE conditions remain unknown. Current ECE course metadata continues to expose enrollment references without enough edition-bound wording to verify them. Department guidance or an older degree plan does not silently become the current catalog rule.

## Runtime scope

The CS discovery plan now selects `R1299/L30`, `R1299/L50`, and `R1299/L70`; CSC120's existing proof remains in `R1299/L40`. One program download supplies all selected sections. The ECE plan retains `R17348/L320`. All course descriptions are fetched during the submitted request, with existing identity, edition, fixed-unit, HTTPS, size, and timeout validation.

The request limits remain three new courses, eight total course downloads, two program sources, and three workers. Candidate order remains configuration/source order. Consequently AI/ML and exploring prioritize CSC110, CSC144, and CSC210 under the current cap; they may leave ECE foundation candidates unfetched. Embedded requests retain the ECE foundation section. This changes which bounded discoveries are available and does not establish catalog completeness. Balancing programs or choosing candidates from a specific question remains open work.

CSC144 is annotated as a foundation learning activity and CSC210 as intermediate. `ReviewedDiscoveryRule.study_stage` is optional and application-owned. It applies only to matching course identity/code/edition, separately from academic satisfaction. A changed enrollment reference leaves the academic condition unreviewed without relabeling CSC210 as introductory. These annotations are preparation suggestions, not semester placement.

Descriptions and prerequisite proofs stay in separate evidence chunks and travel together under the context budget. Changed/missing wording, mismatched identities, failed course checks, or stale evidence cannot approve a condition. A missing description has no fabricated recommendation. Source checks, proof fingerprints, and academic results remain inspectable in the roadmap, picker, and request trace.

The selected-section set is part of the program cache key, so earlier single-section discovery caches cannot masquerade as this expanded selection. Program schema 3, course schema 2, and resource schema 1 remain unchanged. Explicit offline mode still uses the saved collection. No permanent database, recurring source job, or new model call was introduced.

## Verification

The complete suite passes **639 tests**, including **51 CS coverage cases** and **30 Streamlit interactions**. New controlled cases cover each explicit programming/math alternative, grades, unknown placement, prior completion, identity/reference mismatches, changed/missing/hidden statements, separate citations and atomic context, stages, conditional cache reuse, stale course failures, shared request budgets, and the two new UI paths.

The [dated real-source evidence](evidence/cs_foundation_checks_2026-11-04.json) records one source-only refresh scoped to the CS program, without resources, opportunities, embeddings, or generation. It verified six course descriptions and one program page in about 7.4 seconds; all three discovered conditions and CSC120's existing proof were verified. Five controlled histories were then evaluated locally against that same captured catalog:

| History | CSC144 | CSC210 |
| --- | --- | --- |
| ECE101, MATH112, CSC120 all grade B | Satisfied | Satisfied |
| Missing ECE101/CSC120 grades; MATH112 grade B | Unknown | Unknown |
| ECE101/CSC120 grade D; MATH112 grade B | Unsatisfied | Unsatisfied |
| ECE101/CSC120 grade B; no mathematics record | Unknown placement alternative | Satisfied |
| ECE101/MATH112 grade B; CSC120 concurrent only | Satisfied | Unsatisfied |

All five expected outcomes passed. Those history variations did not make new source requests; they test rule behavior against captured current evidence, not repeated live requests or model accuracy. The evidence retains source checks, implementation hashes, proof identities, controlled histories, and initial research failures. The first metadata probes timed out for CSC144, CSC210, and ECE101. One bounded metadata recheck verified each new CS identity, and the later full scoped refresh verified ECE101 as well. These observations are not an uptime or latency benchmark.

Run controlled checks and the normal public-source path with:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/check_sources.py --career ai_ml
```

The CLI exercises the normal configured programs/resources and validates source status with an empty completion history. It does not imply that this history satisfies prerequisites. Its scope is broader than the isolated evidence run above. Frozen retrieval metrics remain historical development measurements; no new retrieval-quality claim is made from these added courses.

Next, improve discovery allocation for specific course questions, seek edition-bound ECE evidence, and obtain independent review of source interpretations and student selections. Additional catalog editions and complete degree/enrollment audits remain outside the implemented scope.
