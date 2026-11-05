# Runtime learning-resource checks

Later checks: [requested-course discovery](25_REQUESTED_COURSE_DISCOVERY.md) retains November 4 resource timeouts; [phrase routing and transport probes](26_COURSE_PHRASE_ROUTING.md) record later successful checks under unchanged HTTP limits. The original resource milestone below retains its own scope and measurements.

Implemented November 3, 2026, in the development repository. This extends [bounded course discovery](16_COURSE_DISCOVERY.md). The submitted repository and midproject artifacts remain unchanged.

**Follow-up, November 3:** [Reviewed development evaluation](18_REVIEWED_EVALUATION.md) adds fixed-corpus relevance and roadmap cases plus authored claim probes. The resource checks and measurements below retain their original scope and results.

## Implemented scope

Relevant roadmap submissions check the two configured public learning resources before retrieval and optional generation:

| Resource | Configured source | Directions |
| --- | --- | --- |
| PyTorch Quickstart | [Official tutorial](https://docs.pytorch.org/tutorials/beginner/basics/quickstart_tutorial.html) | AI/ML and exploring |
| CS50's Introduction to Computer Science | [Official OpenCourseWare](https://cs50.harvard.edu/x/) | AI/ML, embedded, and exploring |

The fetched fields are the resource title, a short introductory excerpt, and the published course/documentation version. Learning notes, activities, direction labels, and stages remain team annotations. A fetched excerpt does not establish university credit, course equivalency, or enrollment eligibility.

Resource versions are independent of academic catalog editions. Resources can be checked for a student whose catalog edition is unsupported by the academic connector; those academic conditions remain unverified.

## Extraction and identity

The parser accepts only the configured resource identities. PyTorch must provide the expected Quickstart document identity, documentation version, and article heading. CS50 must provide the CS50x year, the introductory computer-science course heading, and the Welcome section in the main content. Missing, conflicting, or unfamiliar layouts retain dated evidence.

The extractor selects at most two introductory paragraphs, bounded to 1,500 characters. It excludes navigation, footers, scripts, code blocks, hidden content, notices, and creation/update metadata. It does not execute page scripts. Line breaks and inline formatting preserve readable text.

Both connectors use the shared 3 MB download cap and connection/read/streaming budgets. Course and program redirects remain disabled. CS50 alone permits one redirect from its configured alias to a same-host `/x/YYYY/` edition path; credentials, unrelated paths, insecure URLs, query strings, fragments, and further redirect hops are rejected. A year-specific page must report the same year in its document identity.

Conditional validators are sent only to the exact URL that supplied the cached content. A redirect to a different CS50 year does not reuse the previous year's validators. The resolved URL is recorded and used for source links. An alias that directly serves content can retain its alias URL; the observed year is stored separately.

## Integration and provenance

The production `run_advisor` path enables resource checks on explicit submissions. The lower-level `refresh_catalog` accepts `resource_checks=True` for controlled callers; its default fixed scope remains useful in isolated course tests. Ordinary interface rerenders perform no source checks. At most two resource sources share the same three-worker pool with the existing eight-course/two-program budget. One permitted redirect per resource can add a request; the current configuration permits that extra request only for CS50.

The active resource records contain `resource_version` and `field_sources` for title, summary, and version. Their evidence chunks include the version and the complementary-study boundary. The generator receives the same source dates, field mappings, and excerpts shown in the interface and inspector, under prompt version `p07-v6-resource-sources`. The trace includes `resource_versions`, resource-kind checks, and resolved URLs.

The bundled catalog remains unchanged. Resource freshness and timestamps remain outside embedding identity. Excerpt or version changes alter the evidence text and rebuild the affected vector; unchanged checks reuse compatible vectors.

## Recovery and cache behavior

Public resource snapshots live under `.cache/sources/resources`, keyed by configured identity, requested URL, and cache/parser schema. Entries contain only bounded public content, source identity, version, validators, hashes, and successful-check/download times. No student history or credentials are stored in them.

| Outcome | Behavior |
| --- | --- |
| Valid HTTP 200 | Use freshly extracted fields and record both successful-check and download times |
| Valid HTTP 304 with a matching cache | Reuse content; advance the successful-check time without changing its download time |
| Failure with a valid cache | Use dated cached fields and mark the source stale |
| Failure without a valid cache | Keep the dated bundled resource and mark its source stale |
| Invalid identity, layout, redirect, or cache | Reject that candidate and use the applicable dated fallback |
| Cache write fails | Keep fresh in-memory fields; report that the cache was not saved |
| Resource request budget or binding is unsupported | Skip the check and retain saved evidence |

Reads validate source identity, URL, version, content hash, cache size/schema, and timestamp order. Writes are atomic. A failed check never advances the last-successful-check date. Resource failures do not revoke independently verified academic conditions, and academic-source failures do not prevent independent resource checks.

Explicit offline mode labels sources as saved snapshots, including a caller-supplied catalog that was verified on an earlier request. Previously verified rules become dated snapshot evaluations, while changed or otherwise unresolved rules retain their limitations. A whole-refresher failure marks affected course and resource sources stale. Neither path claims a new check occurred.

## Verification

The automated suite passes 266 tests, including 51 resource-source cases and 16 Streamlit interactions. Coverage includes both provider layouts, hidden/unrelated content, identity/version mismatches, unsafe and chained redirects, cross-edition validator handling, unsupported catalog years, stale/corrupt/oversized caches, conditional checks, cache-write failures, vector reuse, generator context, offline state, independent academic results, and interface rerenders.

[Public-source evidence](evidence/resource_checks_2026-11-03.json) records two complete exploring-profile submissions. They made no embedding, generation, or opportunity-provider calls. An earlier CS50 layout-inspection request timed out; a later inspection and both complete checks succeeded. UTC timestamps fall on November 4; the Arizona development date was November 3.

| Observation | Resource outcome | Total backend time |
| --- | --- | --- |
| First complete resource check | Both resource pages fetched with HTTP 200 | 11.051 s |
| Repeat submitted request | Both resource hosts returned HTTP 304; cached content reused | 11.686 s |

Both observations verified all 12 selected sources and had the same corpus hash. The expected notice that one extra course link was outside the discovery cap is retained. Observed resource versions were PyTorch tutorial documentation `2.15.0+cu132` and CS50x `2026`. These are individual observations, not a latency or answer-quality benchmark.

The existing source-check CLI exercises the integrated path without model credentials:

```powershell
.\.venv\Scripts\python.exe scripts/check_sources.py --career exploring
```

Its success status includes the selected resource checks. A permanent content database and scheduled refresh job have not been introduced; checks during use remain the active freshness mechanism.

## Next backend work

Build reviewed retrieval and claim-support evaluation cases, with expected source IDs and explicit unknown academic outcomes. Keep citation membership, source freshness, retrieval relevance, and factual claim support as distinct measures. Live opportunity verification and broader source coverage remain separate tasks.
