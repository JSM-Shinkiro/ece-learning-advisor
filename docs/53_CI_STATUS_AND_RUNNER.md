# Clear CI status and a fixed Ubuntu release

Team P07 · November 8, 2026 · ECE Learning Advisor

The reported screenshot matches [run 42454804113](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/42454804113). Its Linux artifact is 30,527 bytes (29.8 KiB), with digest `b75e3a48f0c8b05eee9447204da424edfd7131ccb99516f6c21ebfb56090c3f0`. The browser job records two exit-code-1 errors: the current and baseline timing commands both completed zero of five full sessions at the reopening boundary. All 26 UI acceptance gates and the Linux/Windows tests passed in that run.

The collector's close-animation wait fixes that issue. The following [run 42455351082](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/42455351082) passes both complete timing cohorts, all 26 browser gates, and all 1,648 tests/nine runtime checks on Linux and Windows. [The inspector development record](52_LIGHTWEIGHT_INSPECTOR.md) preserves both attempts. The old run keeps its original failed conclusion; use the current commit/run when checking the app's status.

## Runner notice

Both the failed and successful browser job logs identify the actual image as **Ubuntu 26.04**. The notice describes GitHub's rolling `ubuntu-latest` migration, [announced by the runner-images team](https://github.com/actions/runner-images/issues/14748). It is separate from the timing collector's reopening failure. The workflow now explicitly selects `ubuntu-26.04` for Linux backend and browser jobs, retaining the OS release already used by the successful run. This fixes the release selection, not an immutable image build: runner patch updates still occur. Windows remains a separately checked matrix platform.

## Readable outcomes

The browser job now writes a **Browser checks** summary with the current commit/run and distinct rows for:

- Student app browser workflow.
- Reviewer workspace.
- Controlled AI and browsing.
- Current app offline preview timings.
- Fixed-baseline offline preview timings.

Each row shows PASS, FAIL, MISSING or INVALID, with actual passed/total counts. Successful v2 timing rows show first-inspector and reopening medians. Incomplete timing rows name only fixed failed-stage labels and their counts; exception messages, profiles, URLs and arbitrary report text are not copied into the summary. Missing, malformed, contradictory or incomplete reports fail the summary command. No failed check is skipped or converted into success.

The Markdown is attached to the GitHub job summary and retained beside the raw JSON reports in the browser artifact. Timing commands also print the fixed failed-stage/count information directly, so a failed command has a useful explanation beyond its exit code. Existing reports are never overwritten by the summary command. Historical failures remain intact.

For a saved artifact, extract its report files into one directory and run:

```bash
python scripts/summarize_browser_ci.py --reports-dir output/ci --output output/ci/browser-summary.md
```

Use a new output path. In Actions, `--github-summary` additionally appends to the provided step-summary file. This helper uses the Python standard library and runs after browser steps even when an earlier check fails. Controlled fixtures and offline measurements remain distinct from real AI, independent evaluation and participant feedback.

## Scope and readiness

This unit changes CI reproducibility and diagnostics. The student app, sources, ranking, academic conditions, profiles and reviewed/evaluation inputs are unchanged. App/full-submission readiness remain approximately **95% / 72%**, as engineering planning judgments. Independent evaluation, the voluntary student pilot, real-AI/final-release measurements and final report/slides/demo remain open. See [final readiness](FINAL_READINESS.md).
