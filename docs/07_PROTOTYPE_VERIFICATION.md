# Prototype Verification

Updated October 23, 2026, Arizona time. Original prototype checks were performed October 22; automated tests and the live Gemini checks below were run October 23.

## Checks performed

| Check | Result |
| --- | --- |
| Clean Python environment | Installed `requirements-dev.txt` successfully on Python 3.12 |
| Automated tests | 80 passed, including 12 Streamlit interaction tests |
| Server startup | Health endpoint returned `ok`. Root page returned successfully |
| Official source importer | Fetched and parsed all five starter course entries |
| Keyword smoke evaluation | Five cases passed, each repeated 20 times |
| Real embedding/generation requests | Six live checks passed October 23 using `gemini-embedding-2` and `gemini-3.5-flash-lite`; see [live verification](11_GEMINI_LIVE_VERIFICATION.md) |
| Real job request | Not run. No Adzuna credentials configured |
| Browser screenshot review | Pending. Chromium download failed in this environment |

The tests exercise changed goals, learning stages, failed grades, completed-course filtering, rule logic, malformed inputs, citation rejection, provider failures, cache invalidation, profile files, opportunity response handling, and the Astra review regressions. Provider and vector fixtures are controlled test data. They are not used to manufacture live app results.

## Reproduce locally

From the repository root, after installing dependencies:

```bash
python -m pytest -q
python scripts/evaluate.py --runs 20 --output output/keyword_smoke.json
python -m streamlit run app.py
```

In the browser, submit an incoming AI/ML profile with no programming background. ECE101 should appear under Start here, CSC120 under Build toward, and ECE425 under Later goals. Change the direction to embedded systems to see its architecture bridge and microcontroller goal. Still exploring should retain both directions. Marking a course completed removes it and refreshes the visible picker. Completing a prerequisite without a needed grade does not establish that grade condition.

The refinement smoke evaluation measured approximately 0.4–0.5 milliseconds per request at the median across the five cases on this machine. This measures the small, in-memory keyword pipeline only. It excludes app rendering, network calls, model inference, installation, and cold startup. It is not a live RAG latency result or a research benchmark.

## Live RAG acceptance check

1. Configure `GEMINI_API_KEY` locally and confirm the model IDs available to the account.
2. Run `python scripts/build_index.py` to precompute real public-record embeddings.
3. Enable AI explanations and submit a profile.
4. Confirm a generated response, valid record/chunk references, and resolvable source links.
5. Inspect the exact context, actual vectors, cache state, and separate stage timings.
6. Repeat with a changed goal, completed course, and a question outside the collection.
7. Check the explanation against its sources. Reference validation alone does not prove that a claim is supported.

Record live measurements before using them in the report. A cold index build embeds records individually and can take longer. Later requests reuse the compatible index.

## Remaining limits

- Four ECE enrollment conditions are unknown. The CSC120 condition is reviewed from a current catalog program entry, with its source and review limits recorded.
- The learning-stage annotations are team suggestions. They do not establish a semester plan or enrollment eligibility.
- Coverage is five courses, two learning resources, and two career mappings.
- Profiles use portable JSON files and session state. Hosted accounts and durable storage are pending.
- Source refresh produces review candidates. It does not silently replace approved academic data.
- Online resources are curated. Automated broad research and job-skill extraction are later work.
- The required six sample-paper reviews, held-out evaluation, and student pilot remain open.
- The vocabulary coverage guard catches clear nonmatches. It does not replace semantic relevance or answer-support evaluation.

The opt-in `python scripts/verify_live.py` command saves real answers and traces for keyword, semantic, and hybrid retrieval after a key is configured. Add `--jobs` for Adzuna. Live Gemini checks are now recorded in [the October 23 report](11_GEMINI_LIVE_VERIFICATION.md); Adzuna is still pending. The live checks used bundled course evidence and do not verify automatic academic-source retrieval.

## Next evidence to collect

Real RAG traces, provider/model configuration, and a small latency table are saved. Collect a live job result and browser screenshots, resolve the remaining rules, and run the broader answer-quality evaluation for the midpoint report and narrated demonstration.
