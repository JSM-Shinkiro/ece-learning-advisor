# Real-browser acceptance

Implemented November 7, 2026. The optional Chromium check exercises the actual Streamlit frontend and production launcher. Existing AppTest and server-health checks remain useful, but do not establish a working browser upload/download or two real WebSocket sessions.

## Reproduce

```bash
python -m pip install -r requirements-browser.txt
python -m playwright install --with-deps --only-shell chromium
python scripts/check_browser.py --output output/browser-first.json
```

The default starts `scripts/serve.py` on an ephemeral loopback port under `/advisor-check/`, with blank provider credentials, source refresh and development mode disabled, and a temporary cache. It stops/reaps the server and closes both browser contexts on success or failure. Downloaded controlled profiles are temporary. `--executable-path` can select an already installed Chromium executable. Playwright is an optional development dependency, absent from the app's production requirements.

To validate an already running app, explicitly supply its URL:

```bash
python scripts/check_browser.py --url https://YOUR-HOST/advisor --output output/browser-host-first.json
```

Use a plain URL without credentials, query parameters, or fragments. This makes submissions in two temporary browser sessions using controlled profiles, with AI left off. A supplied host retains its server settings and may refresh official public sources; the checker does not reconfigure or deploy it. Authenticated hosts requiring interactive login are outside this command's current scope. A passing local run does not establish public availability, HTTPS/proxy support, AI latency, or participant usability.

## Acceptance gates

| Check | Expected behavior |
| --- | --- |
| Initial roadmap | UI loads; a submitted default profile produces ECE101 in preview; local AI is disabled and source snapshots are labeled |
| Current-course filtering | Current ECE101 remains visible in coursework and is absent from next-step cards |
| Completion transition | Mark completed moves ECE101 to completion with an unknown grade |
| Profile export | Real UI download includes manual current MATH129 and the controlled profile |
| Profile restore | After editing, real file upload restores every field in the downloaded profile |
| Session isolation | A second isolated browser context has an independent empty profile and can change it without changing the first |
| Unsupported request | Marine-biology request shows coverage clarification without course cards; the other session remains unchanged |
| WebSocket sessions | Both prefixed Streamlit streams exchange frames, remain open through the workflow, and have no page JavaScript errors |

Browser HTTP requests to other origins are blocked. The report retains check outcomes, scoped interaction times, browser version, blocked-request counts, and WebSocket/page-error counts. It records neither raw browser errors nor console messages, profile fields, frame payloads, credentials, or the supplied target URL. A failing isolated offline fixture can save a separate diagnostic screenshot; provided-host checks never do. Browser blocking does not measure server-side network calls. Failure type and checker line identify where to investigate without copying raw diagnostics into artifacts. Existing reports cannot be overwritten.

## Verification status

The initial [CI run](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/42361087214), revision `f206cba`, passes the initial real-browser roadmap, all 1,524 Linux tests and nine readiness checks on both operating systems. It fails the next browser profile assertion and one Windows-only assertion that assumed forward-slash path separators (1,523 Windows tests pass). Both failures remain recorded. The follow-up waits for Streamlit's successful-script completion messages before the next edit, checks selected controls before submitting, targets the uploader's actual file input, and uses platform-aware path parts in the test. Profile download now uses `on_click="ignore"` to avoid a redundant app rerun. Only protocol completion counts are retained; message contents are not stored. A successful follow-up is still required.

All 1,524 local tests pass, including 13 new ordinary unit/CLI controls for URL rejection, report preservation, sanitized missing-browser failures, offline launcher settings, and cleanup/reaping. The local workspace cannot launch Chromium because Unix sockets are restricted; the browser download endpoint also returns an unavailable-page response. The retained local attempt is a failure, not a browser acceptance result. The Linux CI job installs the optional dependencies/browser and will run all eight acceptance gates. Until its actual result is inspected, browser acceptance remains unverified.

All nine local readiness checks pass. [Dated evidence](evidence/browser_acceptance_2026-11-07.json) retains the local browser startup failure and preserved input hashes. Linux and Windows backend tests and nine readiness checks stay separate from the Linux Chromium job. Each job retains its own report for fourteen days. See [final readiness](FINAL_READINESS.md) for the remaining submission gates.

The first follow-up, revision `d54667c` / [run 42362437254](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/42362437254), still fails the second submission after both selected-control assertions pass. It records two successful completed scripts and only two outgoing frames: no new request is observed after the second button action. The rerun wait alone does not resolve this. Targeted count-only diagnostics and a screenshot of the isolated offline fixture are being added for investigation. Screenshots are never captured for a supplied host. This is an unresolved acceptance failure.

The diagnostic [run 42362743799](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/42362743799), revision `71b1339`, confirms the second pointer action never reaches the roadmap button: one actual button click, no invalid controls, no app exception, the expected direction still selected, and an open stream. The follow-up explicitly focuses the submit button before clicking so the multiselect finishes its blur/layout change before Playwright chooses the click point. This is an interaction-harness correction, not evidence of a backend validation failure. The first follow-up passes all 1,524 tests and nine readiness checks on both OSes. Full browser acceptance remains pending.

The focused-click [run 42362982355](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/42362982355), revision `261ed0b`, passes the initial roadmap, current-course filtering and completion/export checks. The next manual-current-course submission exposes an actual app regression: the form retains the old current ECE101 selection and empty completed picker, then sends those stale values back. The profile changes from one completed/no current to zero completed/two current when MATH129 is added. AppTest had accepted the changed defaults while the browser retained its keyed values. The fix explicitly publishes canonical profile values before creating widgets on profile transitions, rather than clearing keys and relying on defaults. The browser check now asserts both pickers immediately after completion; the existing Streamlit test also asserts explicit client-value updates. All 128 targeted checks pass; full verification is pending.

Revision `d45515c` / [run 42363431156](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/42363431156) confirms the regression fix through current-course filtering, explicit completion picker updates, a later manual-current edit, and profile export. The next dropdown action times out locating its target option after sidebar scrolling. The checker now focuses the combobox and opens it with ArrowDown before selecting the option. Restore/isolation acceptance remains pending.

The ArrowDown follow-up, revision `ea592e5` / [run 42363632983](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/42363632983), retains the same four passed gates. Its screenshot shows the dropdown remains collapsed. The next checker scrolls the control into view, uses its explicit Open button, and asserts `aria-expanded=true` before selecting an option. This separates opening failures from option-selection failures.
