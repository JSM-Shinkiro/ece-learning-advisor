# Paging through an opportunity search

Development update: November 5, 2026 (MST); verification records use UTC timestamps. Public employer-board searches now retain up to 200 matched listings and display ten per page. Previously, only the first ten matches could be opened in the app even when the matching count was larger.

## Student behavior

Submit **Available Opportunities**, then use **Next listings** or **Previous listings**. The interface shows the displayed range, full matching count, and page number. Empty or single-page results have no navigation controls; the first/last page disables the corresponding button. When more than 200 listings match, a notice explains the retained limit and suggests narrowing the filters.

Paging reads the saved search snapshot. It makes no board, posting-detail, embedding, or generation requests. It preserves the original retrieval timestamp, source checks, warnings, title-filter label, and ordering by provider update date and posting ID. Unsubmitted form edits do not change the saved search. Paging can continue after the snapshot is old; the timestamp remains visible and the interface says sources are not checked again. The 20-minute reuse limit applies to a new explicit reuse action, not to reading pages already in the session.

A new fresh search or explicit matching-result reuse starts on page one and clears posting-detail state. Changing a page also clears the previous checked description. **Check posting details** remains an explicit fresh request for one posting on the displayed page; a posting from another page cannot be checked through that action until it is displayed. Profile transitions remove the search, cache, page errors, and descriptions together.

## Backend contract

`JobSearchResult` appends optional `snapshot_listings` and a zero-based `page`. Existing unpaged/injected results and the separate Adzuna adapter retain their old behavior. Normal public searches supply the snapshot. Filtering, validation, and deduplication happen before the 200-match retention limit; the full matching count is kept separately. The existing three-board, three-worker, 4,000-record/3 MB-per-board transport budgets and single-attempt behavior are unchanged.

`page_info` validates the retained count, unique posting identities, required record fields, page bounds, and agreement between the displayed page and its snapshot. `request_opportunity_page` accepts an absolute integer page, binds the current configured board/policy scope, and revalidates the target page's posting identity, employer, and HTTPS links before display. It returns a new view while leaving the original cached result and metadata unchanged. Legacy/injected results may omit the optional scope fingerprint; target posting/board checks still apply. Normal public searches always supply the fingerprint. Invalid pages and changed configurations require a new search; no fallback provider or remote page request is attempted.

Policy `p07-opportunity-pages-v3` changes the configuration/policy fingerprint so an older search is not silently reused under the new snapshot contract. A new search clears its visible result and page/detail errors before validation; failed source requests remain failures. No persistent database or background refresh task is introduced. A future persistent content database still requires automatic refresh in addition to on-use checks.

## Command line

```powershell
.\.venv\Scripts\python.exe scripts/check_opportunities.py --career embedded --page 2
.\.venv\Scripts\python.exe scripts/check_opportunities.py --career embedded --page 2 --check-first-detail
```

Each CLI invocation starts a fresh search, then selects a local page without additional board requests. CLI pages are numbered 1–20. A page outside the actual returned snapshot is an unsuccessful check. The optional detail flag checks the first posting on the selected page. Reports retain pagination metadata and the displayed listings, while omitting the complete retained list and description text. Existing default CLI searches still show page one and do not request descriptions.

## Verification and limits

The full suite passes **1,092 tests**, including **35 new paging cases** and **59 Streamlit interactions** (eight added here). Controlled cases verify zero/one/partial/full/capped snapshots, complete traversal without HTTP requests or duplicate IDs, date/order/filter preservation, unchanged cached results, invalid inputs and source scope, failed searches, profile resets, explicit reuse, later-page detail checks, CLI bounds, and interface controls. All eight production-runtime checks pass, including loopback liveness and the offline preview.

Two actual bounded source attempts were made: the initial embedded all-level search and one explicit recheck. **All three employer boards timed out in both attempts.** Each attempt made three metadata GETs. Neither produced a validated snapshot, so no live page traversal or later-page description was verified in this unit. Neither failure is treated as a zero-match result. No further retry, timeout change, or provider fallback was added. These failures do not establish a root cause or erase earlier successful source checks.

The [dated evidence](evidence/opportunity_paging_2026-11-05.json) preserves both failures, implementation fingerprints, automated results, and runtime checks. No credentials or model calls were used. Live paging validation remains open. Wider employer/provider coverage, geography-aware search, independent student review, and public hosting also remain open. Earlier observations, frozen academic/evaluation inputs, and submitted midproject artifacts are unchanged.

## November 6 follow-up

The later [opportunity-recovery unit](34_OPPORTUNITY_RECOVERY.md) verified all three boards and traversed all 20 retained pages of a 262-match embedded search, with no additional requests, reordered/duplicate IDs, or changed retrieval dates. One posting on page two and explicit metadata reuse also passed. All live requests succeeded on their first attempts, so the observation does not establish a live retry improvement or a root cause for the earlier failures. The source guards now permit one transient retry and expose attempt diagnostics. The original failed attempts above remain unchanged; the previously blocked live paging path is verified for the later dated snapshot.
