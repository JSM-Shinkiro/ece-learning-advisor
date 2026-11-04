# Runtime official-source checks

Implemented November 3, 2026. Development work belongs in `ece-learning-advisor`; the submitted repository and midproject snapshot remain unchanged.

**Follow-up, November 3:** [Prerequisite evidence](15_PREREQUISITE_EVIDENCE.md) adds checks of explicitly bound program sections, separate rule chunks, and prompt version `p07-v4-rule-provenance`. The course-only milestone and measurements below retain their original scope and results.

**Later follow-up, November 3:** [Bounded course discovery](16_COURSE_DISCOVERY.md) adds program-linked descriptions, internal course-ID checks, field provenance, and prompt version `p07-v5-course-discovery`.

## Request path

`run_advisor` now checks relevant configured official course pages before retrieval, academic evaluation, and optional generation. `recommend` remains a pure operation on an already selected catalog, so provider comparisons and controlled tests can still use a fixed corpus.

The connector selects the configured courses for AI/ML, embedded systems, or both directions, including available dependency records. The pilot includes ECE101, ECE369A, ECE372A, ECE425, and CSC120. It does not discover the entire catalog or refresh resource/program pages yet.

For each course, the connector:

1. Accepts only the configured HTTPS course path on `catalog.arizona.edu`, without following redirects.
2. Parses the Nuxt reference table as JSON, without executing scripts. The primary course code and active catalog label must match the configured record and student's supported edition.
3. Extracts plain description text, title, fixed units, and the enrollment requirement identifier. Missing editions, ambiguous metadata, variable units, or unrecognized layouts retain dated evidence.
4. Overlays validated fields into a copy of the request catalog. Approved bundled records are never overwritten.
5. Returns that same active catalog for generation, rendered cards, and the inspector.

Fetching a course description does not interpret or approve a prerequisite. A changed enrollment requirement identifier revokes an affected reviewed rule. Four ECE conditions remain unresolved. The reviewed CSC120 condition is supported by a separate program page whose original snapshot date remains visible.

## Freshness and recovery

| Field or state | Meaning |
| --- | --- |
| `retrieved_at` | When the cached source content was downloaded |
| `last_checked_at` | Last successful source check; a failed attempt does not advance it |
| `attempted_at` | Time the current check was attempted, in the request trace |
| `updated` | A validated source snapshot was first fetched or its normalized content changed |
| `unchanged` | HTTP 200 supplied the same normalized content |
| `not_modified` | HTTP 304 validated the existing cached snapshot |
| `stale_cache` | A check failed; a previously validated, dated cache supplied the fields |
| `bundled_fallback` | A check failed without a valid cache; the dated reviewed snapshot remains |
| `unsupported_edition` | The student's edition or configured edition metadata is not supported |
| `cache_saved` | Whether this attempt successfully wrote its source cache |

ETag and Last-Modified validators are sent when available. The observed catalog responses did not supply them, so the real checks downloaded pages and compared normalized content hashes. A server's changing navigation or page shell does not change the extracted-course fingerprint.

Source freshness is supplied separately in the generator context and trace under prompt version `p07-v3-source-freshness`. It is excluded from embedding identity. Unchanged checks reuse the existing index; when one description changes, document-level caches reuse the other compatible vectors. Model, dimensions, text, or input-format changes still invalidate their relevant vectors. Cache-write failures retain usable in-memory vectors or freshly fetched source fields, with their cache status reported.

Sources not connected to a runtime checker retain the `snapshot` state. A successful course-page check must not be read as a fresh check of every resource or prerequisite source. Unsupported student editions retain clearly labelled references rather than silently adopting the current requirements.

## Bounds and operation

- Checks run on explicit roadmap actions, not ordinary Streamlit rerenders.
- At most eight configured course sources are checked per request, with three workers.
- Each response is limited to 3 MB; connection and read timeouts are four and six seconds. Streaming also checks a twelve-second per-page budget. These are operational limits, not an end-to-end latency guarantee.
- Corrupt, incompatible, mismatched, or oversized source caches are ignored and can be rebuilt from official pages. Errors expose status/category information rather than raw transport details.
- Only public course data is stored under `.cache/sources`; student profiles and credentials are not part of these entries.
- `ECE_REFRESH_SOURCES=true` is the default. `false` is an explicit offline mode with dated saved evidence.
- A persistent content database is optional. If one is added later, scheduled refresh must supplement checks during use.

To exercise the backend without model requests:

```powershell
.\.venv\Scripts\python.exe scripts/check_sources.py --career exploring
```

The command writes `.cache/source_check_trace.json`. Exit status zero means all requested checks succeeded; an incomplete check returns a nonzero status. The older `refresh_sources.py` stages review candidates, and `verify_live.py` preserves the original bundled-corpus provider comparison.

## Verification

The pinned environment installed successfully, `pip check` reported no broken requirements, and the automated suite passed 124 tests, including 13 Streamlit interaction tests. The command-line checker returned zero for the supported AI/ML catalog check and one for an unsupported student edition.

Controlled HTTP tests cover changed/unchanged pages, conditional requests, outages, redirects, wrong identities/editions, missing metadata, oversized responses, corrupt caches, changed requirement references, and source/vector cache-write failures. A Streamlit test verifies that fetched fields reach the cards and ordinary rerenders do not repeat checks. The generator integration test receives fetched evidence and its exact freshness state through a controlled provider.

Real public-source checks are recorded in [the source-check trace](evidence/source_checks_2026-11-03.json). They use an exploring profile and no embedding or generation calls:

| Observation | Result | Total backend time |
| --- | --- | --- |
| Empty source cache | Two sources fetched; three failures retained dated bundled evidence | 8.576 s |
| Next submitted request | All five course pages verified | 5.497 s |
| Repeat with a verified cache | All five reported unchanged; corpus identity matched the preceding request | 7.389 s |

These are three single observations, not a latency benchmark. The first incomplete request and its fallbacks are retained rather than removed from the evidence. Live Gemini and Adzuna were not retested in these source checks; the existing historical provider evidence keeps its original scope.

Connector reference: [official ECE101 page](https://catalog.arizona.edu/courses/0432351). HTTP behavior follows the [HTTPX client API](https://www.python-httpx.org/api/) and [HTTP conditional-request semantics](https://www.rfc-editor.org/rfc/rfc9110.html#name-conditional-requests).

## Next backend work

Review more academic-rule sources and catalog editions, extend bounded course/resource discovery, verify live opportunity results, and evaluate relevance and claim support. Preserve unknown conditions until their interpretation is supported by evidence.
