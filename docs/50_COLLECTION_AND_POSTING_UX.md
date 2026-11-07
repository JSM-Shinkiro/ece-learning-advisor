# Collection browsing and posting feedback

Team P07 · November 7, 2026 · ECE Learning Advisor

Courses & Resources now has local search, type/direction filters, a matching count, a clear empty state and reset. Opportunity searches, paging and posting checks run in their own UI fragment. A posting check shows its loading feedback beside the selected listing, with the saved search still on screen.

## Collection browsing

Search accepts course codes with or without spaces, titles and topics. Multiple search words narrow the results; text is treated literally. The **Type** filter selects courses/resources, and **Direction** selects all, AI/ML or embedded. Shared records remain available in either direction. Filters describe the current source collection and do not change the student's career direction, profile, academic rules or recommendation ranking.

The count excludes career-mapping records. A no-match message suggests a broader search or reset. **Reset filters** restores the full collection. Opening a record shows its summary, course credits/catalog or resource version, original source links and dated check/snapshot labels. Closed records do not construct their source-detail controls.

These controls rerun only the collection fragment. They do not check websites, call a model, or regenerate the roadmap. Filter values persist through normal full-app/profile updates. The collection reads the latest active catalog after an advisor result, including source overlays and supported discoveries.

## Posting checks

The click callback records a single intent bound to the exact displayed search result, posting ID and page. It performs no HTTP work. The opportunities fragment consumes that intent once, shows **Checking posting details...** in the selected card, and invokes the existing source-bound checker.

A new selection clears the previous posting check before rendering the listing rows, preventing two different checked descriptions from appearing at once. Existing retry/transport diagnostics, metadata-change messages, source dates and failure labels are preserved. A failed detail check keeps the current search results and clears older verified description content.

Search/page/profile changes discard a queued intent. Even if a check has already started, the backend rechecks the current result/page before accepting its return. A stale response cannot overwrite a newer scope. The actual employer request retains its existing bounded HTTP/retry behavior and runs synchronously within this fragment; the loading message communicates that wait rather than guaranteeing a fast network response.

Only an explicit action checks a posting. Scrolling, opening collection records, resetting filters and normal rerenders do not repeat it. Opportunity searches keep their current explicit-search and optional 20-minute reuse policy.

## Implementation and checks

The two panels now have small UI modules (`collection_ui.py`, `opportunity_ui.py`), with shared source-date rendering and a pure collection filter. Request intents are session-local; no new database, model integration or package dependency is added.

Regression checks cover spaced/case-insensitive course search, combined filters, literal/no-match input, reset, lazy details, profile preservation, stale intent rejection and late verified posting returns after search/page/profile changes. The initial targeted run found that the first posting's description could remain rendered when selecting a second one; clearing it when queuing the new selection resolves that case.

The controlled browser workflow adds collection filtering, a 390-pixel phone viewport, deliberately delayed posting feedback, and failed-recheck retention to the existing AI interaction checks. Its provider and employer data are explicit fixtures; all server-side HTTP is blocked. These checks do not establish real employer availability, live network speed, recommendation quality or participant feedback.

Verification revisions and results are recorded in [the dated evidence record](evidence/collection_posting_ux_2026-11-07.json). Current readiness is tracked in [FINAL_READINESS.md](FINAL_READINESS.md).
