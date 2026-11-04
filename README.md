# ECE Learning Advisor

**Team P07 | Fall 2026**

Development copy for the final project on December 11. The midproject baseline is preserved in [ai-degree-planner at commit 3fdbf78](https://github.com/JSM-Shinkiro/ai-degree-planner/tree/3fdbf78079834adb4b1cf73dd4bffd74b2fe4be9). See the [final-project handoff](docs/13_FINAL_PROJECT_DEVELOPMENT.md) for repository boundaries, backend priorities, and the next work.

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

The app starts in **preview mode** without API keys. Choose a career direction, add completed courses with the searchable picker, and select **Update my roadmap**. The plan groups suggestions into **Start here**, **Build toward**, and **Later goals**. Restore/download JSON files under **Saved profile** to carry progress between sessions.

On Windows, the tested Python version is 3.12. You can skip activation:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

If Python 3.12 is missing, install it first with `winget install --exact --id Python.Python.3.12 --source winget`, then reopen PowerShell. To update an existing clone, stop the app with Ctrl+C, run `git pull`, and launch it again.

## Enable live RAG

Copy `.env.example` to `.env` and set `GEMINI_API_KEY`. The example uses `gemini-embedding-2` and `gemini-3.5-flash-lite`, subject to account availability. Model IDs are configurable through the environment. Server keys are never used as widget defaults.

These models passed live checks on October 23. The tested `gemini-flash-latest` and `gemini-3.8-flash` generation requests encountered high-demand errors, so the default generator uses the working lighter model. See [live verification](docs/11_GEMINI_LIVE_VERIFICATION.md) for results and limitations. Keys are supplied locally and are not included in the repository.

For local development only, `ECE_DEVELOPMENT_MODE=true` enables editable model IDs and an empty session-only key field when no server key exists. Keep this off for a shared deployment.

Precompute the index with:

```bash
python scripts/build_index.py
```

Enable **Generate AI explanations**, then update the roadmap. Retrieved evidence is passed to the generator. Recommendation IDs and citations are validated before rendering.

To compare real keyword, semantic, and hybrid RAG requests and save their answers/timings:

```bash
python scripts/verify_live.py
```

Add `--jobs` to also check the configured Adzuna connection. These opt-in checks use real provider quota. Inspect the saved answers against their sources before using them in the report.

That provider-verification script retains the bundled corpus for comparison with the original measurements. Use `scripts/check_sources.py` below to exercise the current official-source path without model calls.

Source exploration is retrieval-only. It does not count as a completed live RAG demonstration.

## Current features

- Dark dashboard and student profile.
- Three learning stages, a bridge course for each direction, and explanations of suggested learning connections.
- Five source-linked courses and two online resources.
- Up to three additional course descriptions discovered from configured official foundation sections on each submitted roadmap.
- Keyword, semantic, and hybrid retrieval.
- Independent prerequisite evaluation with blocked courses kept as later goals.
- Structured Gemini generation and citation checks.
- Evidence inspector and ranking chart.
- PCA projection and cosine drill-down when embeddings are available.
- Versioned public-record embedding cache.
- Official course checks on submitted roadmaps, with a rebuildable source cache and dated failure fallback.
- Explicit prerequisite provenance and on-use revalidation for the reviewed CSC120 condition, with separate citation evidence.
- On-use checks of PyTorch Quickstart and CS50, with short source excerpts, published versions, and dated failure fallback.
- Reuse of unchanged document vectors when another course changes.
- Profile export/import, searchable coursework entry, and Mark completed actions.
- Direction comparison for students who are still exploring.
- Coverage clarification for clear requests outside the starter collection.
- On-demand Adzuna search adapter with a short session cache.

Job search requires `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`. No listings are fabricated when the provider is unavailable.

## Academic data

Submitted roadmaps now check the relevant configured official course pages before retrieval and generation. The connector validates course identity and the active catalog edition, refreshes descriptions and units in the request's catalog, and records check/download times separately. Unchanged content reuses its vectors. Ordinary interface rerenders do not fetch sources.

The connector checks five configured course pages, the reviewed CSC120 program-requirement section, and bounded course links from two configured foundation sections. It validates linked course IDs, subject scope, edition, and fixed units before adding a description. Fetched titles, summaries, units, and enrollment references retain their source IDs. Discovered courses keep unreviewed prerequisites unknown.

The CSC120 prerequisite statement is checked against its exact reviewed text, catalog edition, and structured interpretation. Changed, stale, unavailable, or unsupported prerequisite evidence makes the affected academic result unknown. The rule statement has its own source-linked evidence chunk and travels with the course description into the generator context.

The two configured learning resources are also checked on relevant submissions. Their titles, introductory excerpts, and published versions come from validated resource pages. Resource versions remain separate from academic catalog years and do not establish university credit. Failed checks retain clearly dated valid caches or bundled snapshots; an unfetched new course has no placeholder recommendation. A changed enrollment requirement reference revokes the affected reviewed rule. Catalog-wide discovery remains planned. See [runtime source checks](docs/14_RUNTIME_SOURCES.md), [prerequisite evidence](docs/15_PREREQUISITE_EVIDENCE.md), [bounded discovery](docs/16_COURSE_DISCOVERY.md), and [resource checks](docs/17_RESOURCE_SOURCES.md) for limits and verification.

`ECE_REFRESH_SOURCES=true` is the default. Set it to `false` for an explicit offline run; the app labels its sources as saved evidence. Public source checks do not require a Gemini key. Try:

```bash
python scripts/check_sources.py --career exploring
```

The command saves a trace under `.cache` and exits unsuccessfully if a requested source or its bound prerequisite interpretation could not be verified. It makes no embedding or generation calls. A permanent content database is still optional; if introduced, it must also refresh automatically on a configurable schedule.

The starter collection covers ECE101, ECE369A, ECE372A, ECE425, and CSC120 from the current 2026–2027 catalog. Summaries are paraphrased and linked to official entries.

Live discovery can expand the request's collection by up to three courses within the shared eight-course download budget. The real exploring-profile check added CSC110, ECE201, and ECE220. Candidate selection is limited to the configured foundation sections; finding a link does not approve a prerequisite, degree requirement, or semester assignment. Offline mode retains the bundled collection.

The public course entries return internal enrollment requirement IDs. The starter collection's four unresolved ECE rules and every discovered-course rule remain **unknown**. One CSC120 condition is reviewed against the current Computer Science program requirements, with its source linked in the app. Recorded prerequisite satisfaction does not establish complete enrollment eligibility.

Failed grades cannot be entered as successful completions. Missing prerequisite grades remain unknown. Learning-stage annotations are team suggestions and do not place courses into semesters.

```bash
python scripts/refresh_sources.py
```

This stages source metadata and hashes without modifying approved records.

## Tests and evaluation

```bash
python -m pytest -q
python scripts/evaluate.py --runs 20
```

Tests cover backend behavior and Streamlit interactions. Controlled providers test RAG integration without model requests. The October 23 integration checks included five generated answers plus an unsupported-topic guard that made no provider calls; live Adzuna checks remain pending.

The refinement includes regression tests for the review findings. See [prototype verification](docs/07_PROTOTYPE_VERIFICATION.md) and [refinement notes](docs/08_REFINEMENT_NOTES.md) for checks and remaining limits.

The evaluation script is a keyword-only smoke check, not a completed research benchmark.

## Project documents

**Report title:** ECE Learning Advisor: An Inspectable RAG System.

Start with [the documentation index](docs/README.md) and [the current development handoff](docs/13_FINAL_PROJECT_DEVELOPMENT.md). The older team-progress document preserves the pre-midproject status.

The six sample papers have a focused review in the project notes. The corresponding tool/video review remains to be completed. Broader academic-rule coverage, account-based persistence, and the held-out evaluation remain in the roadmap.
