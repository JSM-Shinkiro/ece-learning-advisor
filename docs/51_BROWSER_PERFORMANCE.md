# Repeated browser performance measurements

Team P07 · November 7, 2026 · ECE Learning Advisor

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

Real-provider/source latency, hosted or phone timing, repeated cache-state cohorts, independent judgments and voluntary student usability observations remain separate work. Rerun against the frozen final revision before using these development measurements in the final report. Readiness estimates are recorded in [FINAL_READINESS.md](FINAL_READINESS.md).
