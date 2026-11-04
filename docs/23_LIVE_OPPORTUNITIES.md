# Live opportunities

Implemented and checked November 4, 2026. This unit adds real public employer-board results to the Opportunities tab without a job API credential or model call. The academic RAG pipeline and preserved midproject deliverables are unchanged.

## Sources and coverage

The configured employers are [Samsara](https://www.samsara.com/company/careers) and [Nuro](https://www.nuro.ai/careers). `data/connectors/employer_boards.json` binds each employer, its Greenhouse board token, and the allowed employer posting-URL shape. The [official Greenhouse Job Board API](https://docs.greenhouse.io/job-board.html) documents public unauthenticated GET requests. The adapter requests each board's `/v1/boards/{token}/jobs` metadata endpoint once per search, without `content=true`, detail requests, authentication, applications, or model generation.

Only these configured boards are searched. This is an initial opportunity source, not a market-wide job service. Matches come from engineering/research/developer/internship title terms for AI/ML or embedded systems, with several recruiting/sales terms excluded. Topic matches can include senior and adjacent engineering roles. Student standing, coursework, authorization to work, qualifications, and remote eligibility are not evaluated. The original posting supplies those requirements and its current availability.

## Search behavior

| Control | Meaning |
| --- | --- |
| Career | Saved AI/ML or Embedded Systems direction; exploring requires choosing a direction first |
| Location contains | Case-insensitive literal substring of the employer's location field; blank includes all listed locations |
| Internship / co-op titles only | Requires an internship or co-op term in the title |
| Listing updated within | Optional 7/30/90-day window using `updated_at`, not the first publication date |
| Recent-result reuse | Explicit opt-in for an identical provider, career, normalized location, internship flag, and update window younger than 20 minutes |

Submitting a search requests the sources by default. Ordinary rerenders do not fetch jobs. A reused result keeps its original retrieval timestamp and is visibly labeled. Changing the saved profile invalidates the result, error, and cache. A fresh failure clears the old visible result; there is no silent stale fallback. No persistent opportunities database or recurring background refresh exists.

Provider first-publication and last-update dates are stored separately. Missing, invalid, timezone-free, or substantially future dates stay unknown; an unknown update date is excluded by an age filter. Results sort by the valid update timestamp, with a stable ID tie break. At most ten are displayed, with the full matching count. The public adapter does not fetch or invent description snippets.

## Validation and failures

The source manifest supports one to three unique boards. Searches use at most three workers, a six-second HTTP timeout with four-second connect/pool limits, and a bounded streaming read. Each response is limited to 3 MB decoded JSON and 4,000 raw posts. The streaming budget is checked between chunks; it is not a strict whole-search latency guarantee. Redirects are rejected. User profile data, location text, and credentials are not sent to these public endpoints; filters run locally.

Each listing needs a positive posting ID and internal job ID, valid plain-text title/location fields, and an HTTPS original link that matches its board/employer and exact posting ID. Prospect/talent-network records are omitted. IDs are namespaced by board, and duplicates are removed. Invalid records are omitted and counted. A nonempty response with only rejected job records fails validation rather than becoming a successful empty search.

Each board check records status, successful-check time, HTTP status when available, accepted/rejected counts, and a safe failure category. Raw exception bodies are not displayed or saved. A partial failure shows valid-board results with an omission warning. All-board failure raises a sanitized error and exposes source checks. A successful zero-match response remains distinct from provider failure. In particular, zero literal Tucson matches say nothing about other employers, nearby locations, or remote roles.

The optional Adzuna adapter appears only with `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`. It remains a separate explicit choice, with no silent provider fallback. Its internship option changes the provider query rather than enforcing a title filter. This unit adds input/download bounds to that adapter, but does not establish live Adzuna operation or equivalent source validation.

## Verification

The complete suite passes **586 tests**, including **96 opportunity cases** and **28 Streamlit interactions**. Controlled cases cover metadata normalization, posting identity and URL binding, dates, local filters, size/status/schema limits, prospect omission, deduplication, genuine empty results, partial/all-source failure, sanitized diagnostics, explicit cache reuse and expiry, profile invalidation, optional Adzuna routing, CLI reports, and UI behavior. These fixtures establish behavior; they are not real job records or live-source success measurements.

The dated [public-source observations](evidence/opportunity_checks_2026-11-04.json) retain both the initial run and the later bounded AI recheck, with implementation hashes. The initial run had five successful filter cases and one all-source error. It predates the structured all-source diagnostic patch, so the specific failed-source cause is unknown. It has not been relabeled as success or a confirmed timeout.

| Live case | Observation |
| --- | --- |
| AI/ML, all listed locations | Initial request failed; one later bounded recheck succeeded, 41 matches, ten shown |
| Embedded, all listed locations | 11 matches, ten shown |
| AI/ML internship/co-op titles | One match |
| Embedded internship/co-op titles | Two matches |
| Embedded, literal Tucson location | Zero matches from successfully checked boards |
| AI/ML, updated within seven days | 14 matches, ten shown |

All successful observations received HTTP 200 from both boards and validated 322 Samsara plus 93 Nuro postings with zero rejected records. The successful observations took roughly 2.4–4.9 seconds; the initial error took about six seconds. These are individual observations, not a latency benchmark or uptime guarantee. No credentials, embeddings, or generation calls were used.

To reproduce the public check from the repository root:

```bash
python scripts/check_opportunities.py --career embedded --internship
python scripts/check_opportunities.py --career ai_ml --updated-within 7
```

The CLI saves a dated JSON report to `.cache/opportunity_checks.json` by default, including implementation hashes and source checks. `--output` changes the destination. Exit zero means all configured boards were verified and no records were rejected; a valid empty search can pass. Exit one retains failed or degraded observations, including safe per-source diagnostics when available. Current results may differ from the saved November 4 observations.

Next, expand and review employer/role coverage, decide whether a broader geography-aware provider is needed, and run independent student checks. Live Adzuna verification remains pending credentials. Wider employment coverage and qualification matching are separate future work.
