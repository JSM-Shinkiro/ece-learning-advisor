# Bounded official-course discovery

Later November 4: [CS foundation coverage](24_CS_FOUNDATION_COVERAGE.md) adds two CS sections and bound CSC144/CSC210 conditions. Under the unchanged three-course cap, AI/ML and exploring now prioritize CSC110/CSC144/CSC210. The original two-section milestone and observations below retain their earlier scope.

November 4 follow-up: [reviewed discovered-course conditions](21_DISCOVERED_COURSE_RULES.md) add CSC110's exact math condition, retain unknown placement, and advance program caches to schema 3. The original discovery milestone and schema-2 verification below retain their November 3 scope. Other discovered conditions remain unreviewed.

Implemented November 3, 2026, in the development repository. This extends [prerequisite-source revalidation](15_PREREQUISITE_EVIDENCE.md). The submitted repository and midproject artifacts remain unchanged.

**Follow-up, November 3:** [Resource-source checks](17_RESOURCE_SOURCES.md) adds live introductory excerpts and published versions for both configured resources, with prompt version `p07-v6-resource-sources`. The discovery milestone and measurements below retain their original scope and results.

## Current coverage

Submitted roadmaps can add up to three validated course descriptions to the five-course starter collection. The connector reads explicit course IDs from two configured foundation sections, then fetches those official course pages. The bundled course records remain unchanged.

| Program source | Section | Directions | Configured learning stage |
| --- | --- | --- | --- |
| [Computer Science BS](https://catalog.arizona.edu/programs/COSCBS/program-requirements-a1nCj) | `R1299/L30` | AI/ML and exploring | Foundation |
| [Electrical and Computer Engineering BSECE](https://catalog.arizona.edu/programs/ECEBSECE/program-requirements-a1nCj) | `R17348/L320` | AI/ML, embedded, and exploring | Foundation |

Direction and learning-stage labels are application annotations in `data/connectors/course_discovery.json`. A link in a program section supplies a discovery candidate; it does not approve a prerequisite, substitution, degree requirement, or semester placement. Newly discovered courses have unreviewed academic rules and retain unknown enrollment status.

The configuration stores program URLs and section locators. Course IDs and descriptions are read during use. Initial candidates follow configuration and source order, deduplicated by URL, within the remaining request budget. This is a bounded foundation expansion; a request for another course can still be outside the available collection. There is no catalog-wide crawler or completeness claim.

## Request path and validation

`run_advisor` loads the validated discovery configuration for each explicit source-enabled submission. The lower-level `refresh_catalog` accepts an explicit `discovery_plans` argument, so isolated source tests and callers can use a fixed scope. Ordinary interface rerenders make no source requests. Explicit offline mode retains the bundled collection.

The connector:

1. Selects configured programs for the requested direction and supported edition.
2. Merges course discovery with any prerequisite job for the same program source. The Computer Science page is downloaded once when both purposes need it.
3. Validates the primary program identity and active catalog edition. Discovery traverses visible `programRequirements` groups in that primary program; unrelated metadata and hidden groups cannot supply course IDs.
4. Accepts only unique, explicitly listed seven-digit course IDs in exact configured sections. Missing or duplicate sections, free-text conditions, nested selections, and oversized lists are rejected for discovery.
5. Resolves IDs to fixed HTTPS paths on `catalog.arizona.edu` and fetches them without redirects. A discovered page must report the same internal `courseGroupId`, the matching edition, an undergraduate ECE/CSC course code, and supported fixed units. Known configured courses also reject conflicting internal IDs when present.
6. Adds usable descriptions to the request's active catalog and records their origin and field sources. Retrieval, rule evaluation, generated context, rendered cards, the collection, completion picker, and inspector use that active catalog.

At most eight course pages and two program pages are requested, with three workers. Discovery can use at most three of the available course slots. Each selected section accepts at most 40 distinct course IDs; a program job accepts at most 16 selected sections. Existing response-size, timeout, and traversal limits apply. These bounds do not promise a fixed end-to-end latency.

## Provenance and failure behavior

Each added record stores the originating program source, section locators, course ID, and discovery time. Its `field_sources` maps title, summary, credits, and enrollment-reference fields to the actual course-page source. The description evidence chunk cites the course page; the program page remains separate origin metadata. Catalog validation rejects dangling field sources and inconsistent discovery bindings.

The generator receives field-source mappings under prompt version `p07-v5-course-discovery`. The bundled data version remains `pilot-2026-11-03-rule-provenance-v1`; the active corpus hash identifies the request's fetched evidence. Generated claim accuracy still needs evaluation beyond citation membership.

Source, prerequisite, and discovery outcomes remain distinct:

| Situation | Behavior |
| --- | --- |
| Fresh, validated program links and course content | Add the course with its source dates and unknown academic rule |
| Program check fails, even with a dated valid link cache | Keep the link cache as reference; do not promote new candidates from it |
| Course check fails with a valid course cache | A dated description can remain available; its source is stale and its rule is unknown |
| Course check fails without a valid cache | Add no record or placeholder; trace status is `unavailable` and download time is absent |
| Optional discovery section fails while the reviewed prerequisite section verifies | Preserve the independent prerequisite result; discovery remains unavailable |
| Linked page duplicates or conflicts with an existing course identity | Retain the configured record and report the skipped candidate |
| Edition or request budget is unsupported | Retain bounded saved evidence and report the limitation |

Course and program caches use schema version 2. Program cache identity includes the selected prerequisite and discovery sections. Reads validate identities, hashes, edition, section sets, timestamp ordering, and supported course scope. Incompatible caches rebuild from public sources. Atomic-write failures retain freshly fetched in-memory records; student profiles and credentials are not stored in these public-source caches. Unchanged checks reuse compatible embedding vectors.

## Verification

The automated suite passes 212 tests, including 39 discovery cases and 15 Streamlit interactions. New cases cover primary/visible-section scope, malformed and unbounded IDs, wrong subjects and graduate courses, missing/mismatched internal IDs, unsupported editions and units, shared download budgets, deduplication, independent prerequisite outcomes, outages, conditional requests, stale/corrupt/incompatible caches, cache-write failures, generation context, field provenance, and interface rerenders.

[Public observations](evidence/course_discovery_2026-11-03.json) retain an initial discovery check and a final CLI check after internal-ID validation was added. Both use a controlled exploring profile and make no embedding, generation, or opportunity-provider calls. UTC timestamps fall on November 4; the Arizona development date was November 3.

The initial check verified both program pages and all eight selected course pages, adding:

| Course | Title | Units |
| --- | --- | --- |
| CSC110 | Introduction to Computer Programming I | 4 |
| ECE201 | Programming 2 | 3 |
| ECE220 | Basic Circuits | 5 |

Its total backend time was 6.943 seconds. One additional link was deliberately left unfetched under the discovery cap. The final CLI returned zero and verified matching internal IDs for all eight selected courses. These are individual observations, not a latency or answer-quality benchmark.

Run the same public-source path without model credentials:

```powershell
.\.venv\Scripts\python.exe scripts/check_sources.py --career exploring
```

The trace includes discovered course origins, field sources, successful-check/download times, and separate `rule_status` and `discovery_status` values. Exit zero requires every selected check to succeed; skipped links beyond the configured candidate cap are reported as a bounded-coverage notice.

## Next backend work

Add checks of the two configured resource pages, then expand reviewed retrieval and claim-support cases. Broader discovery should follow source-specific parser review and suitability evaluation. Academic conditions remain unknown until edition-specific evidence supports a reviewed interpretation.
