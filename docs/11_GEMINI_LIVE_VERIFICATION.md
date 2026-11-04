# Gemini Live Verification

Checked October 23, 2026, Arizona time.

Both supplied credentials completed real embedding and generation requests. The starter application completed keyword, semantic, and hybrid RAG with `gemini-embedding-2` and `gemini-3.5-flash-lite`. These are now the default models. Keys were used in process memory and are not included in source files, saved traces, or repository configuration.

## Working configuration

| Setting | Verified value |
| --- | --- |
| Python SDK | `google-genai==2.33.0` |
| Embedding model | `gemini-embedding-2` |
| Dimensions | 768 |
| Generator | `gemini-3.5-flash-lite` |
| Collection | `starter-2026-10-22-v2`: five courses, two resources, two career mappings |
| Real evidence index | Nine independently embedded chunks; shape 9 × 768 |
| Generation API | Existing application adapter using `client.interactions.create`, structured JSON, and `store=False` |

The separate AI Studio-style `client.models.generate_content` sample also returned a valid answer with the lighter model. Both credentials generated embeddings. The full application checks used Key 1. No real student records were used.

## Live integration results

| Scenario | Result | Index cache | Total application time |
| --- | --- | --- | --- |
| AI beginner: keyword RAG | Passed | not_used | 8.567 s |
| AI beginner: semantic RAG | Passed | miss | 8.260 s |
| AI beginner: hybrid RAG | Passed | hit | 3.574 s |
| Changed goal: embedded systems | Passed | hit | 4.516 s |
| Completed foundation: ECE101 | Passed | hit | 5.091 s |
| Unsupported topic: no provider calls | Passed | No model calls | <0.001 s |

The first semantic request built the real index. Subsequent semantic/hybrid requests reused it while embedding their queries. Times are single-request observations on this machine, including the relevant provider calls. They are not averages, cost estimates, performance guarantees, or a comparison benchmark. Browser rendering, application startup, and official website retrieval are excluded.

The five generated answers passed JSON validation, allowed-course checks, duplicate checks, and evidence-ID validation. Changing the goal returned the embedded-systems courses. Completing ECE101 removed it from recommendation candidates, and the recorded B grade satisfied the reviewed CSC120 alternative. Unresolved ECE conditions remained unknown. The unsupported paleontology query returned the coverage clarification without any embedding or generation calls; this verifies the application guard, not model abstention.

The 80 existing automated tests also passed after changing the model defaults, in 7.51 seconds.

## Model availability observations

Requests to `gemini-flash-latest` encountered HTTP 503 high-demand and timeout responses. A direct `gemini-3.8-flash` request also returned 503; the original application generation attempt did not complete. Listing models and making real embedding requests succeeded, and `gemini-3.5-flash-lite` completed the generation checks. This is evidence of a working alternative, not a guarantee that a listed model will have capacity on every request.

The older default application attempt took about 82.3 seconds before returning its failure state. The configured client timeout is not established as an end-to-end deadline for that path; measure and address failure latency before claiming a strict request limit.

## Answer review

Compared the five generated answers with their supplied evidence and rule results. The semantic and hybrid examples preserved the course descriptions and suggested learning stages in this small set. The keyword answer changed **perceptrons** to **perception** in its ECE425 description. Its citation ID was valid, so citation validation did not catch the terminology error. The original response is retained in the saved evidence.

These checks establish that the live pipeline runs and its references resolve. They do not establish that every generated statement is correct. Broader claim-support and terminology evaluation remain necessary, along with academic-rule review.

## Reproduction

Set a local `GEMINI_API_KEY` as described in the repository README. Use these values if an existing environment file overrides the new defaults:

```dotenv
EMBEDDING_MODEL=gemini-embedding-2
GENERATION_MODEL=gemini-3.5-flash-lite
EMBEDDING_DIMENSION=768
```

Then run:

```bash
python scripts/build_index.py
python scripts/verify_live.py
python -m pytest -q
```

The verification script covers the first three retrieval modes. The additional scenarios used an incoming student with AI/hardware interests; a changed embedded-systems goal with experienced programming background; ECE101 completed with a B and some programming experience; and an unsupported paleontology question. Their exact retrieved evidence, outputs, rule results, and timings are saved in [the credential-free trace](evidence/gemini_live_2026-10-23.json).

## Remaining work

The app still uses bundled academic evidence. Automatic official-source fetching, on-use revalidation, scheduled database refresh if a database is introduced, live Adzuna checks, and browser screenshots remain pending. These provider checks do not complete those features. No keys need to be committed for a teammate to reproduce the tests.
