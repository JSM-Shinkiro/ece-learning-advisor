# Lightweight ranking inspection

Team P07 · November 7, 2026 · ECE Learning Advisor

The inspector's simple ranking chart now uses native HTML and CSS bars. The original score table retains record/chunk identities, retrieval method, ranking score, BM25 and cosine values. Ranking order, source evidence, statement controls, trace download and academic decisions remain unchanged. Plotly still renders the real vector PCA view after a successful semantic/hybrid request.

## Rendering behavior

Opening **How this plan was made** remains a fragment operation. The closed inspector builds no chart, score table or trace JSON. In keyword preview, opening it no longer sends a Plotly chart or initializes that chart runtime. The native bars preserve a shared zero baseline, handle signed scores and all-zero results, and scale against the largest absolute score. Labels wrap at phone width; exact numeric values remain in the table and the displayed score's tooltip. All source labels and the method are escaped as literal text. There is no chart JavaScript.

PCA coordinates still come from the actual stored document/query vectors. Selecting another vector recomputes its displayed dot product, norms and cosine without regenerating the plan. Plotly is imported on that path. No provider, source, profile, ranking, cache or academic-rule behavior changes in this unit.

## Repeatable comparison

The timing collector advances to **v2** and observes the same functional inspector boundary for both renderers: a laid-out ranking visualization and an enabled trace-download button. It measures first opening, closes the fragment, verifies content removal and waits for the native expander's closing animation to finish, then measures reopening on the same page. JavaScript modules can remain in memory between openings. Browser HTTP caching remains disabled by the same-origin request guard. These are DOM observations, not physical paint or user-study results.

```bash
python scripts/measure_browser.py --samples 5 --output output/performance/native-01.json
git worktree add --detach .cache/inspector-baseline 88ab5849ffa42130765e3afb1f1eaba69280acc9
python scripts/measure_browser.py --app-root .cache/inspector-baseline --samples 5 --output output/performance/baseline-01.json
```

Both commands use the current collector, pinned installed dependencies, blank credentials, disabled source downloads and the unchanged default profile. `--app-root` selects a local checkout, starts that checkout's production launcher and records its own Git revision independently from the collector's revision. It accepts no remote host. Use new report paths. The baseline worktree can be removed with `git worktree remove .cache/inspector-baseline` after collecting evidence.

Browser CI checks out that fixed baseline separately and measures five sessions for each version on the same runner, current app first and baseline second. Each cohort uses a separate production server/browser process and fresh contexts per sample. The samples are small and ordered, with shared-runner variability; no latency threshold, p95 or statistical significance is claimed. Historical v1 results and their original boundaries remain in [the earlier measurement record](51_BROWSER_PERFORMANCE.md).

The added browser gate checks the native ranking at 390-pixel phone width, trace-download availability, absence of page overflow and no full-app/provider rerun. Targeted mobile/desktop ranking screenshots accompany the controlled browser artifact. Unit/UI checks cover signed/zero/extreme scores, escaped markup, lazy rendering, and actual PCA/cosine preservation.

The [first CI attempt](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/42454804113) passed all 1,648 tests and nine runtime checks on Linux/Windows, plus all 26 browser acceptance gates. Both timing cohorts failed at reopening: the collector clicked again after fragment completion/content removal while the native `details.open` flag could still describe the closing animation. The collector now explicitly waits for `open == false` before the next click. The failed samples remain retained and are excluded from successful-cohort summaries; they are not accepted performance results.

## Verified result

Revision `dd7e764a40e2bd43c71981c6ee65eb7bf3cc5590` passes [CI run 42455351082](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/42455351082): **1,648 tests** and **nine runtime checks** on Linux and Windows, **26 browser acceptance gates** and **five complete timing sessions per version**. The current app and fixed baseline have the same corpus fingerprint, clean checkouts, Python 3.12.16, Chromium 151.0.7922.34 and Linux x86-64/four logical CPUs on this runner. The collector revision is recorded separately for both.

| Inspector boundary | Version | n | Minimum (ms) | Median (ms) | Maximum (ms) |
| --- | --- | --- | --- | --- | --- |
| First opening | Baseline / Plotly | 5 | 1,583.8 | 1,608.4 | 1,833.0 |
| First opening | Current / native | 5 | 663.7 | 686.7 | 762.2 |
| Reopening | Baseline / Plotly | 5 | 342.9 | 361.8 | 368.7 |
| Reopening | Current / native | 5 | 295.5 | 307.8 | 319.0 |

The observed median first-opening time fell from 1.608 to 0.687 seconds, a 57.3% reduction within this experiment. Reopening is measured after the close animation and content removal, on the same page. The smaller reopening difference is consistent with reuse of already loaded modules, but this experiment does not isolate every rendering, transfer or server cost. No improvement in live-AI/source latency or field performance is established.

Current preview request feedback/roadmap controls were separately ready at medians of 221.2/453.4 ms. The roadmap remains usable before opening the inspector. No roadmap speed improvement is claimed by this rendering change.

[The dated evidence](evidence/lightweight_inspector_2026-11-07.json) retains both CI attempts, all successful and failed sample rows, artifact digests, reviewed screenshot hashes and eight unchanged frozen/review input hashes. All 408 saved grades remain blank. The browser artifact download was SHA-256 verified.

App readiness rises to approximately **95%** by closing this preview inspection gap. Full-submission readiness remains approximately **72%** because independent evaluation, the voluntary student pilot, real-AI/final-release performance and final artifacts remain open. These are engineering planning judgments.

## Remaining work

Live-AI/source timing, independent relevance judgments, voluntary student feedback and the final report/slides/demo remain separate acceptance work. See [final readiness](FINAL_READINESS.md) for the current estimates and verified revision.
