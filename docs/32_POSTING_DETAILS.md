# On-demand posting descriptions

Implemented and verified November 6, 2026 (UTC). The Opportunities tab now lets a student check the actual description of one displayed employer posting. Title-based search remains separate from reviewing the employer's requirements. The app displays source text without inferring qualifications or introducing job text into the academic RAG pipeline.

## Student interaction

1. Submit an employer-board search in **Opportunities**.
2. Select **Check posting details** on a displayed result.
3. Read the **Checked posting description** and its separate successful check time. Use **Open checked posting** for the original page.

Every click requests that posting again. Ordinary widget rerenders or opening an expander make no requests and retain the original check time. The search's metadata timestamp and optional 20-minute reuse do not establish description freshness. Only the most recently checked posting is retained. A new search, including explicit result reuse, or a profile change clears the description and its error state.

Descriptions retain paragraphs and list boundaries, with employer HTML converted to plain text. Scripts, styles, templates, and noscript content are omitted; links, images, and employer markup are not rendered. The checked title, employer, location, original link, and available provider dates accompany the description. If title, location, link, publication date, or update date differs from the search snapshot, a notice lists the changed fields. The original search is not silently overwritten or refiltered.

## Source and failure contract

`src/opportunity_details.py` uses the [documented public Greenhouse retrieve-job endpoint](https://docs.greenhouse.io/job-board.html#retrieve-a-job). It constructs the request from the configured board token and selected numeric posting ID. It never fetches a supplied application URL. No credentials, profile text, search terms, applicant fields, or application submissions are sent.

The service requires a uniquely selected posting from the currently displayed public search and the current board/policy fingerprint. Results without the optional fingerprint remain compatible with the previous injected/legacy result contract. Normal public searches always supply it. The returned public posting ID, employer name when supplied, internal job identity, and HTTPS posting URL must pass the existing identity/source checks. A prospect post, wrong posting ID, wrong employer, off-board link, missing visible description, or malformed response cannot become a successful check.

| Outcome | Display and retained state |
| --- | --- |
| Verified | Validated source text and successful check time |
| HTTP 404/410 | Posting not found at the source; no description and no assertion that the position is closed |
| Timeout, connection failure, rate limit, or other HTTP error | Source unavailable; no stale description |
| Invalid identity, content, format, size, or elapsed guard | Response could not be validated; no description |

Each action makes **one GET**, without redirects, automatic retries, or provider fallback. It shares the existing 3 MB decoded JSON guard and HTTPX phase timeouts (6 seconds read/write, 4 seconds connect/pool). The 12-second elapsed guard now checks headers, body chunks, and end-of-body, including an empty body. This remains cooperative around synchronous I/O, not a hard wall-clock cancellation deadline.

Raw HTML content is limited to 200,000 characters. At most 50,000 extracted characters are displayed; shortened text is explicitly labeled and links back to the original. A SHA-256 fingerprint and total extracted-character count cover the complete normalized text before display truncation. These establish snapshot identity, not source accuracy. Failed checks contain no source body, raw exception text, old description, or successful check time.

This adds no persistent job database, scheduled task, model call, application form, or eligibility rule. Broader employers/providers, geography-aware search, and independent student review remain open.

## Verification

The full suite passes **1,049 tests**, including **52 new posting-detail cases** and **51 Streamlit interactions** (five added in this unit). They cover all three configured board bindings, visible/escaped HTML, truncation and fingerprints, identity changes, invalid responses, stream interruption, elapsed guards, HTTP/rate-limit failures, source-scope changes, explicit request boundaries, failed rechecks, profile/search resets, and switching between postings. Interaction tests caught an unsupported Streamlit text argument during development; it was removed before the final passing suite. No real removal or rate-limit observation is claimed from controlled tests.

Both opt-in live checks passed in the production-only environment, with all three metadata boards verified and no rejected records:

| Search | Checked posting | Description observation |
| --- | --- | --- |
| Embedded internship/co-op | Anduril Industries · 2027 Guidance, Navigation, & Control Engineer Intern · `5268736007` | 6,017 extracted characters; no shortening or metadata change |
| AI/ML new-grad/entry-level | Nuro · Software Engineer, AI Platform - New Grad · `7351066` | 4,603 extracted characters; no shortening or metadata change |

These are dated public-source observations, not guarantees of future availability or qualification fit. Samsara's detail path is covered by controlled tests; no live Samsara description was checked in this unit. The [evidence](evidence/posting_details_2026-11-06.json) records source identities, provider/check dates, text lengths/hashes, and outcomes, without storing the descriptions. No credentials, embedding requests, or generation requests were used. All eight local runtime checks also pass, including loopback liveness and the offline preview.

Reproduce the opt-in checks in PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts/check_opportunities.py --career embedded --internship --check-first-detail
.\.venv\Scripts\python.exe scripts/check_opportunities.py --career ai_ml --early-career --check-first-detail
```

The additional flag checks only the first displayed match. A requested detail check with no selected match is reported as unsuccessful. Default CLI searches still request metadata only. Saved CLI detail evidence omits description text while retaining its identity, character count, fingerprint, and truncation flag. The academic corpus, frozen evaluation labels, earlier observations, and submitted midproject artifacts remain unchanged.
