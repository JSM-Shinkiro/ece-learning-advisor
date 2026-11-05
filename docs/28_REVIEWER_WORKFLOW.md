# Retrieval reviewer workflow

Implemented and verified November 5, 2026. A separate offline command now prepares unscored evidence packets and evaluates completed relevance judgments. It enables an external review; **no real reviewer judgments have been collected in this unit**. The existing frozen references, published measurements, application behavior, and submitted midproject files are unchanged.

## What the reviewer receives

The default packet contains the existing 16 development questions and all ten saved evidence chunks. Each question has a separately shuffled candidate order, without retrieval scores, previous grades, split labels, expected answers, rationales, or query-expansion hints. The seed makes candidate order reproducible. This hides ranking information; it is not an authenticated blind study.

Three files are exported:

| File | Purpose |
| --- | --- |
| `packet.json` | Exact questions, candidate identities, evidence, source metadata, and snapshot fingerprints |
| `review_template.json` | Blank grades plus reviewer alias, role, and completion timestamp |
| `review_guide.md` | Questions, candidate order, saved evidence text, source links, and grading instructions |

All grades start as JSON `null`. The reviewer uses the existing relevance scale: 0 unrelated, 1 broad background, 2 useful supporting evidence, 3 direct evidence. Every chunk needs an explicit grade for every question. All-zero judgments are valid when the collection cannot help. Optional question notes can explain uncertainty. Reviewers should judge the saved evidence; current linked pages may differ from that snapshot.

Use an alias containing letters, numbers, underscores, or hyphens. Names and email addresses are unnecessary. Set the self-reported role to `independent_reviewer`, `project_contributor`, or `controlled_fixture`. A role value does not authenticate independence. The aware ISO completion timestamp must not precede packet creation.

## Run in PowerShell

From the repository root, with the existing environment:

```powershell
.\.venv\Scripts\python.exe scripts/review_retrieval.py prepare --output .cache/review_v1
Copy-Item .cache/review_v1/review_template.json .cache/review_v1/review_reviewer_a.json
```

Read the guide and fill the copied form, keeping the packet fingerprint, question IDs, and evidence IDs. Enter the alias, role, completion timestamp, and integer grades. `Get-Date -Format o` supplies a local timestamp with timezone. The blank template cannot be scored.

```powershell
.\.venv\Scripts\python.exe scripts/review_retrieval.py score --packet .cache/review_v1/packet.json --review .cache/review_v1/review_reviewer_a.json --output .cache/reviewer_a_raw.json
.\.venv\Scripts\python.exe scripts/review_retrieval.py score --packet .cache/review_v1/packet.json --review .cache/review_v1/review_reviewer_a.json --query-mode expanded --output .cache/reviewer_a_expanded.json
```

Use a separate form and reports for each reviewer. Existing packet directories and report files are never overwritten; choose new paths for another export or run. Exit 0 means the requested export or scoring operation completed. It does not certify good scores or academic correctness. Exit 2 means invalid/incomplete input, a snapshot mismatch, or a file/output problem. Input text is not echoed in CLI errors.

Custom questions use a JSON list of objects with only `case_id` and `query`:

```json
[
  {"case_id": "question-01", "query": "How do processors execute instructions?"}
]
```

This is a format example, not a new independent benchmark. Save the reviewer-authored question file separately, then pass `--questions .cache/questions.json --packet-id p07-custom-v1` to `prepare`. Custom questions are labeled `custom_questions_unverified`; the tool cannot establish who authored them or whether developers have seen them. Default questions are labeled `existing_development_questions` and remain development material even if another person grades them. Question IDs and normalized question text must be unique. Inputs allow at most 50 questions and 100 evidence chunks; JSON files are limited to 2 MB.

## Validation and scoring

Before scoring, the backend checks the packet fingerprint, evidence corpus, full catalog snapshot, exact evidence/source payload, complete candidate sets, and default question-suite identity. Freshness or structured-rule changes invalidate the snapshot even if the embedded text is unchanged. A reviewer form must bind the packet fingerprint, contain each question exactly once, and give each evidence chunk one integer grade from 0 through 3. Booleans, floats, strings, missing grades, unknown IDs, and duplicate JSON keys are rejected. Fingerprints establish content consistency, not reviewer identity or resistance to deliberate forgery.

The scorer measures **keyword retrieval only**, with raw questions by default and explicitly labeled domain-alias expansion as an alternative. It reuses the [frozen evaluator's metric conventions](18_REVIEWED_EVALUATION.md): binary relevance begins at grade 2; precision uses the fixed cutoff; nDCG uses linear gain. Reports include exact rankings, grades, notes, query treatment, precision ceiling, implementation fingerprints, and the reviewer's self-reported role. They retain the number of questions without relevant evidence and the count of defined values for each aggregate metric. Undefined recall/MRR/nDCG values remain absent rather than becoming perfect scores.

This workflow makes no source-refresh, embedding, or generation requests, does not load API credentials, and does not score generated answers or academic eligibility. Semantic/hybrid scoring remains in the earlier frozen-reference evaluator; importing external grades into that path is future work. A held-out study additionally needs genuinely new questions, independent judgments, an experiment frozen before inspection, and separate reporting of tuning decisions. This command alone supplies none of those guarantees.

## Verification

The complete suite passes **848 tests**, including **59 reviewer-workflow cases** and the existing 39 Streamlit interactions. Cases cover unscored exports, repeatable shuffling, source links, custom question provenance, complete/strict grading, duplicate keys, changed snapshots, modified packet content, no-relevant-evidence queries, raw/expanded comparisons, offline boundaries, and CLI file preservation.

The [November 5 workflow evidence](evidence/reviewer_workflow_2026-11-05.json) records a separate CLI round trip in the fresh production-only Python environment without pytest installed. Export succeeds; scoring the blank form fails without creating a report. Explicitly marked controlled-fixture forms reuse the old assistant-authored labels and reproduce the old raw/expanded keyword metrics. These checks verify the tool, not new human judgments or retrieval-quality improvement. No real reviewer responses, model calls, or source requests are included.

Next, collect separate voluntary reviews, inspect disagreements, and freeze a new question set before comparing systems. Keep the original suite and prior measurements as historical development references.
