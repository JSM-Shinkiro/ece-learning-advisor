# Comparing retrieval methods with the same review

Implemented and verified November 6, 2026. The external-review scorer now accepts keyword, semantic, and hybrid retrieval. The same completed relevance form can score each method without provider or source requests. Semantic/hybrid methods read a separately created embedding snapshot bound to the exact packet, saved evidence, and raw/expanded query treatment.

This prepares the comparison workflow. **No actual independent judgments or new retrieval-quality result were collected in this unit.** Existing development questions and assistant-authored labels retain that origin.

## Workflow in PowerShell

First prepare the usual unscored packet and blank form:

```powershell
.\.venv\Scripts\python.exe scripts/review_retrieval.py prepare --output .cache/review_v1
Copy-Item .cache/review_v1/review_template.json .cache/review_v1/review_reviewer_a.json
```

Supply only the original packet, guide, and blank form to the reviewer. Keep embedding files and score reports separate: they expose the effective queries, vectors, or rankings and could influence judgments. The original export contains no prior grades, rankings, or expansion hints. Candidate shuffling and file separation are not an authenticated blind study.

For semantic/hybrid comparison, explicitly precompute a vector snapshot using the configured Gemini key/model/dimensions:

```powershell
.\.venv\Scripts\python.exe scripts/review_retrieval.py embed --packet .cache/review_v1/packet.json --live-embeddings --output .cache/review_vectors_raw.json
```

`--live-embeddings` is required. This action sends the packet's exact evidence through the existing document-embedding adapter as needed and sends each effective question through its query-embedding adapter. It receives no reviewer grades, student profile, or generation context, and never requests generation or source refresh. Existing matching public-document vectors are reused from the configured cache. Each question requires an embedding-adapter invocation. For the default 10-chunk/16-question packet, creation can need ten document and sixteen query invocations; a matching cached document index avoids those document calls. Inputs remain bounded to 100 chunks, 50 questions, and 1–3,072 dimensions. Model access and quota remain necessary when using the real adapter.

After the reviewer completes the copied form, score all three methods using new output paths:

```powershell
.\.venv\Scripts\python.exe scripts/review_retrieval.py score --packet .cache/review_v1/packet.json --review .cache/review_v1/review_reviewer_a.json --method keyword --output .cache/reviewer_a_keyword_raw.json
.\.venv\Scripts\python.exe scripts/review_retrieval.py score --packet .cache/review_v1/packet.json --review .cache/review_v1/review_reviewer_a.json --method semantic --embeddings .cache/review_vectors_raw.json --output .cache/reviewer_a_semantic_raw.json
.\.venv\Scripts\python.exe scripts/review_retrieval.py score --packet .cache/review_v1/packet.json --review .cache/review_v1/review_reviewer_a.json --method hybrid --embeddings .cache/review_vectors_raw.json --output .cache/reviewer_a_hybrid_raw.json
```

Keyword remains the default and does not accept an unused embedding file. Semantic/hybrid methods require one; they never initialize a provider when it is missing. A blank or incomplete form cannot be scored. Existing packet directories, vector files, and reports are not overwritten. Provider closure and sanitized errors also apply when embedding creation fails.

For the expanded-query treatment, create a separate snapshot with `embed --query-mode expanded`, then pass `--query-mode expanded` to each score command. A raw snapshot cannot be used for expanded scoring. Choose separate output names and compare reports only when packet, review, cutoff, and query treatment match. Creating a new packet, even from the same questions, requires a snapshot bound to that new packet.

## Binding and reports

`src/review_vectors.py` validates packet/corpus/full-catalog fingerprints, exact chunk IDs and order, evidence-text hashes, effective question text and order, query policy, embedding format, dimensions, aware creation time, and a full snapshot fingerprint. Zero, nonfinite, non-normalizable, ragged, boolean, and string vectors are rejected. Changing source freshness or rule metadata invalidates the catalog binding even if the embedded evidence text did not change. Rehashing a modified input cannot bypass those exact input checks.

Review packets, forms, and custom-question files retain the 2 MB input limit. Vector files allow up to 24 MB, with duplicate JSON keys still rejected. Files contain JSON numbers and strings; loading never uses pickle. Vectors are normalized by the existing cosine retriever at ranking. The embedding-format identifier matches the existing application's prefix/cache format. Snapshot creation reuses that cache rather than building a second indexing implementation.

Score reports now use **schema 2**. Packet, form, and vector snapshot schemas remain 1. Reports retain the exact packet/review fingerprints, reviewer self-reported role, question origin, judgments, notes, metric conventions, query treatment, and defined/undefined metric counts. They add the selected method, keyword/cosine component scores, implementation fingerprints, and a compact embedding-snapshot reference. Full vectors are omitted from score reports. `embedding_calls`, `generation_calls`, and `source_refresh_calls` in a score report are zero; the separate snapshot records adapter invocations during creation and cache state.

Fingerprints establish input consistency. They do not authenticate who supplied vectors, which provider/model actually produced them, reviewer independence, or new-question provenance. Vector metadata is explicitly `operator_supplied_unverified`. The tool validates bindings, not an external attestation. A new study still needs genuinely new questions, independent judgments, a frozen experiment, and separate reporting of tuning. It does not score generated answers, source freshness, academic eligibility, or live discovery.

## Verification

The full suite passes **1,183 tests**, including **47 new vector/review cases**, the existing 59 reviewer-workflow cases, and the unchanged 61 Streamlit interactions. New checks cover all three methods and both query treatments, analytic unit-vector rankings for individual questions, document-cache reuse, complete and all-zero judgments, malformed/nonfinite vectors, stale inputs, rehashed changes, explicit provider-use boundaries, no-overwrite behavior, sanitized failures, and provider cleanup.

The [November 6 evidence](evidence/review_methods_2026-11-06.json) includes a separate round trip in the production-only environment, without pytest installed. A clearly labeled controlled adapter creates raw/expanded snapshots: ten document and 32 query invocations in total, with document reuse on the second export. Six score reports use the same controlled-fixture form, make no provider/source calls, and preserve existing outputs. Implicit creation and blank grades are rejected. All network clients are blocked, with zero network attempts and zero generation calls.

The old raw/expanded keyword Recall@5 controls remain 0.8229167 and 0.9479167 on the unchanged authored references. Neural fixtures verify the method routing and artifact contract; their numbers are not new quality results. Real Gemini snapshot creation was not rerun in this unit; it uses the unchanged existing adapter. No credentials or new human judgments were used in verification. All eight local runtime checks pass. The application UI, academic interpretations, frozen corpus/labels, historical evidence, and submitted midproject artifacts are unchanged.
