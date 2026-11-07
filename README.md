# ECE Learning Advisor

**Team P07 | Fall 2026**

[![Backend checks](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/workflows/backend.yml/badge.svg)](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/workflows/backend.yml)

Development copy for the final project on December 11. The midproject baseline is preserved in [ai-degree-planner at commit 3fdbf78](https://github.com/JSM-Shinkiro/ai-degree-planner/tree/3fdbf78079834adb4b1cf73dd4bffd74b2fe4be9). See the [final-project handoff](docs/13_FINAL_PROJECT_DEVELOPMENT.md) for repository boundaries, backend priorities, and the next work.

[Final readiness](docs/FINAL_READINESS.md) tracks the app and submission separately, including independent evaluation, browser validation, and final report/slides/demo. Each development step updates this assessment.

Submitted roadmaps show [live request stages](docs/46_REQUEST_PROGRESS.md), with an expandable history and server phase timings in the inspector. Preview, clarification and fallback paths report only the work actually attempted.

[Responsiveness improvements](docs/48_RESPONSIVENESS_REVIEW.md) reuse successful public-source checks for up to five minutes and render the inspector only when opened. **Check sources again** bypasses recent reuse for the submitted profile; source timestamps remain unchanged when reused.

[AI-enabled requests](docs/49_PROGRESSIVE_AI_REQUESTS.md) keep the page interactive and show a source plan before optional AI explanations finish. **Keep source plan** stops accepting that AI result; new profile submissions supersede older work.

A separate [human review workspace](docs/47_REVIEW_WORKSPACE.md) supports explicit relevance grades, notes, draft download/resume and validated completed-review exports. Run `python -m streamlit run reviewer_app.py --server.address 127.0.0.1 --server.port 8502` locally. Reviewing uses saved evidence and needs no model credentials; actual independent judgments remain to be collected.

An inspectable retrieval-augmented generation (RAG) advisor for prospective and current University of Arizona ECE students. The first prototype connects student interests with course evidence, complementary resources, and a configurable RAG pipeline.

## Run locally

Python 3.11 or newer is required. From the repository root:

```bash
git clone https://github.com/JSM-Shinkiro/ece-learning-advisor.git
cd ece-learning-advisor
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m streamlit run app.py
```

On Windows PowerShell, activate with `.\.venv\Scripts\Activate.ps1` instead.

The app starts in **preview mode** without API keys. Choose a career direction, add completed and currently taking courses with the searchable pickers, and select **Update my roadmap**. The plan groups suggestions into **Start here**, **Build toward**, and **Later goals**. Current courses stay out of next-step suggestions; **Mark completed** moves one to successful completions without inventing a grade. Restore/download JSON files under **Saved profile** to carry progress between sessions. See [current coursework](docs/43_CURRENT_COURSEWORK.md) for the workflow and verification.

On Windows, the tested Python version is 3.12. You can skip activation:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

If Python 3.12 is missing, install it first with `winget install --exact --id Python.Python.3.12 --source winget`, then reopen PowerShell. To update an existing clone, stop the app with Ctrl+C, run `git pull`, and launch it again.

## Check runtime before hosting

Run `python scripts/check_deployment.py --smoke` to validate configuration, pinned production dependencies, bundled evidence/connectors, writable caches, local server liveness, and an offline preview roadmap. The smoke test uses no provider credentials or external source requests. Its report defaults to `deployment_check.json` in the configured cache directory. See [runtime readiness](docs/27_DEPLOYMENT_READINESS.md) for hosting settings and verification scope.

For the optional [real-browser acceptance check](docs/45_BROWSER_ACCEPTANCE.md), install `requirements-browser.txt` and Chromium with `python -m playwright install --with-deps --only-shell chromium`, then run `python scripts/check_browser.py --output output/browser-first.json`. It exercises profile download/upload, current-course completion, two isolated sessions, and actual WebSocket activity through the production launcher. Use a new report path each time. Linux browser CI runs separately from the Linux/Windows backend checks. A separate `python scripts/check_progressive_browser.py --output output/progressive-browser-first.json` exercises deliberately delayed AI through a controlled local provider and the same student UI; it makes no real model/source requests and accepts no running-host URL.

`ECE_CACHE_DIR` selects the source/embedding cache root; relative paths resolve from the project directory. The default is `.cache`. Invalid server configuration stops with a sanitized message naming the setting. Shared-hosting readiness requires `ECE_DEVELOPMENT_MODE=false`; API keys remain optional for preview mode.

[Shared embedding-cache coordination](docs/40_SHARED_EMBEDDING_CACHE.md) now lets concurrent requests in one server process reuse a successful public document build, including unchanged chunks across source overlays. Query embeddings, profiles, answers, and source-selection traces stay request-local. Successful public-source checks can also be reused briefly under the [source reuse policy](docs/48_RESPONSIVENESS_REVIEW.md). Waiting is bounded; a busy cache uses the existing keyword fallback. A production-only controlled check completes eight simultaneous controller requests with 34 document calls, eight separate query/generation calls, and no real model/HTTP requests. Public hosting and multi-process coordination remain separate.

For a shared host, the [production launcher](docs/41_PRODUCTION_LAUNCHER.md) runs the local preflight before opening the server:

```bash
python scripts/serve.py --check
python scripts/serve.py
```

It accepts a host-supplied `PORT`, validates the address and optional URL prefix, and starts one Streamlit process using the current Python environment. Use `--address 127.0.0.1` for a loopback-only launch. The full readiness smoke now exercises this same command and passes nine checks. Host HTTPS/access settings, remote browser sessions, and the actual hosted pilot remain open.

[Automatic backend checks](docs/42_BACKEND_CI.md) run the complete test suite and startup smoke on Linux and Windows with Python 3.12 for code/data/configuration changes. Each job saves JUnit and readiness reports. Check the linked workflow for its actual revision and result; these checks remain separate from live-provider and independent quality evaluation.

## Enable live RAG

Copy `.env.example` to `.env` and set `GEMINI_API_KEY`. The example uses `gemini-embedding-2` and `gemini-3.5-flash-lite`, subject to account availability. Model IDs are configurable through the environment. Server keys are never used as widget defaults.

These models passed live checks on October 23 with the earlier output format. The tested `gemini-flash-latest` and `gemini-3.8-flash` generation requests encountered high-demand errors, so the default generator uses the working lighter model. The November 4 statement-selection format now passes real keyword, semantic, hybrid, changed-goal, completion, and runtime-discovery checks. See [current Gemini verification](docs/22_CURRENT_GEMINI_VERIFICATION.md), [the earlier measurements](docs/11_GEMINI_LIVE_VERIFICATION.md), and [the explanation contract](docs/19_GROUNDED_EXPLANATIONS.md). Credentials are supplied locally and are not included in the repository.

For local development only, `ECE_DEVELOPMENT_MODE=true` enables editable model IDs and an empty session-only key field when no server key exists. Keep this off for a shared deployment.

Submitted AI requests share a [45-second AI time budget](docs/44_AI_TIME_BUDGET.md) after official-source checking. `AI_TIME_BUDGET_SECONDS` accepts 5–120 seconds. Model timeouts and cache waits use the remaining allowance; an expired request shows the updated source roadmap and a clear notice. This cooperative limit excludes source work and browser rendering. The runtime verifier uses the same configured value.

Precompute the index with:

```bash
python scripts/build_index.py
```

Enable **Generate AI explanations**, then update the roadmap. The model receives retrieved evidence and application-owned statements, and selects relevant statement IDs. The app supplies the exact displayed wording, fact/suggestion labels, and citations. Arbitrary model prose or altered statements are rejected; source cards remain available on failure.

To compare real keyword, semantic, and hybrid RAG requests and save their answers/timings:

```bash
python scripts/verify_live.py
```

Add `--jobs` to also check the configured Adzuna connection. These opt-in checks use real provider quota. Inspect the saved answers against their sources before using them in the report.

That provider-verification script retains the bundled corpus for comparison with the original measurements. Use `scripts/check_sources.py` below to exercise the current official-source path without model calls.

The [expanded runtime verifier](docs/39_RUNTIME_PROVIDER_VERIFICATION.md) checks the current 34-chunk collection through the app controller. Run `python scripts/verify_runtime.py --live-models --output .cache/runtime_provider_check.json`; add `--with-sources` for one current-source scenario. It requires explicit model-use opt-in, caps calls, preserves failed checks, and rejects existing reports before quota use. November 6 real observations verify all seven authored expectations across an initial run and one bounded follow-up after a proxy error. The initial failure remains recorded; independent quality grading is still open.

Source exploration is retrieval-only. It does not count as a completed live RAG demonstration.

## Current features

- Dark dashboard and student profile.
- Three learning stages, a bridge course for each direction, and explanations of suggested learning connections.
- Twenty source-linked courses and eight official learning resources in the app, with a separate frozen collection for historical evaluation.
- On-use checks prioritize requested course codes, reviewed topic phrases, and named resources within the existing download limits.
- Up to three additional course descriptions can be discovered from configured official sections when they are absent from the loaded collection and download slots remain.
- Explicit course codes and reviewed title/topic phrases get discovery priority within the verified source scope and existing download cap, with matched phrases and outcomes in the inspector.
- Keyword, semantic, and hybrid retrieval.
- Independent prerequisite evaluation with blocked courses kept as later goals.
- Structured Gemini statement selection with application-owned wording, citations, and academic limitations.
- Evidence inspector and ranking chart.
- PCA projection and cosine drill-down when embeddings are available.
- Versioned public-record embedding cache.
- Official course checks on submitted roadmaps, with a rebuildable source cache and dated failure fallback.
- Explicit prerequisite provenance and on-use revalidation for the reviewed CSC120 condition, with separate citation evidence.
- Reviewed-rule attachment during discovery for CSC110, CSC144, and CSC210, with edition-bound coursework/grade conditions and unknown placement alternatives.
- On-use checks for PyTorch, CS50, Python, NumPy, scikit-learn, Pico, and two archived MIT courses, with source excerpts, version labels, and dated failure fallback.
- Reuse of unchanged document vectors when another course changes.
- Profile export/import, searchable completed/current coursework entry, and Mark completed actions.
- Direction comparison for students who are still exploring.
- Coverage clarification for clear requests outside the starter collection.
- Bounded domain aliases for student wording, with visible added search terms and question-focused course selection.
- On-demand employer-board opportunities with source checks, original links, separate posting/update dates, and title/location filters.
- Fresh opportunity requests by default, with optional explicit reuse of matching results for 20 minutes.
- On-demand posting descriptions with separate check times, source identity validation, change notices, and visible failures.
- Ten opportunities per page, with up to 200 retained matches from the same dated search and no source requests while paging.
- One bounded retry for selected transient employer-source failures, with visible attempt history and unchanged per-source time/download guards.

## Opportunities

Open **Opportunities** and select **Available Opportunities** to check the configured Samsara, Nuro, and Anduril Industries employer boards. This public-source path needs no API key or language model. It matches AI/ML or embedded engineering terms in titles; it does not assess your qualifications. Leave the location filter blank for all listed locations, or enter text that must occur in the employer's location field. Choose all levels, internship/co-op, or explicit new-grad/entry-level title labels; the last-update filter is optional.

Each search requests the sources unless you explicitly select recent-result reuse. Results show retrieval time and available provider dates. Source failures are visible; a failed search removes the previous visible results. Coverage is limited to the configured employers. A zero-match location search does not establish that the wider market has no jobs.

Use **Next listings** and **Previous listings** to browse ten matches at a time. A search retains the first 200 matches in update order and shows the full matching count; narrow the filters if more matches were found. Paging uses the same dated search without checking sources again. A new search or explicit matching-result reuse starts on page one. See [opportunity paging](docs/33_OPPORTUNITY_PAGING.md).

Select **Check posting details** on a result to request that posting's description. Each click checks the source again, separately from the search timestamp. Descriptions appear as plain text, with a notice if posting information changed or the text was shortened. A failed recheck removes the previous description. Review the employer's wording and original page for requirements; the app does not turn them into eligibility decisions. See [posting details](docs/32_POSTING_DETAILS.md).

Employer metadata and posting checks may retry once after a selected transient connection/read/write failure or HTTP 502/503/504, within the same source time/download guards. Rate limits, Retry-After responses, redirects, and invalid content stop the check. Attempt outcomes and timings appear in the source checks and posting details. See [opportunity request recovery](docs/34_OPPORTUNITY_RECOVERY.md).

Run the public-source check separately with:

```bash
python scripts/check_opportunities.py --career embedded --internship
```

The command saves its source checks under `.cache` and returns a failure status if any source is unavailable or has rejected records, even when other results remain usable. See [live opportunities](docs/23_LIVE_OPPORTUNITIES.md) for verification and limits. The separate Adzuna location-search adapter appears only when `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` are configured; live Adzuna verification remains pending.

## Academic data

Submitted roadmaps now check the relevant configured official course pages before retrieval and generation. The connector validates course identity and the active catalog edition, refreshes descriptions and units in the request's catalog, and records check/download times separately. Unchanged content reuses its vectors. Ordinary interface rerenders do not fetch sources.

The app loads 20 courses and eight resources by adding reviewed coverage to the unchanged five-course/two-resource evaluation baseline. The additional courses are CSC110, CSC144, CSC210, ECE201, ECE220, ECE274A, ECE310, ECE311, ECE320A, ECE340A, ECE351C, ECE373, ECE352, ECE381A, and CSC372. Title, summary, units, and enrollment references retain source IDs and catalog edition. All 15 ECE conditions and the CSC372 condition remain unknown; only the four existing exact CS interpretations can acquire verified conditions. The lower end of the original coverage target is met; academic-rule and independent quality coverage remain open. See [track and open-course coverage](docs/37_TRACK_AND_OPEN_COURSE_COVERAGE.md).

At most eight course pages, two program pages, and two resource pages are checked per submitted roadmap. Explicit course requests and reviewed phrases come first; saved courses with reviewed prerequisite evidence then take priority over other records. Remaining ties favor unfinished courses. Courses beyond the budget remain visibly dated snapshots. Eight configured program sections remain available for bounded discovery. Unfamiliar track links use reviewed section preparation labels; exact per-course annotations take precedence. Finding a link does not approve enrollment.

[Bounded source recovery](docs/30_SOURCE_RECOVERY.md) allows one retry for selected transient public-source failures. Attempts share elapsed/size guards, and the inspector/CLI retain retry outcomes. Rate limits and invalid evidence are not retried; unsuccessful checks keep labeled dated fallbacks. Source limits count distinct checks, while a retry adds a bounded HTTP attempt.

The CSC120 prerequisite statement is checked against its exact reviewed text, catalog edition, and structured interpretation. Changed, stale, unavailable, or unsupported prerequisite evidence makes the affected academic result unknown. The rule statement has its own source-linked evidence chunk and travels with the course description into the generator context.

Named resources are prioritized in both the two resource-check slots and the explanation context. Their titles, introductory excerpts, and published versions come from validated pages. Pico's page supplies no release version, so its label explicitly says `unversioned documentation`. MIT teaching terms remain explicitly Spring 2020 and Spring 2017 when those archived resources are checked. Resource versions remain separate from academic catalog years and do not establish university credit. Failed checks retain dated caches or bundled snapshots; a changed enrollment reference revokes the affected reviewed rule. Catalog-wide discovery remains planned. Earlier [runtime checks](docs/14_RUNTIME_SOURCES.md), [prerequisite evidence](docs/15_PREREQUISITE_EVIDENCE.md), [bounded discovery](docs/16_COURSE_DISCOVERY.md), and [resource checks](docs/17_RESOURCE_SOURCES.md) retain their original measurements.

`ECE_REFRESH_SOURCES=true` is the default. Set it to `false` for an explicit offline run; the app labels its sources as saved evidence. Public source checks do not require a Gemini key. Try:

```bash
python scripts/check_sources.py --career exploring
python scripts/check_sources.py --collection runtime --career ai_ml --question "CSC210 with NumPy and scikit-learn"
```

The command defaults to the frozen baseline for reproducible historical checks; `--collection runtime` uses the app's expanded collection. It saves a trace under `.cache` and uses a strict exit: any unverified check, including an expected budget skip, returns failure. Inspect selected checks and skipped snapshots separately. It makes no embedding or generation calls. A permanent content database is still optional; if introduced, it must also refresh automatically on a configurable schedule.

The frozen starter collection covers ECE101, ECE369A, ECE372A, ECE425, and CSC120 from the 2026–2027 catalog. Its records and evaluation labels remain unchanged. The app and `scripts/build_index.py` now use the expanded runtime collection; historical provider/retrieval evaluation scripts continue to use the frozen baseline. Earlier quality measurements do not measure the expanded corpus.

Live discovery can expand a request's collection by up to three courses within the shared eight-course download budget. The November 3 exploring-profile check added CSC110, ECE201, and ECE220. The [CS expansion](docs/24_CS_FOUNDATION_COVERAGE.md), [requested-course priority](docs/25_REQUESTED_COURSE_DISCOVERY.md), and [ECE core coverage](docs/29_ECE_CORE_COVERAGE.md) retain their dated scope. Those configured identities are now also available from reviewed runtime snapshots in offline mode. Career scope and download limits still apply. Finding a link does not approve a prerequisite, degree requirement, or semester assignment.

The inspector shows whether a requested course was added, retained as dated cached content, already in the collection, limited by the budget, or unavailable from the selected sources. [Reviewed phrase routing](docs/26_COURSE_PHRASE_ROUTING.md) recognizes configured phrases such as “phasors,” “unit testing,” and “object-oriented programming.” Explicit codes come first; matched phrases then follow mention order. These are reviewed routing hints, not general natural-language understanding or academic evidence. To exercise this path without model calls:

```bash
python scripts/check_sources.py --career ai_ml --question "How should I prepare for ECE201?"
python scripts/check_sources.py --career ai_ml --question "How can I learn phasors and unit testing?"
```

[ECE core coverage](docs/29_ECE_CORE_COVERAGE.md) adds ECE310, ECE311, ECE320A, ECE340A, ECE351C, and ECE373 through verified core/computer-engineering program links. Bound preparation stages keep these under “Build toward” while their academic conditions remain unknown. Known completed candidates no longer consume discovery slots; the inspector lists skipped completions. Existing download limits and novice defaults remain in place.

The command reports source checks and requested-course outcomes separately. A successful source-check exit does not establish that every mentioned course was found or that prerequisites are satisfied.

The public course entries return internal enrollment requirement IDs. All fifteen ECE conditions and CSC372 in the runtime collection remain **unknown**. The saved runtime records include the four exact reviewed CS interpretations; discovery can also attach those interpretations when starting from the smaller baseline. The CSC144 condition combines an introductory programming alternative with a mathematics alternative; its placement branch remains unknown. CSC210 requires a confirmed CSC120 grade of C or higher. These checks preserve prior completion, minimum grades, and unknown evidence. Other discovered conditions remain unreviewed. See [discovered-course conditions](docs/21_DISCOVERED_COURSE_RULES.md) and [the CS expansion](docs/24_CS_FOUNDATION_COVERAGE.md). Recorded prerequisite satisfaction does not establish complete enrollment eligibility.

Failed grades cannot be entered as successful completions. Missing prerequisite grades remain unknown. Learning-stage annotations are team suggestions and do not place courses into semesters.

```bash
python scripts/refresh_sources.py
```

This stages source metadata and hashes without modifying approved records.

## Tests and evaluation

```bash
python -m pytest -q
python scripts/evaluate.py --runs 20
python scripts/evaluate_reviewed.py --output .cache/reviewed_evaluation.json --markdown .cache/reviewed_evaluation.md
```

Tests cover backend behavior and Streamlit interactions. Controlled providers test RAG integration without model requests. The October 23 integration checks included five generated answers plus an unsupported-topic guard that made no provider calls; live Adzuna checks remain pending.

The refinement includes regression tests for the review findings. See [prototype verification](docs/07_PROTOTYPE_VERIFICATION.md) and [refinement notes](docs/08_REFINEMENT_NOTES.md) for checks and remaining limits.

`evaluate.py` retains the original keyword-only smoke check. `evaluate_reviewed.py` adds frozen retrieval judgments, roadmap expectations, and authored claim probes. Its default run makes no source, embedding, or generation calls. The [reviewed baseline](docs/18_REVIEWED_EVALUATION.md) preserves retrieval misses and nine unsupported claims admitted by the earlier citation checker. The [November 4 follow-up](docs/19_GROUNDED_EXPLANATIONS.md) rejects those authored explanations and accepts 82/82 canonical statement controls. It also rejects true paraphrases outside the fixed wording; this is an output contract, not a general entailment score or live model-accuracy result.

Semantic/hybrid comparison requires an explicit `--live-embeddings` opt-in and a configured Gemini key. It uses real provider quota for embeddings only; no generator is called. Controlled test vectors are labeled as fixtures and are not published as neural quality results.

The [November 4 live comparison](docs/22_CURRENT_GEMINI_VERIFICATION.md) uses real Gemini embeddings on the frozen expanded-query references: semantic/hybrid Recall@5 is 1.0, versus keyword 0.9479. This is a small development set with aliases tuned after known misses, not an independent held-out result. Seven live integration expectations also passed, including one guard case with no model calls.

Add `--query-mode expanded` to measure the bounded aliases separately from the default raw-query baseline. The [query-interpretation follow-up](docs/20_QUERY_INTERPRETATION.md) records Recall@5 of 0.9479 versus 0.8229 on the same small authored reference set. This is development tuning after known misses, not an independent held-out result. The current Linux/Windows suite passes 1,600 tests, including 93 Streamlit scenarios (87 student-app and six reviewer-workspace). Alias expansion makes no extra model calls and does not change academic evidence or eligibility.

For external review, [the expanded-catalog workflow](docs/38_EXPANDED_REVIEW_COLLECTIONS.md) supports `--collection runtime` and archived `--catalog-snapshot` inputs across preparation, embedding, and scoring. The default remains the frozen baseline. A [prepared runtime packet](data/reviews/runtime_v1) contains 12 assistant-authored development questions, 34 evidence chunks, and 408 blank grades. These are not held-out questions or independent judgments. New exports include the exact catalog snapshot so grades remain usable after repository data changes. Use that snapshot for later embedding/scoring; old forms or vectors cannot silently substitute. Keyword, semantic, and hybrid methods use the same completed form. Preparation/scoring stay offline; optional Gemini vectors still require `embed --live-embeddings`. Keep the catalog snapshot, vectors, and score reports with the operator, separate from reviewer materials. Earlier [reviewer](docs/28_REVIEWER_WORKFLOW.md) and [method-comparison](docs/35_REVIEW_METHOD_COMPARISON.md) notes retain their historical observations.

The [student-opportunity extension](docs/31_STUDENT_OPPORTUNITIES.md) adds Anduril Industries and a **Role titles** choice for all levels, internship/co-op, or new-grad/entry-level labels. Filters run locally and do not infer qualifications. Explicit recent-result reuse also binds the board configuration and title-policy fingerprint. Use `python scripts/check_opportunities.py --career embedded --early-career` for a source-only check.

## Project documents

**Report title:** ECE Learning Advisor: An Inspectable RAG System.

Start with [the documentation index](docs/README.md) and [the current development handoff](docs/13_FINAL_PROJECT_DEVELOPMENT.md). The older team-progress document preserves the pre-midproject status.

The six sample papers have a focused review in the project notes. The corresponding tool/video review remains to be completed. Broader academic-rule coverage, account-based persistence, and the held-out evaluation remain in the roadmap.
