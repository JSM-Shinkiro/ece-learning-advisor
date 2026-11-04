# Technical Design

## Stack

| Component | Starting choice |
| --- | --- |
| Interface | Python, Streamlit, Plotly |
| Semantic retrieval | Gemini Embedding 2 adapter, NumPy cosine ranking |
| Keyword and hybrid retrieval | BM25, Reciprocal Rank Fusion |
| Explanations | Gemini selects application-owned statements; default `gemini-3.5-flash-lite`; new schema needs live verification |
| Records and validation | JSON, Pydantic, exact statement/wording and citation checks |
| Academic rules | Python predicates and three-state evaluation |
| Profiles | Export/import first, then authenticated durable storage |
| Opportunities | One job API, initially Adzuna if access and coverage work |

Use one Python application. A separate frontend service and vector database are unnecessary for the initial collection. Model IDs are configurable and the tested top-level dependencies are pinned.

## Automatic source retrieval target

The deployed app should obtain academic information from official sources itself. Saved course exports, program PDFs, sample plans, and screenshots are development references and parser-validation examples. They are not a required production catalog database.

Add source adapters that resolve official program and course links, fetch the required pages or documents, parse them into validated records, and supply evidence to RAG. Prefer supported public exports or documented APIs when available. Verify each access path before relying on it. Begin with ECE and a bounded number of source requests per interaction. An unrestricted web crawler is unnecessary.

Keep source URLs, parser rules, and trusted domains in configuration. Build the active evidence index in memory and use a rebuildable cache for fetched content and embeddings. A permanent academic or vector database is optional. Query a job provider separately when the student requests opportunities.

The current app starts with bundled reviewed JSON, then checks relevant configured course/resource pages and explicitly bound prerequisite-source sections before retrieval. It overlays validated public fields in a request-local catalog and discovers additional course descriptions from configured foundation sections. Catalog-wide discovery remains planned. See [runtime checks](14_RUNTIME_SOURCES.md), [prerequisite evidence](15_PREREQUISITE_EVIDENCE.md), [bounded discovery](16_COURSE_DISCOVERY.md), and [resource checks](17_RESOURCE_SOURCES.md).

## Code organization

| Module | Responsibility |
| --- | --- |
| app.py | Forms, action buttons, and rendered results |
| src/models.py | Validated data contracts |
| src/catalog.py / src/ingest.py | Reviewed collection, evidence chunks, and source parsing |
| src/sources.py / src/rule_sources.py / src/source_http.py | Bounded course/rule checks, source caches, and shared HTTP limits |
| src/discovery.py / data/connectors/course_discovery.json | Validated program-section configuration, course candidates, and provenance |
| src/resource_sources.py | Resource identity, introductory excerpts, versions, bounded redirects, and caches |
| src/evaluation.py / scripts/evaluate_reviewed.py | Frozen-corpus metrics, roadmap references, authored claim probes, and explicit embedding opt-in |
| src/controller.py | One submitted request, source refresh, provider setup, and failure recovery |
| src/providers.py | Gemini calls, vectors, and versioned embedding cache |
| src/query.py | Versioned whole-token domain aliases and bounded source-vocabulary query expansion |
| src/grounding.py | Canonical explanation statements, context binding, model selections, and exact wording validation |
| retrieval.py | BM25, semantic ranking, fusion, and deduplication |
| rules.py | Prerequisite evaluation |
| src/service.py | Query/context assembly, orchestration, reference checks, and validated answer rendering |
| src/inspector.py / src/retrieval.py | Inspection UI, statement selections, scores, and embedding projection |
| profiles.py / jobs.py | Saved progress and opportunity search |

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

## Configuration, caching, and storage

Use configuration for providers, model IDs, dimensions, retrieval method, candidate count, context budget, recommendation count, timeouts, data version, and explicit fixture mode. Keep secrets outside source control.

Cache index data by corpus and model configuration. Request caches include the relevant profile, query, prompt, model, and data versions. Updating completed coursework invalidates dependent recommendations.

For runtime source retrieval, key fetched content by canonical URL and catalog edition. Track the last successful source check, last content download, content hash, validation state, and source-specific expiry. Aim to revalidate the relevant sources when a student submits a roadmap update or job search, respecting provider limits. Use conditional requests when supported and reuse unchanged content and embeddings. A widget rerender should not trigger a new fetch.

Any persistent content database must have an automatic refresh job with configurable intervals, bounded retries, and a recorded outcome. Use source-specific schedules, with faster checks for job listings than for degree requirements. Refresh changed records and their dependent chunks, embeddings, and answers together. Preserve catalog editions and source versions needed by existing citations. This background job supplements freshness checks during use.

Explicit roadmap updates perform on-use revalidation. If a source cannot be checked, identify the last successful check and label cached results rather than claiming they are current. Choose and measure refresh intervals during connector testing. Scheduled source updates remain planned; no recurring job is active in the current app.

Session State supports the current interaction. Profile export/import can preserve progress without a server database. Account-based return visits would need separate durable profile storage. Choose that hosting and sign-in path after the local baseline works. Profile storage does not require a permanent course database.

Job results contain provider/query metadata, retrieval time, listing IDs, titles, employers, locations, original application links, available posting dates, and descriptions as supplied. Distinguish snippets from full descriptions. Start with a roughly 20-minute cache, subject to provider terms.
