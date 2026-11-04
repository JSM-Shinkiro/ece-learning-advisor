# Reviewed development evaluation

Fixed saved corpus; assistant-authored references. This is not an independent held-out benchmark.

Suite: `saved-corpus-review-2026-11-03-v1` · 10 evidence chunks · cutoff 5.
Suite hash: `8a2c2ee00f57fb07532d4f53feed1e8d591d0eda01d3b3653efd723a5649a689`.
Corpus hash: `8df543f9bfe5d83374385ea5f756160d42144d9ab04bfc20b49e7f78059d643d`.
Retrieval query mode: domain-alias expansion without profile expansion.
Expanded-query results use aliases authored after the known misses; they are development tuning, not held-out validation.

| Method | Split | Cases | Precision | Maximum precision | Recall | MRR | nDCG |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| keyword | development | 10 | 0.3600 | 0.4000 | 0.9167 | 0.9333 | 0.8800 |
| keyword | validation | 6 | 0.4000 | 0.4000 | 1.0000 | 1.0000 | 0.9302 |
| keyword | all | 16 | 0.3750 | 0.4000 | 0.9479 | 0.9583 | 0.8988 |

Roadmap expectations passed: 18/18.
Citation-integrity expectations matched: 16/16 authored probes.
Authored unsupported/contradicted claims admitted by citation checks: 9.
Claim verdicts are supplied review labels. Citation acceptance does not infer factual support.

## Application-owned explanation contract

Contract: `statement-selection-v1`. Unsupported reviewed claims admitted: 0.
Canonical statement controls accepted: 82/82.
Legacy authored answers accepted: 0/16.
This contract also rejects true paraphrases that are outside the application-owned wording. It does not classify unrestricted prose entailment.
Controls are authored offline selections, not live model accuracy or recommendation-quality measurements.

Embedding origin: none. Generation calls: 0. Source refresh calls: 0.
Local ranking times exclude network, generation, source refresh, and interface rendering.

## Missed relevant evidence

- `retrieval_data_structures` (keyword): recall 0.5000.
- `retrieval_neural_models` (keyword): recall 0.6667.
