# Reviewed development evaluation

Implemented November 3, 2026, in the development repository. The submitted repository, midproject report, figures, and historical measurements remain unchanged.

The original five-case smoke check could verify a few expected course choices, but could not quantify retrieval relevance or distinguish a valid citation from a supported factual statement. The new evaluator measures those concerns separately and preserves its failures.

## Scope and reference review

[The reference suite](../data/evaluation/reviewed_v1.json) contains 16 retrieval queries, 18 roadmap scenarios, and 16 authored answer probes. The implementation assistant reviewed the saved course descriptions, rule statement, source identities, and team annotations to assign the labels. They are assistant-authored development references. No instructor, academic advisor, or independent student review is implied.

The ten development queries and six validation examples share the same author and small collection; the validation split is not an independent held-out study. The claim probes are constructed examples, not captured model outputs. Their failure count is not a model hallucination rate.

The benchmark uses the unchanged saved collection: five courses, two resources, two career mappings, and ten evidence chunks. It does not refresh sources or include newly discovered course descriptions. Runtime source handling has separate integration tests and public-source observations.

Every query has an explicit grade for every evidence chunk. Judgment arrays were fixed before the first measurement and were not changed to improve the score. Their fingerprint is `025eea97ee864e5dfda13bbe03bff2c93645ab87d9a53d19073ded45e4f7561b`.

The evaluator verifies three identities before scoring: the evidence corpus hash, the full catalog snapshot hash, and the judgment fingerprint. The full snapshot captures structured rules, stages, and freshness metadata that are deliberately excluded from embedding identity. A change requires an explicit review/version decision. Reports also retain implementation-file hashes, prompt/model metadata, exact ranked chunk IDs, and expected/retrieved source IDs.

## Retrieval metrics

Raw reference questions are ranked without profile expansion. Roadmap policy is checked separately through the normal saved-corpus recommendation path, using keyword retrieval. This separation avoids confusing a default career-term expansion with direct evidence retrieval quality.

| Grade | Meaning | Counts as binary relevance? |
| --- | --- | --- |
| 0 | Unrelated to this question | No |
| 1 | Broad background | No |
| 2 | Useful supporting evidence | Yes |
| 3 | Direct evidence | Yes |

The default cutoff is five evidence chunks:

- Precision@5 is the number of binary-relevant retrieved chunks divided by five, even when fewer results are returned.
- Recall@5 divides that count by all binary-relevant chunks in the judged collection.
- Reciprocal rank is `1/rank` for the first binary-relevant result within the cutoff, or zero if none is returned. The report averages it across queries as MRR@5.
- nDCG@5 uses **linear gains**, `grade / log2(rank + 1)`, divided by the ideal graded ranking. Grade-one background can receive discounted gain without counting as a binary hit.

Metrics use equal query weights. Undefined values are excluded rather than treated as perfect scores. Rankings retain the retriever's score order and stable chunk-ID tie break. Because this small collection has few relevant chunks for each question, mean Precision@5 has an oracle ceiling of 0.4; the report includes that ceiling.

Metric references: [NIST TREC reciprocal-rank definition](https://trec.nist.gov/pubs/trec10/appendices/measures.pdf) and [scikit-learn's nDCG definition](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.ndcg_score.html). The evaluator implements the documented conventions directly and adds no scoring-library dependency. Its explicit tie ordering differs from averaging tied scores.

## Recorded baseline

The [machine-readable report](evidence/reviewed_evaluation_2026-11-03.json) and [readable report](evidence/reviewed_evaluation_2026-11-03.md) record the keyword-only run. It made zero source-refresh, embedding, or generation calls. UTC timestamps fall on November 4; the Arizona development date was November 3.

| Split | Queries | Precision@5 | Recall@5 | MRR@5 | nDCG@5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development | 10 | 0.3600 | 0.9167 | 0.9333 | 0.8731 |
| Validation examples | 6 | 0.2333 | 0.6667 | 0.6389 | 0.5637 |
| All references | 16 | 0.3125 | 0.8229 | 0.8229 | 0.7571 |

Five questions missed some reviewed relevant evidence. The pictures/pattern-recognition paraphrase had zero recall; the button and chip paraphrases had partial recall. The current vocabulary-based coverage guard also needs end-to-end paraphrase cases before these ranking findings can be treated as full application quality. No retriever tuning or judgment changes were used to hide these misses.

All 18 roadmap expectations passed, covering novice/experienced profiles, both directions, exploration, completed courses, OR alternatives, grades and incomplete histories, unsupported editions, controlled stale/changed-rule states, independent study, unsupported topics, and unresolved ECE conditions. Controlled rule-state overrides are explicitly reported; they are not live source verifications.

## Citation checks and claim-support labels

Each authored answer reason has a separate review label and rationale. The audit records whether the existing reference validator accepts the answer; it does not infer a truth judgment from that acceptance.

The 16 probes contain 18 reviewed reasons: six supported facts, three contradicted facts, eight claims with insufficient cited evidence, and one learning suggestion. All expected citation-integrity outcomes matched. **Nine unsupported or contradicted authored claims still passed the citation checks.** Examples concern credits, enrollment clearance, OR-versus-AND requirements, future offerings, freshness, university credit for a resource, job guarantees, and a sentence citing the wrong source despite another sentence having a valid course citation.

This exposes a boundary in the current runtime validator: it verifies reference membership and recommendation-level support, but does not establish each sentence's factual support. The report preserves that gap. Authored verdicts are reference annotations, not an automatic entailment model, and no claim-quality result from a real generator is reported here.

## Running the evaluator

The default run is entirely local:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_reviewed.py --output .cache/reviewed_evaluation.json --markdown .cache/reviewed_evaluation.md
```

Exit zero means the expected roadmap and reference-integrity behavior matched. Low retrieval scores and known unsupported-claim acceptance remain visible findings; exit zero does not mean factual validation is complete. Exit one reports a roadmap/integrity regression; exit two means the evaluation could not complete or its configuration/reference binding was invalid.

Optional semantic/hybrid comparison requires explicit provider-quota opt-in:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_reviewed.py --methods keyword semantic hybrid --live-embeddings --output .cache/reviewed_neural_evaluation.json
```

The optional path loads the configured Gemini key, obtains real document/query embeddings, and compares methods on the same frozen questions. It never generates answers. A query embedding is shared between semantic and hybrid ranking. Provider failure stops the run instead of silently relabeling keyword scores as neural results. This optional live path was not run for the recorded baseline; only controlled vectors tested its orchestration, and those are labeled fixtures.

The original `evaluate.py` remains the historical smoke check. No permanent database, background job, or runtime output contract changed in this evaluation unit.

## Verification and next backend work

The full automated suite passes 316 tests, including 50 evaluation tests and 16 Streamlit interactions. Evaluation tests cover hand-calculated metrics, short rankings, cutoff/grade validation, duplicate/unjudged IDs, complete judgments, full-snapshot binding, unchanged labels, atomic prerequisite bundles, reviewed-claim alignment, repeatability, provider-call boundaries, explicit neural origin, failure handling, and CLI reports/statuses.

Next, harden factual-answer validation using application-owned facts and academic results, then review actual generated answers against source evidence. Add independent reviewer judgments and broader queries before claiming a held-out result. Keep source freshness, reference integrity, retrieval relevance, roadmap policy, and factual support as distinct measures.

## November 4 follow-up

The production provider now selects application-owned explanation statements. See [grounded explanations](19_GROUNDED_EXPLANATIONS.md) and the separate [follow-up report](evidence/statement_validation_2026-11-04.json). The historical November 3 artifacts and all frozen source/label identities remain unchanged.

The current evaluator still records the earlier membership checker independently: its nine admitted unsupported claims remain visible. The new contract admits zero unsupported reviewed claims and accepts 82/82 canonical statement controls. All 16 legacy prose answers are rejected, including true paraphrases, because they are outside its fixed wording. This is an output-contract regression check, not a semantic classifier or real model result. Retrieval metrics and all 18 roadmap outcomes remain unchanged. The current automated suite passes 386 tests.

Current CLI success additionally requires zero unsupported claims admitted by the new contract and all canonical controls accepted. Actual Gemini compatibility and selection quality remain unverified for this new schema; no source, embedding, or generation calls were made for the follow-up.
