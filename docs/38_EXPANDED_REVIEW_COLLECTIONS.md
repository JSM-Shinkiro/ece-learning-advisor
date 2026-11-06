# Review of the expanded catalog

Implemented November 6, 2026 MST. The review workflow now supports the saved runtime collection and exports a catalog snapshot so completed reviews remain usable after application data changes. The app's source pipeline, academic interpretations, historical measurements, and midproject artifacts remain unchanged.

## Prepared review material

[data/reviews/runtime_v1](../data/reviews/runtime_v1) contains an unscored packet for the 20-course/eight-resource collection: **12 questions, 34 evidence chunks, and 408 blank grades**. Questions in [runtime_questions_v1.json](../data/evaluation/runtime_questions_v1.json) are assistant-authored development examples, labeled `custom_questions_unverified`. They are not held out or independently authored. No relevance grades or expected answers are supplied.

| File | Use |
| --- | --- |
| `packet.json` | Immutable questions, shuffled candidate orders, evidence, source metadata, and fingerprints |
| `review_template.json` | Blank grades; copy separately for each reviewer |
| `review_guide.md` | Saved text, source links, grading scale, and workload |
| `catalog_snapshot.json` | Operator's exact catalog input for later embedding/scoring |

Provide the first three files to reviewers. Retain the catalog snapshot with the operator's inputs; keep vectors and score reports separate from reviewer materials. Do not overwrite the prepared bundle when updating the app. Export a new directory for changed questions or data.

Every question requires an explicit integer grade for every chunk: 0 unrelated, 1 background, 2 useful support, 3 direct evidence. `null` means unfinished. All-zero cases are allowed. Use an alias, a self-reported role, and an aware completion timestamp. Project contributors should use `project_contributor`; a role value does not authenticate independence. Judge saved evidence rather than changing live pages.

## Select current or archived inputs

All three commands accept mutually exclusive choices:

| Option | Evidence input |
| --- | --- |
| No option, or `--collection baseline` | Original five-course/two-resource collection, ten chunks |
| `--collection runtime` | Current saved runtime collection, currently 34 chunks |
| `--catalog-snapshot PATH` | Exact exported catalog, independent of later repository data changes |

The default remains baseline. Mismatched inputs fail before scoring or provider initialization. Archived catalog reads are bounded to 2 MB, reject duplicate JSON keys/synthetic-fixture catalogs, and validate source references. Packet validation still requires exact corpus/full-catalog fingerprints, evidence text, source metadata, complete candidate sets, and question provenance.

Default questions come from the original frozen question bank even when reviewing another collection. Their identity is checked separately from selected evidence. Reusing those sixteen questions with 34 chunks creates **544 blank grades**, not transferred baseline labels. Old ten-chunk grades cannot complete a 34-chunk form; missing judgments are not padded with zeros. Custom questions never load old relevance labels.

## PowerShell workflow

Use the prepared packet, copying the form outside its immutable directory:

```powershell
$reviewDir = "data/reviews/runtime_v1"
New-Item -ItemType Directory -Force .cache/reviews | Out-Null
Copy-Item "$reviewDir/review_template.json" .cache/reviews/reviewer_a.json
```

Read the guide and complete the copied form. `Get-Date -Format o` supplies a timestamp with timezone. An unfinished template cannot be scored.

```powershell
.\.venv\Scripts\python.exe scripts/review_retrieval.py score --catalog-snapshot "$reviewDir/catalog_snapshot.json" --packet "$reviewDir/packet.json" --review .cache/reviews/reviewer_a.json --output .cache/reviews/reviewer_a_keyword_raw.json
```

To export current data into another directory:

```powershell
.\.venv\Scripts\python.exe scripts/review_retrieval.py prepare --collection runtime --questions data/evaluation/runtime_questions_v1.json --packet-id p07-runtime-review-next --output .cache/review_next
```

Preparation and scoring use no source requests or provider calls. Optional real Gemini vector creation still requires explicit opt-in and uses configured quota:

```powershell
.\.venv\Scripts\python.exe scripts/review_retrieval.py embed --catalog-snapshot "$reviewDir/catalog_snapshot.json" --packet "$reviewDir/packet.json" --query-mode raw --live-embeddings --output .cache/reviews/runtime_raw_vectors.json
.\.venv\Scripts\python.exe scripts/review_retrieval.py score --catalog-snapshot "$reviewDir/catalog_snapshot.json" --packet "$reviewDir/packet.json" --review .cache/reviews/reviewer_a.json --method hybrid --embeddings .cache/reviews/runtime_raw_vectors.json --output .cache/reviews/reviewer_a_hybrid_raw.json
```

Use `--method semantic` for semantic scoring. Expanded queries require their own `embed --query-mode expanded` snapshot and matching `score --query-mode expanded`. All methods use the same completed form. Existing outputs are not overwritten. Changed data or query treatments cannot silently replace reviewed inputs. Reports retain schema 2 and metric conventions, adding catalog version/year and record/chunk/course/resource counts. Packet, form, and vector schemas remain 1. Reports record implementation fingerprints/query policy; archived inputs do not freeze future ranking code.

## Verification and remaining work

All **1,344 tests pass**, including 39 expanded-review cases and the existing 62 Streamlit interactions. Coverage includes question provenance, legacy compatibility, full 34-chunk grading, rejected old forms/vectors, archived snapshot integrity, stale rules/dates/stages, size/duplicate-key/schema failures, all scoring methods, CLI choices, opt-in/provider ordering, and output preservation. The pre-change legacy packet retains fingerprint `f3290347bdf4d7bb6e0dd1e64b90b50adef09efb4b089dfbe7e96b45ce56b8f2`.

All eight production-runtime readiness checks pass. [Dated evidence](evidence/runtime_review_2026-11-06.json) records a production-only CLI round trip without pytest installed. Thirteen commands verify runtime export, blank/wrong-collection rejection, archived scoring after current collection loaders become unavailable, raw/expanded vectors, six method/treatment reports, output preservation, and wrong-vector rejection. Network clients are blocked. A controlled local adapter makes 34 document and 24 query calls, reusing document vectors for the second treatment; there are zero real model/source calls and no actual credentials. Controlled all-zero grades verify tooling only, and their metric values are not reported as quality results. The published bundle remains unchanged and blank.

Actual independent grades have not been collected. Prepared questions are development material, reviewer identity/independence remains unverified, and vector/model provenance remains operator supplied. No expanded-corpus relevance score, held-out result, answer-accuracy improvement, new enrollment approval, or hosting result is claimed. Next, collect genuine judgments, inspect disagreements, and use separately frozen reviewer-authored questions for a later held-out comparison.
