# App improvement and responsiveness review

Team P07 · November 7, 2026 · ECE Learning Advisor

The main delay is external work performed on a submitted roadmap, particularly source revalidation and optional AI calls. The small JSON collection and NumPy search are not the current bottleneck. Adding a database would help future accounts/history, but would not by itself make these interactions faster.

## Improvements implemented in this step

### Reuse recent successful public-source checks

A normal **Update my roadmap**, completion action, direction change or profile restore can reuse a selected public page successfully checked by the current server process within the last **five minutes**. Source selection, profile filtering, prerequisite evaluation and ranking still run for the current student. This does not cache a person's plan or share their profile/answer with another session.

**Check sources again** submits the current profile details and revalidates the selected pages immediately. It is a one-request bypass, and is disabled when the server has turned off live source checks. Download limits, edition checks, resource identities and reviewed-rule constraints still apply.

The app retains the original successful check/download times. The trace marks reuse as `recent_cache`, with no HTTP status or network attempts; the roadmap explains that it used recent checks. No new source verification timestamp is invented.

Reuse requires both a validated on-disk entry and a matching successful-check record in the running process. The bounded, thread-safe in-memory table holds at most 256 public cache identities. Wall-clock age and monotonic expiry must both pass. Reading an entry does not extend its lifetime. Expiry, a force check, altered cache identity, or a failed source attempt revokes reuse. Restarting the server requires fresh checks before reuse, even if disk caches survive. Existing source/checker commands and the opt-in runtime verifier continue to make fresh requests.

This is deliberately limited to one server process. It does not coordinate fresh HTTP work across replicas or guarantee one HTTP request for simultaneous cold misses. The existing source failures still produce dated evidence and unknown academic results when appropriate.

### Render the inspector only when opened

The closed **How this plan was made** panel now builds and sends no ranking charts, evidence tables, PCA projection or request JSON. Opening it renders the details. It uses a Streamlit fragment, so its controls can update independently of the rest of the page. Downloading a request trace does not trigger another rerun.

This keeps the same inspection features while avoiding unnecessary work on ordinary profile interactions. It follows the documented [expander state](https://docs.streamlit.io/develop/api-reference/layout/st.expander) and [fragment execution](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment) APIs, also checked against the installed Streamlit 1.66.1 signatures. It does not introduce background AI jobs or change source/model call counts when inspecting a saved plan.

## Observed timings

Real public-source requests, preview mode, one server process, a new temporary source cache, embedded-systems profile:

| Action | Server wall time | HTTP attempts | What happened |
| --- | ---: | ---: | --- |
| First source update | 13.021 s | 11 | Eleven selected sources downloaded |
| Immediate repeat | 0.020 s | 0 | Eleven recent source checks reused |
| Add ECE101 to currently taking | 3.789 s | 1 | Ten sources reused; the newly selected course fetched |
| Explicit recheck | 9.570 s | 11 | Nine unchanged responses and two HTTP 304 responses |

These are four observations, not a performance distribution or a controlled speedup benchmark. They exclude AI and browser rendering, and do not predict every network condition. The changed profile still filtered ECE101 out of next-step recommendations. The affected ECE academic conditions remained unknown.

A separate local AppTest rendering probe used the same prebuilt preview before and after the change. Before, even the closed inspector constructed one chart, three tables and a trace JSON block. After, all those counts were zero. Its first render was 1.036 s before and 0.339 s after; repeated renders were approximately 0.09–0.22 s before and 0.07–0.12 s after. These small, sequential local samples are not browser-visible latency measurements.

Detailed results and verification belong in [the dated evidence record](evidence/responsiveness_2026-11-07.json).

## Verification

Verified code revision: `3a8c7a8ae37f47455830ba5cdf8868cde0eefe2d` in [successful CI run 42403841774](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/42403841774).

- All **1,580 tests** and **nine readiness checks** pass on both Linux and Windows; there are 18 new regression cases in this step, including four student UI scenarios.
- All **ten student-browser** and **six reviewer-browser** gates pass in real Chromium. The added inspector gate observes two fragment completions, no full-app rerun, no chart while closed and an unchanged profile.
- Reuse tests cover HTTP elimination, recomputation for the current profile, expiry, future timestamps, explicit refresh, a changed source, failed force-check invalidation, corrupt caches, process restart, resource/discovery identity, exact reviewed statements, monotonic expiry and bounded memory.
- Eight frozen/review inputs retain their hashes; all 408 actual review-template grades remain blank.

The inspector browser gate took 3.192 seconds for its full scripted open/close sequence, including the first chart load and waits. This is a useful remaining distinction: work has been deferred out of normal roadmap interactions; opening detailed analysis can still have a first-use cost. The preview browser sequence does not test real AI, networked source checks, public hosting or human usability.

## Highest-value remaining improvements

| Priority | Improvement | Why it matters / acceptance check |
| --- | --- | --- |
| Next | Show a useful source-based plan before optional AI finishes; allow a newer edit to supersede older work | First-time source checks and AI are still synchronous. Use request identities so late work can never overwrite a newer profile; keep unverified snapshots labeled. Measure time to the first usable plan. |
| Next | Make opportunity requests report progress where the action occurs | Search already has a spinner, but posting-detail work starts in a callback. Move the request into the visible result area or an isolated fragment and retain the last valid search on failure. |
| Next | Make the collection easier to scan | Add course-code/topic search and simple course/resource/direction filters. Validate on a phone viewport; avoid losing filter/profile values when panels change. |
| Before freeze | Reduce warning repetition and clarify applied versus edited settings | Several per-source issues can crowd the roadmap, and AI/ranking controls apply on the next submission. Show a concise summary with expandable details, while keeping changed prerequisites and blocking issues prominent. |
| Before submission | Test actual student tasks and recommendation quality | Collect genuine independent evidence judgments and 3–5 voluntary usability tasks. Record confusion, failures and missing courses rather than inferring quality from automated tests. |
| Before submission | Measure cold/warm browser response times, including real AI and concurrent users | Record first usable content, completed plan and interaction latency separately. Report medians/tails only with enough samples, on the frozen code and chosen access path. |
| Later, if needed | Persist profiles/accounts in a database | Useful for automatic cross-device save/history; adds account and data-management work. Manual JSON portability is sufficient for the scoped submission unless requirements change. |

Suggested performance targets for the final measurement plan—not established guarantees: ordinary non-network controls should finish within about 0.3 seconds; a warm preview update within about one second; visible feedback should appear immediately for network actions. Cold source and AI completion times must be reported separately. A 45-second AI budget is a fallback ceiling, not a responsiveness target, and excludes source work.

Avoid adding live checks to every keystroke, globally caching personal answers, marking cached data as newly checked, or hiding a slow request behind a spinner without reducing its work. Forms, bounded retries, content-addressed embedding reuse and source-bound fallbacks already provide useful foundations.

## Submission effect

This step addresses redundant source revalidation and hidden inspector work. The planning estimates remain approximately **90% app / 70% full submission**. Independent judgments, student feedback, final AI/browser performance measurements and the final report/slides/demo are still the main open gates; faster automated runs do not close them.
