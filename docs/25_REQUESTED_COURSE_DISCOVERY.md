# Requested-course discovery

Implemented and checked November 4, 2026. An explicit configured course mention can now reserve a discovery slot before source-order defaults consume the three-course cap. The saved corpus, frozen evaluation references, submitted midproject files, academic interpretations, and dependency versions remain unchanged.

## Behavior

For example, a submitted AI/ML question about ECE201 previously reached the three CS defaults first. It can now select ECE201's verified ECE-program link first, then use the remaining slots in their existing order. Multiple supported mentions follow their first-mention order. Without explicit mentions, default selection is unchanged.

Policy `p07-course-request-priority-v1` recognizes whole ECE/CSC codes at undergraduate levels 100–499, including supported suffixes and optional spaces. It normalizes case/spaces, removes duplicates, and considers at most 16 distinct codes. The question takes precedence; interests supply mentions only when the question is blank. Experience, consent, and completed-course fields do not supply priority requests. The policy matches literal mentions; it does not infer negation, prerequisites, intent, topic similarity, or natural-language course titles.

Requested codes receive priority only within the selected career's configured program sections. An embedded request does not silently fetch the CS program. Already collected courses use no new discovery slot. An unrecognized or unavailable code cannot construct a catalog URL or broaden source scope. Up to three discoveries, eight course downloads, two program sources, and three workers remain the limits. A failed selected download does not trigger extra replacement requests.

This changes source allocation. Existing retrieval/context policies still determine which fetched records appear in the roadmap or generated explanation; selecting several descriptions is not a guarantee of a complete comparison answer. Priority does not approve a prerequisite, course substitution, semester placement, or enrollment.

## Identity and caches

The validated `DiscoveryPlan.course_codes` map supplies reviewed routing metadata for the configured ECE foundations:

| Code | Configured official course URL |
| --- | --- |
| ECE201 | [Course 0432591](https://catalog.arizona.edu/courses/0432591) |
| ECE220 | [Course 0120881](https://catalog.arizona.edu/courses/0120881) |
| ECE274A | [Course 0360981](https://catalog.arizona.edu/courses/0360981) |

CSC110, CSC144, and CSC210 reuse the identities already bound in their reviewed-condition entries. Conflicting mappings within or across plans are rejected. These labels supply routing, not academic evidence. Each ID must occur in a freshly verified selected program section before it can become a candidate. Stale/missing program links cannot be rescued by a code hint.

The fetched page must confirm the expected course code, internal identity, edition, and the existing supported metadata constraints. A code mismatch adds no record or placeholder, including when a cached payload is revalidated with HTTP 304. Actual descriptions and provenance still come from the course page. ECE201, ECE220, and ECE274A have no newly approved prerequisite interpretation and remain academically unknown.

Priority is computed for each submitted profile and is absent from public content caches. Changing the question recomputes selection even when program metadata is revalidated with HTTP 304. Source/cache identities, versions, response limits, and failure handling are unchanged. No new database, background refresh job, model call, or additional API credential is needed.

## Inspector and trace

`source_refresh.discovery_selection` includes the policy version, whether mentions came from question/interests, the bounded canonical codes, selected IDs/sections, selection reasons, actual added codes, source-check status, and final outcomes. It does not copy the free-text question into that selection object. The ordinary request trace can still contain the submitted profile under its existing contract.

| Final request status | Meaning |
| --- | --- |
| `added` | A matching validated course was added from a successful source check |
| `stale_added` | Dated validated cached content was added after a failed course refresh |
| `in_collection` | The active collection already contains the code; this label is not a freshness guarantee |
| `budget_limit` | A mapped live-link candidate did not fit the remaining discovery slots |
| `not_available` | No mapped candidate was available from freshly verified selected sections; the course may exist elsewhere |
| `unavailable` | A selected candidate could not be added, such as a missing download or identity mismatch |

The inspector displays requested-course outcomes separately from ranking, source freshness, and academic results. A request with no available course/topic match receives the existing coverage notice and does not initialize generation. Mentioning a missing course alongside a supported topic does not add that course to the evidence or allowed model statements. No successful-source label or fabricated card hides an unavailable target.

## Verification

The complete suite passes **678 tests**, including **36 discovery-priority cases** and **33 Streamlit interactions**. Controlled checks cover strict code parsing, input precedence, ordering/deduplication, the mention cap, default order, career scope, source/download budgets, configured identities, missing/stale links, outages, conditional caches, mismatched cached codes, no question text in public caches, unknown-course guards, grounded provider integration, and UI outcomes without rerender fetches.

The [dated live observation](evidence/discovery_priority_2026-11-04.json) exercises the normal source-check CLI with the ordered mentions ECE274A, ECE201, and ECE220. All three were added in that order. Six course pages and both configured programs were verified; CSC120's existing proof stayed verified and the three ECE conditions stayed unknown. The CLI and local cache checks made no embedding, generation, or opportunity requests and used no credentials.

The broader run did **not** pass every source check: PyTorch and CS50 both timed out and used visibly dated bundled evidence. One bounded resource-only recheck also timed out. The saved report retains the original unsuccessful overall exit, the successful course-selection result, and the failed resource observations. The initial CLI took about 12.4 seconds, including resource timeouts; this is one observation, not a latency benchmark or uptime claim.

Reproduce the explicit-code path with:

```powershell
.\.venv\Scripts\python.exe scripts/check_sources.py --career ai_ml --question "How should I prepare for ECE201?"
```

`--question` accepts up to 1,200 characters. The CLI prints source checks and requested-course statuses, then saves its normal trace. Its exit code continues to describe all selected source/interpretation checks; read the separate target statuses to determine whether a requested course was available. Source success alone does not establish request fulfillment or academic satisfaction.

Next, extend routing to reviewed course-title/topic requests, review broader source/deployment reliability, and obtain independent review of course selection and academic interpretations. Catalog-wide search, additional editions, and unresolved ECE conditions remain outside this unit.
