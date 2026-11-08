# Repeated browser performance measurements

Team P07 · November 7, 2026 · ECE Learning Advisor

This record preserves the original **v1** experiment and its results. The current [v2 collector and lightweight inspector](52_LIGHTWEIGHT_INSPECTOR.md) add same-page reopening and a common ranking-visualization-plus-trace-download boundary for native/Plotly comparisons. Do not combine the differently defined v1/v2 inspector metrics as one series.

The optional collector measures five fresh Chromium sessions through the actual production launcher. Each session submits the unchanged default incoming AI/ML profile once, then opens the inspector. It uses the saved runtime collection, no source downloads, blank credentials and no AI. The application itself is unchanged by this measurement step.

## Reproduce

```bash
python -m pip install -r requirements-browser.txt
python -m playwright install --with-deps --only-shell chromium
python scripts/measure_browser.py --samples 5 --output output/performance/preview-01.json
```

Choose a new output path for each run; existing reports are never overwritten. Two to twenty sessions are supported. The script starts an isolated loopback production process with the same prefixed path as browser acceptance, then stops it. There is no public-host or live-provider mode. The ordinary app and pytest suite do not require Playwright.

## What the numbers mean

| Metric | Boundary and clock |
| --- | --- |
| Navigation to interactive | Driver navigation begins → enabled visible submit button and successful initial Streamlit script completion; Python monotonic |
| Request feedback DOM | Native submit click → laid-out request progress or completed status summary; page `performance.now()` |
| Roadmap controls ready | Native submit click → first enabled, laid-out “Mark completed” control on this session's first roadmap; page clock |
| Submit to script finished | Driver click starts → successful full Streamlit script completion; Python monotonic, including driver/polling overhead |
| Inspector plot ready | Native inspector click → laid-out Plotly element with initialized data; page clock, measured separately from roadmap generation |

DOM observation runs on animation frames after mutations. It includes controls outside the current viewport and is not physical paint, FCP, LCP, field INP or a participant's perceived response time. Only the fixed status kind (`progress` or `complete`) is retained; a fast request that first exposes completion is not claimed to have shown intermediate progress. Inspector timing includes that fresh context's first Plotly load/initialization.

Sessions have fresh nonpersistent contexts but share one browser and server process. Same-origin request routing blocks unexpected external browser requests and disables the browser HTTP cache, as documented in the [Playwright BrowserContext API](https://playwright.dev/python/docs/api/class-browsercontext#browser-context-route). These samples are not a cold-versus-warm cache comparison. No clocks from different processes are subtracted. Collection fingerprints, app revision/dirty flag, platform, Python/browser versions, logical CPU count and server timing fields accompany the samples.

Each real trace is downloaded through the inspector, validated as offline keyword preview, reduced to numeric timing/provenance fields and deleted from temporary storage. Profiles, questions, source excerpts, URLs, raw browser frames and raw errors are excluded from the report. A changed collection, page error, external browser request or reconnection invalidates that sample. Failed/partial rows remain visible; summary min/median/max use successful complete rows only. There is no p95 estimate or absolute speed threshold for this small sample.

## Verification and remaining evidence

The browser CI job runs the collector independently after the existing acceptance workflows, including when an earlier gate fails, and retains its JSON report. Unit checks cover scope rejection, real-trace compatibility, finite durations, failure retention, optional dependencies, sanitized failure output and prevention of overwriting earlier evidence before any process starts.

The first CI attempt passed all 1,640 tests and nine runtime checks on Linux and Windows. Its existing phone workflow timed out clicking the sidebar-collapse button after resizing: the control could disappear during the responsive transition. The checker now explicitly closes the sidebar at desktop width, verifies its collapsed state, then resizes and retains the same phone interaction/overflow assertions. That failed attempt remains part of the evidence; it did not run the new timing collector. No app behavior changed in this correction.

## Measured result

Verified revision `edf5255b8f881c7993b697da2eba1158233e5e6f` passes [CI run 42445221606](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/42445221606): all **1,640 tests** and **nine runtime checks** on Linux and Windows, all **25 browser acceptance gates**, and **five of five** timing sessions. The downloaded browser artifact was SHA-256 verified; reports, sample rows, original failures and frozen-input hashes are preserved in [the dated evidence](evidence/browser_performance_2026-11-07.json).

The measurement runner uses Linux x86-64 with four logical CPUs, Python 3.12.16 and Chromium 151.0.7922.34, at a 1,500 × 1,100 viewport. The checkout was clean and the corpus fingerprint was identical in all five samples. These machine/session details bound the observations; they do not predict a student device.

| Metric | n | Minimum (ms) | Median (ms) | Maximum (ms) |
| --- | --- | --- | --- | --- |
| Navigation to interactive | 5 | 852.286 | 964.719 | 1,465.907 |
| Request feedback DOM | 5 | 225.900 | 250.000 | 271.500 |
| Roadmap controls ready | 5 | 347.700 | 459.000 | 604.500 |
| Submit to successful script completion | 5 | 517.636 | 539.612 | 762.325 |
| First inspector plot ready | 5 | 1,655.200 | 1,711.900 | 1,875.700 |

Server result-assembly total was separately 9.788 ms at the median (9.226–16.038 ms range). It excludes provider cleanup and browser rendering. No cross-clock subtraction is used to estimate a rendering cost. All five sessions exposed a progress summary before their first roadmap controls.

The roadmap controls appeared within 0.605 seconds in these five offline samples. First inspector loading was the larger visible DOM wait, approximately 1.71 seconds at the median, with its first Plotly load included. The inspector remains separate from the usable plan. This is a useful next optimization target; warm reopening needs its own measurement before assigning the cost to either rendering or asset loading. No before/after performance improvement is claimed by this collector.

App readiness remains approximately **94%**; full-submission readiness rises to approximately **72%** by adding reproducible preview evidence. These are planning judgments. The overall performance gate remains partial.

Real-provider/source latency, hosted or phone timing, repeated cache-state cohorts, independent judgments and voluntary student usability observations remain separate work. Rerun against the frozen final revision before using these development measurements in the final report. Readiness estimates are recorded in [FINAL_READINESS.md](FINAL_READINESS.md).
