# Student opportunity coverage

Implemented and verified November 5, 2026. The public employer-board search now includes [Anduril Industries](https://www.anduril.com/open-roles) alongside Samsara and Nuro. The Opportunities form adds a separate “New grad / entry-level” title filter and retains internship/co-op filtering. These are local title matches, not qualification decisions or market-wide coverage.

## Reviewed third employer

The configured `andurilindustries` token is supported by employer postings on [Greenhouse](https://job-boards.greenhouse.io/andurilindustries/jobs/5148079007). Its metadata is read through the [documented public Job Board API](https://developers.greenhouse.io/job-board.html), without authentication or job-description downloads. A scoped metadata inspection accepted 2,592 records, all identifying Anduril Industries, with zero rejected records. This is a dated source observation, not a fixed future count.

`EmployerBoard` now permits a standard Greenhouse-hosted posting base on a different host from the employer's careers site, only when the base path is exactly `/{configured_token}/jobs/` and the URL style uses posting IDs in the path. Each returned link still needs HTTPS, the exact configured token/posting ID, permitted query parameters, and a matching employer name when the provider supplies it. Other Greenhouse tokens, lookalike hosts, mismatched IDs, unsupported paths, and redirects remain rejected. Both standard Greenhouse posting hostnames are supported.

The existing caps remain **three boards**, three workers, 4,000 raw records and 3 MB decoded JSON per board, and ten displayed matches. This fills the third available board slot rather than widening those limits. The public endpoint receives no career, role-level, location, completion, or credential data; filtering happens locally. Opportunity requests retain their existing single-attempt transport behavior; the academic/resource retry layer is separate.

## Role-title choices

| Choice | Behavior |
| --- | --- |
| All levels | Existing career-title filtering, without a seniority restriction |
| Internship / co-op | Requires an internship or co-op term in the title |
| New grad / entry-level | Requires an explicit supported early-career label and excludes internship/senior/leadership titles |

Supported early-career labels include new grad/graduate, recent graduate, university graduate, entry-level, early career, and junior. Senior, Sr., staff, principal, lead, manager, director, head, distinguished, and executive labels exclude a title from this filter. Internship and early-career filters are mutually exclusive. Unicode dash variants are normalized for title matching while the original displayed title is retained.

Titles such as “Engineer I,” generic “Graduate Research Scientist,” and unlisted labels are not inferred to be entry-level. A title must also meet the existing direction/engineering-role filters and avoid the existing recruiting/sales/marketing exclusions. Consequently, a generic software internship without an explicit AI/ML or embedded title signal can remain outside the result set. Neither this filter nor a zero-match result establishes degree requirements, experience fit, eligibility, geographic coverage, or the absence of other jobs.

The location and listing-update filters still compose with the role choice. The optional Adzuna path keeps its separate “Prefer internship search terms” behavior; it does not claim the new title filter and rejects that option at the backend boundary.

## Result and cache identity

Policy `p07-opportunity-title-filters-v2` records the role filter in `JobSearchResult.role_filter`. The interface labels the **displayed result's** filter, so an unsubmitted form change cannot relabel old results. Searches still run only on the action button, and widget rerenders do not fetch listings.

Public results also record `source_scope_hash`, computed from the validated board configuration and title-policy version. Explicit 20-minute reuse now requires the same role flags, direction, literal location, update window, provider, and configuration/policy fingerprint. A source or policy change forces a new request. The same captured board list used for the fingerprint is passed to the search. A returned nonempty scope hash for a different configuration is rejected. Legacy/injected result objects without the new optional metadata remain compatible; normal public searches supply it.

Fresh requests remain the default. Reuse preserves the original retrieval timestamp and is visibly labeled. Failed searches clear the old visible result and expose source diagnostics; partial success retains only valid-board results with omission warnings. No persistent job database or background refresh job is added.

## Verification and dated observations

The complete suite passes **992 tests**, including **47 new student-opportunity cases**, the previous 96 opportunity cases, and **46 Streamlit interactions**. New cases cover positive/negative title labels, Unicode dashes, internship separation, local location/date composition, hosted-board bindings, partial/all-source failures, explicit cache reuse, changed source/policy identity, unsupported Adzuna filtering, CLI arguments, result labels, and rerender boundaries.

The [November 5 evidence](evidence/student_opportunities_2026-11-05.json) retains all live attempts:

| Case | Observation |
| --- | --- |
| Embedded internship/co-op titles | All three boards verified; six matching listings |
| Embedded new-grad/entry-level titles | Initial request timed out at all three boards; failure retained |
| AI/ML new-grad/entry-level titles | All three boards verified; one matching listing |
| Embedded early-career bounded recheck | One explicit recheck verified all three boards; four matching listings |

Successful requests accepted 305 Samsara, 94 Nuro, and 2,592 Anduril records with zero rejections. Their returned metadata and source dates are retained in the evidence. These counts describe three configured employers at those timestamps, not the job market, qualification accuracy, or permanent availability. The failed request is not a zero-match result, and the later recheck does not erase it. There is no automatic opportunity retry or provider fallback.

All eight local readiness checks passed in the production-only Python environment, including real loopback server liveness and the offline preview. No credentials, embeddings, or generation requests were used in the opportunity verification. The saved academic corpus, frozen retrieval labels/metrics, earlier evidence, and submitted midproject artifacts are unchanged.

Run the public checks in PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts/check_opportunities.py --career embedded --internship
.\.venv\Scripts\python.exe scripts/check_opportunities.py --career embedded --early-career
.\.venv\Scripts\python.exe scripts/check_opportunities.py --career ai_ml --early-career
```

The two role flags cannot be combined. In the app, choose **Employer boards**, a role-title option, and **Available Opportunities**. Check the original listing for current availability and requirements. Broader employer/provider coverage, geography-aware search, Adzuna live verification, and independent student review remain open.
