# Current Gemini development verification

Verified November 4, 2026, using the latest Gemini credential explicitly authorized by the user. It was supplied to transient processes through hidden input and was not written to environment files, repository files, or saved results. OpenRouter was not used. The submitted midproject repository and all earlier measurements remain preserved.

No application change was needed: the existing pinned adapter accepted the current statement-selection schema and completed real retrieval/generation requests.

## Live integration

Configuration: `google-genai==2.33.0`, `gemini-embedding-2`, 768 dimensions, `gemini-3.5-flash-lite`, prompt `p07-v7-statement-selection`, contract `statement-selection-v1`. The saved collection has ten evidence chunks. These are authored integration profiles, not actual student records or an independent evaluation.

The [credential-free report](evidence/gemini_statement_live_2026-11-04.json) records selections, materialized answers, request traces, provider-call counts, source checks, implementation hashes, and an implementation-assistant review.

| Scenario | Outcome | Index cache | Total seconds |
| --- | --- | --- | ---: |
| Picture-pattern question, keyword | Answered; valid statement selection | Not used | 6.971 |
| Same question, semantic | Answered; real 10 × 768 index built | Miss | 4.442 |
| Same question, hybrid | Answered; validated selection | Hit | 2.096 |
| Embedded board/button question | ECE372A selected; academic uncertainty preserved | Hit | 1.544 |
| ECE101 completed with B, CSC120 question | Completed course excluded; dated CSC120 condition qualified | Hit | 1.780 |
| Unsupported marine-biology question | Coverage guard stopped all provider calls | Not used | 0.001 |
| Runtime CSC110 discovery with MATH112 B | Current source condition verified; qualified explanation selected | Not used | 11.856 |

All seven integration expectations passed. Six made actual generation calls; the unsupported case tests the application guard, not model abstention. The acceptance run made ten document-embedding calls, four query-embedding calls, and six generation calls. A separate successful generation preflight is included in the report, making seven generation calls including credential validation.

The first five supported requests used saved evidence, with descriptions labeled saved. The CSC110 request checked the scoped COSCBS program and relevant course pages before generation; it made no resource or opportunity-provider requests. Its stored condition was satisfied by the controlled coursework history, without establishing complete enrollment eligibility.

The six answers selected the expected focus record. Their displayed wording, claim types, citations, and preparation limitations came from the application-owned registry and passed production validation. The implementation assistant reviewed those selections and limitations; no instructor/advisor/student review is implied. This does not measure unrestricted prose entailment, a model hallucination rate, or correctness of every underlying source.

Times are single observations, not averages or performance guarantees. The CSC110 case includes public-source checks; the saved-corpus cases do not. Browser rendering and startup are excluded. No billed-cost figure is inferred from request counts.

## Real embedding comparison

The separate [JSON report](evidence/neural_expanded_evaluation_2026-11-04.json) and [readable report](evidence/neural_expanded_evaluation_2026-11-04.md) compare all three methods on the same 16 frozen reference questions, with bounded alias expansion and no profile terms.

| Method, all references | Precision@5 | Recall@5 | MRR@5 | nDCG@5 |
| --- | ---: | ---: | ---: | ---: |
| Keyword | 0.3750 | 0.9479 | 0.9583 | 0.8988 |
| Semantic | 0.4000 | 1.0000 | 0.9688 | 0.9523 |
| Hybrid | 0.4000 | 1.0000 | 0.9688 | 0.9518 |

This run used the actual Gemini document index built above, reused it from cache, and made 16 real query-embedding calls shared by semantic and hybrid ranking. It made zero new document-embedding, generation, or source-refresh calls. The keyword result matches the earlier expanded-query measurement. Across acceptance and comparison, there were ten real document and twenty real query embeddings.

These results concern a tiny, closed collection with assistant-authored judgments. Aliases were developed after inspecting known misses, including the named validation examples. Recall 1.0 here does not imply perfect retrieval on new students or broader material. The precision ceiling remains 0.4. Independent judgments, wider unseen queries, and source/edition coverage remain necessary. The old raw-query score of 0.8229 and every historical report remain unchanged.

The comparison also retains the 18 roadmap checks, 82 canonical controls, and authored claim audit. Its generation count is zero; those claim labels do not become actual generated-answer quality measurements merely because its embeddings are real.

## Reproduction and next work

Configure a Gemini credential locally, then use the existing opt-in scripts:

```powershell
.\.venv\Scripts\python.exe scripts/verify_live.py
.\.venv\Scripts\python.exe scripts/evaluate_reviewed.py --methods keyword semantic hybrid --live-embeddings --query-mode expanded --output .cache/neural_expanded_evaluation.json --markdown .cache/neural_expanded_evaluation.md
```

`verify_live.py` covers the three basic retrieval modes. Additional scenario profiles and their exact inputs are in the saved report; runtime discovery uses the scoped source configuration recorded there. A fresh comparison cache will require document embeddings. These commands consume real provider quota.

The unchanged application revision passed 482 automated tests before these live checks. This unit adds evidence/documentation, not application behavior. The former credential blocker is resolved for authorized development tests; credentials remain transient. Next priorities are broader independent evaluation, unresolved ECE/edition evidence, live Adzuna verification, and deployment stability. Any future OpenRouter integration remains free-only.
