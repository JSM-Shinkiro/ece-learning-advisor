# Technical Design

## Stack

| Component | Starting choice |
| --- | --- |
| Interface | Python, Streamlit, Plotly |
| Semantic retrieval | Gemini Embedding 2 adapter, NumPy cosine ranking |
| Keyword and hybrid retrieval | BM25, Reciprocal Rank Fusion |
| Explanations | Gemini selects application-owned statements; default `gemini-3.5-flash-lite`; current schema verified November 4 |
| Records and validation | JSON, Pydantic, exact statement/wording and citation checks |
| Academic rules | Python predicates and three-state evaluation |
| Profiles | Export/import first, then authenticated durable storage |
| Opportunities | Public Greenhouse employer boards; optional configured Adzuna adapter |

Use one Python application. A separate frontend service and vector database are unnecessary for the initial collection. Model IDs are configurable and the tested top-level dependencies are pinned.

## Automatic source retrieval target

The deployed app should obtain academic information from official sources itself. Saved course exports, program PDFs, sample plans, and screenshots are development references and parser-validation examples. They are not a required production catalog database.

Add source adapters that resolve official program and course links, fetch the required pages or documents, parse them into validated records, and supply evidence to RAG. Prefer supported public exports or documented APIs when available. Verify each access path before relying on it. Begin with ECE and a bounded number of source requests per interaction. An unrestricted web crawler is unnecessary.

Keep source URLs, parser rules, and trusted domains in configuration. Build the active evidence index in memory and use a rebuildable cache for fetched content and embeddings. A permanent academic or vector database is optional. Query a job provider separately when the student requests opportunities.

The current app starts with bundled reviewed JSON, then checks relevant configured course/resource pages and explicitly bound prerequisite-source sections before retrieval. It overlays validated public fields in a request-local catalog and discovers additional course descriptions from configured foundation/core/track sections. Catalog-wide discovery remains planned. See [runtime checks](14_RUNTIME_SOURCES.md), [prerequisite evidence](15_PREREQUISITE_EVIDENCE.md), [bounded discovery](16_COURSE_DISCOVERY.md), and [resource checks](17_RESOURCE_SOURCES.md).

## Code organization

| Module | Responsibility |
| --- | --- |
| app.py | Forms, action buttons, and rendered results |
| src/settings.py | Validated runtime settings, protected credentials, and cache-root resolution |
| src/deployment.py / scripts/check_deployment.py | Local configuration/dependency/data/cache checks and bounded server/offline-preview smoke test |
| src/models.py | Validated data contracts |
| src/catalog.py / src/ingest.py | Reviewed collection, evidence chunks, and source parsing |
| src/sources.py / src/rule_sources.py / src/source_http.py | Bounded course/rule checks, source caches, and shared HTTP limits |
| src/discovery.py / data/connectors/course_discovery.json | Validated program-section configuration, course candidates, and provenance |
| src/resource_sources.py | Resource identity, introductory excerpts, versions, bounded redirects, and caches |
| src/evaluation.py / scripts/evaluate_reviewed.py | Frozen-corpus metrics, roadmap references, authored claim probes, and explicit embedding opt-in |
| src/review.py / scripts/review_retrieval.py | Unscored review packets, separate complete judgments, snapshot binding, and offline keyword metrics |
| src/controller.py | One submitted request, source refresh, provider setup, and failure recovery |
| src/providers.py | Gemini calls, vectors, and versioned embedding cache |
| src/query.py | Versioned whole-token domain aliases and bounded source-vocabulary query expansion |
| src/grounding.py | Canonical explanation statements, context binding, model selections, and exact wording validation |
| retrieval.py | BM25, semantic ranking, fusion, and deduplication |
| rules.py | Prerequisite evaluation |
| src/service.py | Query/context assembly, orchestration, reference checks, and validated answer rendering |
| src/inspector.py / src/retrieval.py | Inspection UI, statement selections, scores, and embedding projection |
| src/profiles.py | Saved progress |
| src/jobs.py | Shared opportunity result and optional Adzuna adapter |
| src/opportunities.py / data/connectors/employer_boards.json | Bounded public employer-board requests, validated postings, local filters, and explicit session reuse |
| scripts/check_opportunities.py | Public-source observation report, with no credentials or model calls |

Provider calls run only after explicit actions, behind service adapters. Scripts build the index, refresh source candidates, and run smoke evaluation. Reviewed records and synthetic test fixtures are separate.

## Data design

The table describes the intended record design. The pilot schema is smaller. It has source dates/hashes, course summaries and credits, rules, team topic/stage annotations, profile background, evidence IDs, and cache manifests. Explicit rule provenance binds a source section and reviewed statement to an interpretation hash. Publication dates, costs, skill mapping reviews, and durable profile IDs need further work. CSC120 has a reviewed saved condition; runtime discovery can attach CSC110's bound math condition with unknown placement. The four ECE conditions stay unknown.

| Record | Main fields |
| --- | --- |
| Source | ID, URL, title, type, retrieval time, publication time if known, catalog edition, hash, review status |
| Course | ID, exact code, edition, title, description, confirmed credits, source IDs, original prerequisite text, structured rule, reviewed skill links |
| Resource | ID, title, provider, URL, topic, level, known cost, source IDs, check date |
| Career direction | ID, reviewed skills, course/resource mappings, supporting rationale and sources, job query terms |
| Student | Profile ID, standing, catalog edition if known, interests, goal, completed courses, whether the history is complete, optional experience/current enrollment |
| Evidence chunk | Chunk ID, record ID, source ID, text, section locator, hash, edition, review status |
| Index manifest | Corpus hash, ordered chunk IDs/hashes, model, dimensions, normalization, format version, build time |

Course identity includes its catalog edition. Preserve suffixes and cross-listings. A graduate entry cannot automatically substitute for an undergraduate record.

Career mappings are reviewed team annotations. They are not official guarantees about employment. Retrieval time and publication time remain separate.

## Prerequisite rules

Support AND and OR conditions, course completion, minimum grades, completion-or-concurrent enrollment, standing, consent, and unknown conditions.

Return **satisfied**, **unsatisfied**, or **unknown**, with reasons and source references.

- For AND, any unsatisfied child makes the result unsatisfied. Otherwise, an unknown child makes it unknown.
- For OR, any satisfied child makes the result satisfied. Otherwise, an unknown child makes it unknown.
- Reject empty logical groups as malformed data.
- If a declared complete history lacks a required course, that completion condition is unsatisfied. If the history is incomplete, absence remains unknown.
- A missing required grade, unverified equivalency, or unsupported rule remains unknown.
- A changed statement or interpretation, failed live check, or unsupported catalog edition makes a bound condition unknown. Explicit offline mode can evaluate a dated reviewed snapshot, with that limitation recorded in its reasons.
- Respect alternatives and co-requisites when arranging a learning order. Flag cycles.

The roadmap suggests learning order. It does not establish official enrollment eligibility or complete a degree audit. The first implementation prioritizes foundations for students who report being new to programming and have no listed foundation course. It marks advanced matches as later goals. These stage annotations are team decisions, not catalog prerequisites.

## Request and output boundaries

The retrieval stage returns chunk/record IDs, method, rank, and the relevant scores. The context object stores the exact evidence sent to the generator, allowed record IDs, rule results, prompt version, and budget use.

The provider returns a selection with no free-text explanation field:

```text
status: answered or insufficient_evidence
recommendations:
  - record_id
    statement_ids: one to four owned statement IDs
clarification_code: null, insufficient_evidence, or more_details
```

`GenerationContext.allowed_statements` contains up to 80 statements, each with record identity, field, claim type, exact wording (at most 1,400 characters), and supplied evidence IDs. Stable statement hashes bind these values to the complete context. Long or URL-bearing candidate wording is omitted. The model may select up to five distinct allowed records and four distinct owned statements per record. An abstention uses a fixed code with no recommendations.

The service reconstructs statements from the active catalog and compares the registry before materializing the existing `GeneratedAnswer` display shape: record IDs, reasons with text/type/evidence, or application-owned clarification text. Exact wording/type/citation validation follows schema and reference checks. Mutated selections, foreign IDs, arbitrary prose, repeated statements, changed context inputs, and unsupported clarification text fail the contract. A factual statement cannot bypass the contract by being labeled a recommendation. Source cards and computed academic results remain available on failure.

`validate_references` preserves the earlier membership behavior for the frozen audit. Production uses `validate_answer(answer, context, catalog)`. Trace fields include `answer_contract`, `selected_statement_ids`, `statement_validation_passed`, and a sanitized `validation_error`. Prompt version is `p07-v7-statement-selection`, contract `statement-selection-v1`. This changes the provider's role to statement selection rather than unrestricted explanation writing; source accuracy and selection suitability still require evaluation. See [grounded explanations](19_GROUNDED_EXPLANATIONS.md).

Query policy `p07-domain-aliases-v1` is separate from the prompt/output contract. Coverage gates and query construction share original-text alias matching; up to 12 existing-catalog terms may be appended within the 5,000-character query limit. For specific questions, a local keyword lookup can prefer one course from the permitted career scope within the existing context policy. Traces add `query_interpretation` (version, matched aliases, added terms) and `focused_record_ids`. The inspector exposes added terms. The raw evaluator remains the default; expanded evaluation is separately labeled and retains the original/effective query pair. See [query interpretation](20_QUERY_INTERPRETATION.md).

`DiscoveryPlan.reviewed_rules` binds an optional interpretation to an exact discovered course ID/code, catalog edition, enrollment reference, visible program section, and reviewed statement/tree hashes. New links receive no interpretation unless the binding matches. Program cache schema 3 stores optional visible discovery statements beside course IDs; their absence preserves descriptive discovery while the condition remains unknown. Production prerequisite statements are selected through the primary visible requirements tree. See [discovered-course conditions](21_DISCOVERED_COURSE_RULES.md).

The [CS coverage extension](24_CS_FOUNDATION_COVERAGE.md) adds CSC144 and CSC210 beside CSC110, using additional sections of the same program request. CSC144 combines programming and mathematics alternatives; CSC210 checks prior CSC120 completion with minimum grade C. Placement remains unknown. An optional `ReviewedDiscoveryRule.study_stage` supplies a team learning annotation after exact course-ID/code/edition validation; it does not depend on academic satisfaction and does not become introductory if an enrollment reference changes. Source order controls default selection under the unchanged three-discovery limit; explicit course mentions can now reserve slots through the policy below.

[Requested-course policy](25_REQUESTED_COURSE_DISCOVERY.md), with [phrase routing](26_COURSE_PHRASE_ROUTING.md) and [version 3 completion/stage handling](29_ECE_CORE_COVERAGE.md), matches supported course codes and reviewed phrases from the question, falling back to interests only when the question is empty. At most 16 combined distinct targets are considered: explicit codes first, then phrase matches in mention order. `DiscoveryPlan.course_codes` supplies reviewed routing labels alongside identities already bound by reviewed rules; `course_phrases` binds bounded, distinct phrases to those known codes. Conflicting identities, ambiguous phrases, and broad standalone generic words are rejected. A hint can prioritize only an ID in a freshly verified selected program section, and the downloaded page must confirm that exact code as well as its existing identity/edition checks. Remaining candidates retain source order. No user text enters source URLs or public content caches.

`DiscoverySelection` records candidate reasons, matched reviewed phrases, and final request outcomes; `CatalogRefresh.trace()` exposes it under `discovery_selection`. The inspector shows these outcomes separately from source freshness and academic status. A failed target has no substitute request beyond the existing budget and no fabricated record. Stale cached descriptions are labeled separately. This policy allocates source downloads; it does not interpret natural-language intent, broaden career scope, or change enrollment rules.

A reviewed phrase can open the pre-retrieval source gate, but generation still needs an available target in the active collection. `requested_record_ids` filters resolved targets by identity, edition, career scope, and recorded completion. Only successful/dated additions or already collected targets can supply preferences to `recommend`. Validated preferred codes missing from the retrieval query are appended within its 5,000-character bound and recorded as `discovery_query_terms`; the first eligible target supplies the focus preference. Missing or out-of-scope records cannot bypass the generation guard. Offline mode receives no new discovery preferences. The frozen evaluator and domain-alias policy remain unchanged.

The [ECE core extension](29_ECE_CORE_COVERAGE.md) adds core and computer-engineering program sections with six bound identities. `DiscoveryPlan.course_stages` holds optional preparation annotations for known codes, independently of rule satisfaction. Overrides conflicting with reviewed-entry stages are rejected. Policy v3 removes known completed candidates before allocating the unchanged discovery budget and exposes skipped codes in the inspector. A downloaded code assigned to a different configured identity is rejected. Stage origins stay separate from official field provenance; questions, completion histories, and grades never enter public source caches.

The [source-recovery layer](30_SOURCE_RECOVERY.md) permits one transient retry per public source job, with shared elapsed and decoded-size guards across a resource redirect. HTTPX phase timeouts are clipped to the remaining cooperative guard; this is not hard cancellation of synchronous I/O. `SourceCheck.attempts`, `retry_count`, and `transport_seconds` retain safe transport metadata. Logical source caps are distinct from HTTP-attempt caps. Parsing, identity, cache, edition, and rule checks still control freshness and academic results; model/opportunity transports are unchanged.

## External relevance review

The [reviewer workflow](28_REVIEWER_WORKFLOW.md) exports exact saved evidence and source metadata, shuffled candidate orders, and blank grades without rankings or prior labels. Separate completed forms bind a packet fingerprint. Scoring requires every question/chunk pair, strict grades, unique JSON keys, and the matching full catalog snapshot. Default questions remain development material; custom question provenance and reviewer independence are not authenticated. Raw/expanded keyword reports retain grades, exact rankings, undefined-metric counts, and implementation identities. No model or source calls occur. This does not change the live recommendation path or certify a held-out study.

## Configuration, caching, and storage

Use configuration for providers, model IDs, dimensions, retrieval method, candidate count, context budget, recommendation count, timeouts, data version, and explicit fixture mode. Keep secrets outside source control.

The Streamlit app loads `RuntimeSettings` before profile widgets. Environment flags accept true/false or 1/0, model IDs use the supported Gemini naming format, and embedding dimensions are locally bounded to 1–3072. Invalid values produce sanitized setting-name errors. Secret fields are excluded from representation and exports; presence flags do not establish valid credentials. `ECE_CACHE_DIR` resolves relative to the project root, with separate public source and embedding subdirectories. This changes cache placement, not cache schemas or academic interpretations.

The [runtime-readiness command](27_DEPLOYMENT_READINESS.md) checks local production dependencies, evidence/connectors, writable cache paths, a loopback Streamlit health response, and an offline AppTest submission. Smoke children receive blank credentials and fixed offline/development flags, preserve validated model settings, and block the application's synchronous HTTP clients. Processes terminate after the check. These checks do not verify hosting, external-source availability, model access, or authentication.

Cache index data by corpus and model configuration. Request caches include the relevant profile, query, prompt, model, and data versions. Updating completed coursework invalidates dependent recommendations.

For runtime source retrieval, key fetched content by canonical URL and catalog edition. Track the last successful source check, last content download, content hash, validation state, and source-specific expiry. Aim to revalidate the relevant sources when a student submits a roadmap update or job search, respecting provider limits. Use conditional requests when supported and reuse unchanged content and embeddings. A widget rerender should not trigger a new fetch.

Any persistent content database must have an automatic refresh job with configurable intervals, bounded retries, and a recorded outcome. Use source-specific schedules, with faster checks for job listings than for degree requirements. Refresh changed records and their dependent chunks, embeddings, and answers together. Preserve catalog editions and source versions needed by existing citations. This background job supplements freshness checks during use.

Explicit roadmap updates perform on-use revalidation. If a source cannot be checked, identify the last successful check and label cached results rather than claiming they are current. Choose and measure refresh intervals during connector testing. Scheduled source updates remain planned; no recurring job is active in the current app.

Session State supports the current interaction. Profile export/import can preserve progress without a server database. Account-based return visits would need separate durable profile storage. Choose that hosting and sign-in path after the local baseline works. Profile storage does not require a permanent course database.

Job results contain provider/query metadata, retrieval time, listing IDs, titles, employers, locations, original application links, available publication/update dates, source checks, issues, total matches, and fresh/reused status. The public-board path requests metadata only and supplies no description snippet. The legacy Adzuna path can supply a snippet; it is not a full job description.

The separate [posting-detail action](32_POSTING_DETAILS.md) requests one displayed public posting through a configured board/token/ID endpoint. It revalidates the returned identity, employer when supplied, and original link before extracting bounded plain text. The session holds one checked description, with its own requested/successful check times, provider dates, text fingerprint, truncation flag, and changed metadata fields. Each action sends one fresh GET; rerenders send none. Failed checks retain no description or successful check time. A new search, including explicit metadata reuse, or a profile transition clears posting-detail state. Job text remains outside academic rules, retrieval/generation context, and profile exports.

`request_opportunities` runs only on the search action. Default searches request the sources; explicit reuse can select the same provider/career/literal-location/internship/update-window result younger than 20 minutes. Reuse preserves the original retrieval timestamp. A new request clears visible results and old error state before validation; a source failure cannot silently display the old search as current. Profile changes clear both the opportunity result and its session cache.

The [student-opportunity extension](31_STUDENT_OPPORTUNITIES.md) uses the third board slot for Anduril Industries. A standard Greenhouse-hosted posting base can differ from the careers-site host only with an exact configured board-token path. `early_career` is an explicit title-label filter, mutually exclusive with internship filtering; it excludes senior/leadership and internship titles without inferring qualifications. Returned role labels describe the displayed snapshot. A configuration/title-policy fingerprint joins the cache key, and the captured board list is passed to the fetch; changing either forces a new search even when reuse is selected.

The public adapter supports one to three configured Greenhouse boards, at most three workers, 4,000 raw posts and 3 MB decoded JSON per board, and ten displayed matches. Posting links must bind the configured employer/board and exact job ID. Prospect posts are omitted. Titles are filtered locally, locations use a case-insensitive literal substring, internship/co-op is a title filter, and the optional 7/30/90-day window uses the provider's update date. These filters do not infer qualifications, geographic equivalence, or enrollment eligibility. Partial failures retain labeled valid-source results; all-source failure raises a sanitized error with source-check metadata. See [live opportunities](23_LIVE_OPPORTUNITIES.md).
