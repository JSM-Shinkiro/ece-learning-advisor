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

## Profile synchronization fix

The browser flow exposed a real regression: after marking current ECE101 completed, the downloaded profile was correct but the form still showed the old current selection and an empty completed picker. Adding manual current MATH129 then resubmitting silently undid the completion. Changed widget defaults after deleting session keys did not update the browser's retained keyed values.

Accepted profile transitions now publish explicit widget values before the form is created. This applies to completion, profile restore, direction choices, and submitted edits. Ordinary rerenders retain pending edits. The form uses this synchronized state rather than competing defaults; grades remain unknown until supplied, and imported fields outside the form remain in the canonical profile. Profile downloads use `on_click="ignore"` to avoid an extra app rerun.

The browser checks assert both pickers immediately after completion and verify the later edit/export. The existing Streamlit regression case also asserts `set_value` and the actual client values, covering the distinction AppTest previously missed. The checker waits for successful-script completion, finishes field blur before clicking submit, and uses the dropdown's explicit Open control after scrolling it into view.

## Verified result

The later [request-progress unit](46_REQUEST_PROGRESS.md) adds a ninth browser gate for visible stage history and passes 1,539 tests on both OSes. The original browser milestone's dated results below are retained.

Revision `11e26d567b503d79dee0ef437cf369918aba1d83` passes [run 42363890309](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/42363890309):

| Environment | Observed result |
| --- | --- |
| Local Python 3.12.14 | 1,524 tests and all nine runtime readiness checks pass |
| Linux / Python 3.12 | 1,524 tests and all nine runtime readiness checks pass |
| Windows / Python 3.12 | 1,524 tests and all nine runtime readiness checks pass |
| Linux / Chromium 151.0.7922.34 | All eight real-browser acceptance gates pass |
| Two simultaneous browser contexts | Each has one open bidirectional Streamlit WebSocket, zero page JavaScript errors, and independent profile state |

The successful browser artifact was downloaded and its ZIP SHA-256 verified. Session A records eight sent/2,030 received frames; session B records three sent/761 received frames. Neither stream closes during the workflow. These are protocol observations from controlled local sessions on a CI runner. Interaction durations in the report include scripted UI work; they are not a live-AI latency benchmark or participant study.

Thirteen new unit/CLI cases cover plain URL validation, existing-report preservation, sanitized missing-browser failures, offline launcher settings, and cleanup/reaping. There are still 73 Streamlit interactions overall. All eight frozen/evaluation/review input hashes are unchanged, and all 408 review grades remain blank. No independent quality score or public-host validation is added.

## Retained failures and scope

[Dated evidence](evidence/browser_acceptance_2026-11-07.json) retains earlier attempts and the successful follow-up separately:

| Attempt | Finding |
| --- | --- |
| Local workspace | Browser binaries cannot be downloaded through the available endpoint; system Chromium startup is blocked by Unix-socket restrictions. This is a failed local attempt. |
| `f206cba`, run 42361087214 | Initial browser roadmap passes; second form assertion fails. One new Windows test also assumes Linux path separators. |
| `d54667c` / `71b1339` | Backend path assertion is fixed. Rerun waits alone do not resolve the browser action; diagnostics show the second click never reaches the button. |
| `261ed0b`, run 42362982355 | Focused submit clicks pass current-course/completion checks and expose the actual stale-form regression on a later edit. |
| `d45515c` / `ea592e5` | Explicit profile values fix the regression through edit/export; dropdown-opening checks still fail after sidebar scrolling. |
| `11e26d5`, run 42363890309 | Explicit dropdown opening completes all eight acceptance gates; Linux/Windows tests and readiness also pass. |

Failures are not relabeled as passes. The Linux browser job uses an isolated loopback server through the production launcher; public hosting, reverse proxies, TLS, other browser engines, AI behavior, independent grading and student usability remain separate checks. Reports are retained in CI for fourteen days, with durable observations and hashes in the dated evidence. See [final readiness](FINAL_READINESS.md) for the remaining submission work.
