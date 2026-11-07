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

Browser HTTP requests to other origins are blocked. The report retains check outcomes, scoped interaction times, browser version, blocked-request counts, and WebSocket/page-error counts. It records neither raw browser errors nor console messages, profile fields, frame payloads, screenshots, credentials, or the supplied target URL. Browser blocking does not measure server-side network calls. Failure type and checker line identify where to investigate without copying raw diagnostics into artifacts. Existing reports cannot be overwritten.

## Verification status

All 1,524 local tests pass, including 13 new ordinary unit/CLI controls for URL rejection, report preservation, sanitized missing-browser failures, offline launcher settings, and cleanup/reaping. The local workspace cannot launch Chromium because Unix sockets are restricted; the browser download endpoint also returns an unavailable-page response. The retained local attempt is a failure, not a browser acceptance result. The Linux CI job installs the optional dependencies/browser and will run all eight acceptance gates. Until its actual result is inspected, browser acceptance remains unverified.

All nine local readiness checks pass. [Dated evidence](evidence/browser_acceptance_2026-11-07.json) retains the local browser startup failure and preserved input hashes. Linux and Windows backend tests and nine readiness checks stay separate from the Linux Chromium job. Each job retains its own report for fourteen days. See [final readiness](FINAL_READINESS.md) for the remaining submission gates.
