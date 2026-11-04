# Reviewed conditions for discovered courses

Later November 4: [CS foundation coverage](24_CS_FOUNDATION_COVERAGE.md) extends this mechanism to CSC144 and CSC210. The first CSC110 unit's counts, conditions, and public observations below retain their original scope.

Implemented November 4, 2026, in the development repository. The frozen evaluation collection, earlier measurements, and submitted midproject artifacts remain unchanged.

Runtime discovery can now attach an explicitly reviewed academic condition to a newly fetched course. The first supported discovery condition is CSC110's mathematics requirement in the [2026–2027 Computer Science BS program](https://catalog.arizona.edu/programs/COSCBS/program-requirements-a1nCj), visible section `R1299/L30`. This extends CSC120's existing reviewed condition. The four ECE conditions remain unresolved.

## Reviewed scope

The program describes mathematics placement or MATH112 completion with minimum grade C. The backend preserves the OR:

- A recorded MATH112 grade of C or higher can satisfy the coursework branch.
- The placement branch remains `unknown`; the app has no verified placement score or threshold.

A lower or missing grade, absent coursework, complete history, concurrent enrollment, Junior/Senior standing, or an arbitrary consent label cannot establish placement. With that alternative unresolved, an unsatisfied coursework branch leaves the OR result unknown. This checks one stored condition, not complete enrollment eligibility. The section's separate restriction on counting introductory alternatives toward the degree remains source text; it is not interpreted as a degree audit.

The [reviewed configuration](../data/connectors/course_discovery.json) binds the interpretation to:

| Identity | Required binding |
| --- | --- |
| Course | CSC110, linked course ID `0393681` |
| Edition | 2026–2027 |
| Enrollment reference | `017080`, matched as an opaque identifier rather than decoded |
| Program/section | `catalog:CS_foundations`, COSCBS, `R1299/L30` |
| Interpretation | Full rule-tree fingerprint and cited proof ID |
| Reviewed wording | Normalized statement fingerprint and review timestamp |

The implementation assistant reviewed these bindings against fetched official sources. This is not instructor/advisor approval. Hashes establish consistency with reviewed data, not the correctness of an arbitrary interpretation.

## Runtime and parser boundaries

The configured program download supplies both existing rule evidence and bounded course links. Optional condition wording comes from the same visible sections supplying those links. After validating a discovered course, the backend attaches only an exact, pre-reviewed manifest entry. A link cannot create a new interpretation.

Course ID/code, enrollment reference, edition, source/program/section, and explicit course-list membership must match. Different identities or enrollment references remain unreviewed. Changed or absent wording leaves the academic result unknown. A failed course-description check cannot be overridden by fresh program evidence.

The course overview and prerequisite proof have separate source-linked chunks and remain atomic under context limits. A condition can reference MATH112 without adding its description to the collection. The explanation contract preserves the limitation that recorded satisfaction is not full enrollment eligibility.

Production prerequisite checks now resolve unique sections through the primary program's visible requirements tree, including CSC120's existing proof. Hidden groups and unrelated metadata cannot supply a missing visible statement or replace its wording. Duplicate/malformed sections fail verification. Missing discovery-condition text does not erase validated descriptive course discovery.

Program caches advance to schema **3**, storing optional discovery statements beside course-ID lists. Existing schema-2 program caches rebuild on the next source check. Reads validate identities, edition, exact selected sections, permitted statement keys, hashes, and timestamp ordering. Course-cache schema 2 and resource-cache schema 1 remain as before.

Conditional responses reuse only validated schema-3 data. Failed checks preserve dated reference material while affected academic conditions remain unknown. Explicit offline use can evaluate a dated reviewed snapshot with its limitation. The eight-course/two-program budgets still apply; no extra program URL, worker, permanent database, or scheduled job was added.

Source traces include discovered-rule status, proof IDs, interpretation hashes, and reviewed-statement hashes. Course checks expose aggregate rule-verification status, so a successfully fetched description cannot hide an unavailable academic proof from the source-check CLI.

## Verification

The full pinned suite passes **482 tests**, including **37 discovered-rule cases** and **20 Streamlit interactions**. New cases cover grades/placement, proof binding, exact course/enrollment identity, missing/changed/hidden text, outages, unsupported editions, cache migration and alteration, conditional responses, separate citations, atomic context budgets, controlled generation, trace fingerprints, and UI rendering.

The [public-source evidence](evidence/discovered_rule_checks_2026-11-04.json) uses controlled MATH112 histories with real official-source requests, only the COSCBS discovery plan, and no resource checks. Its final two observations use the strict visible-section parser: a grade-B history satisfies the verified coursework condition; a missing grade leaves the academic result unknown despite verified sources. Earlier observations retain their own implementation hashes. None made embedding, generation, or opportunity-provider requests. This is not a full-source coverage or latency benchmark.

The saved-corpus evaluation remains unchanged: 18 roadmap expectations pass; raw Keyword Recall@5 is 0.8229 and expanded-query Recall@5 is 0.9479. Runtime discovery is tested separately from frozen relevance labels.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/check_sources.py --career ai_ml
```

The source checker uses the normal configured discovery/resource path. Success verifies source/interpretation checks, not that a student's academic result is satisfied. The grade-specific evidence above uses the scoped COSCBS path documented in its report.

## Remaining coverage

ECE101, ECE369A, ECE372A, and ECE425 remain unknown. The checked [ECE425 catalog entry](https://catalog.arizona.edu/courses/0435981/general-aoYks) exposes an enrollment identifier; [department guidance](https://ecse.engineering.arizona.edu/undergrad-programs/courses/ECE425) supplies prose without a matching catalog-edition binding. These sources do not justify automatically verifying the ECE conditions or treating ordinary standing as Engineering advanced standing.

Other discovered courses remain unreviewed until similarly exact evidence is available. Wider official evidence, more catalog editions, real provider verification with local credentials, independent selection review, and live opportunities remain open.

Later November 4: [current Gemini verification](22_CURRENT_GEMINI_VERIFICATION.md) now includes an actual generation request after this scoped CSC110 source refresh. It selected the expected record and qualified stored-condition statement. Independent academic/selection review and wider source coverage remain open; the source-only observations above retain their original scope.
