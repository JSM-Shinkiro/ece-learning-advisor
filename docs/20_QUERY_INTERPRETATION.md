# Student wording and query coverage

Implemented November 4, 2026, after the bounded explanation contract. Development repository only; the midproject submission and earlier evidence artifacts remain preserved.

The former vocabulary guard rejected the button and picture-pattern examples before retrieval began. Broad career/profile terms could also fill an exploring roadmap's course slots while displacing a course relevant to a specific question. This unit shares a bounded query interpretation between coverage checks and retrieval, then gives a specific question a limited course preference during context assembly.

## Interpretation policy

`src/query.py` defines `p07-domain-aliases-v1`. Nine explicit whole-token rules cover visual recognition/learning, board events, processor execution/memory, microcontroller I/O, introductory coding, and tensor practice. Each rule requires its stated combination of original student words. Matching is case-insensitive; added terms never trigger another rule.

Only canonical terms already present in the active collection's titles, summaries, or topics may be added. Terms are deduplicated and capped at 12. They are search policy, not source evidence or new course/academic facts. The query stays within 5,000 characters, reserving space for its aliases even with a full-length profile. No extra model call performs interpretation.

| Example wording | Added search concepts | Relevant course |
| --- | --- | --- |
| Train computers to pick out patterns from pictures | Computer vision, deep learning, neural networks | ECE425 |
| Make a board react when a button is pressed without polling | Microcontrollers, interrupts, hardware interfaces, embedded systems | ECE372A |
| How a chip speaks with memory and executes machine instructions | Processor organization, instruction sets, memory caches, computer architecture | ECE369A |

An explicit question takes precedence over profile interests for coverage/alias interpretation. Interests are used when there is no question. Career and experience defaults cannot rescue an unrelated explicit question. Generic questions can still produce the selected direction's standard roadmap.

Coverage checks run before source fetching and again against the active request catalog. Broad words such as training, models, project, and patterns alone do not establish computing coverage. Whole-token combinations avoid substring matches and obvious ambiguities such as recipe instructions for potato chips or fashion-model training. Unsupported requests skip both source requests and provider initialization. This is still a vocabulary policy, not a general semantic classifier; unfamiliar or ambiguous wording can require clarification.

## Question preference and academic boundaries

For a nonempty question, the service performs a small keyword lookup without default career terms. It may prefer one existing course when a domain alias matches, a known course is named, or at least two distinct original query tokens occur in that course's title/summary/topics. The candidate must fit the selected career. This local preference adds no embedding request and does not relabel keyword results as semantic results.

The preference operates within the retrieved candidates and context budget. Novices retain a programming foundation. Completed courses stay excluded. Generic exploring profiles retain both directions; a specific question may use a slot that would otherwise show a broad career goal. Complete prerequisite evidence bundles remain atomic. Academic results and learning-stage policy are evaluated independently, so a question preference does not establish enrollment eligibility or promote an unknown condition to satisfied.

The context preserves the original question. The inspector shows **Search also uses** when terms were added. Traces record the query-policy version, matched aliases, added terms, and preferred course IDs in `focused_record_ids`; they do not add the raw profile or question to routine traces.

## Development measurements

The [expanded-query JSON](evidence/query_expansion_2026-11-04.json) and [readable report](evidence/query_expansion_2026-11-04.md) use the original frozen corpus and labels. Default evaluation still ranks raw questions, preserving its original inputs and scores. Expanded evaluation adds aliases without profile/career expansion, making the treatment explicit.

| Input mode, all 16 references | Precision@5 | Recall@5 | MRR@5 | nDCG@5 |
| --- | ---: | ---: | ---: | ---: |
| Original raw questions | 0.3125 | 0.8229 | 0.8229 | 0.7571 |
| Bounded alias expansion | 0.3750 | 0.9479 | 0.9583 | 0.8988 |

The aliases were authored after inspecting known misses, including examples in the named validation split. These are development-tuning results, not held-out gains or independent student evidence. Data-structure and neural-model queries still miss some relevant chunks at cutoff five; the readable report retains those misses. No source-refresh, embedding, or generation calls were made for these scores.

The separate [context comparison](evidence/query_coverage_2026-11-04.json) runs the saved-corpus keyword recommendation path with an experienced exploring profile. The before state was reproduced from exact development commit `8878614bf8810b4c96f5c9c4861ff849656ccb28` using the pinned environment. All other profile fields use defaults. Of the 16 frozen queries, 15 have a grade-three course/resource target; the other has only a direct career-mapping target, which is not a recommendation card.

Before this unit, two queries were blocked by coverage, and eight of the 15 queries with a direct course/resource target retained one in their recommendation context. Afterward, none of the 16 are blocked and all 15 target-bearing queries retain a directly relevant record. This measures context visibility, not answer quality, full relevant-set recall, or real model behavior. The raw corpus, full saved catalog, relevance labels, and historical reports remain unchanged.

All 18 roadmap expectations still pass. The explanation audit still accepts 82/82 canonical controls and admits zero unsupported reviewed claims through the strict output contract. The old citation checker still admits the same nine unsupported claims for comparison.

## Verification and reproduction

The full suite passes **444 tests**, including **56 query-policy cases** and **19 Streamlit interactions**. Coverage includes 15 positive phrasings, 15 unrelated/ambiguous negative examples, source-prefilter agreement, controlled statement selection, generic and focused exploration, completed courses, career boundaries, input precedence, absent catalog coverage, term/query limits, evidence immutability, preserved raw scores/labels, explicit expanded reports, and shared neural-query inputs without extra provider calls. The two added UI cases display the recovered roadmap and added search terms.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/evaluate_reviewed.py --output .cache/raw_query_evaluation.json
.\.venv\Scripts\python.exe scripts/evaluate_reviewed.py --query-mode expanded --output .cache/expanded_query_evaluation.json --markdown .cache/expanded_query_evaluation.md
```

`--query-mode expanded` is independent of the existing explicit live-embedding opt-in. A semantic/hybrid comparison uses the same effective query for both methods and shares its query embedding. Controlled test vectors validate orchestration only and are not neural-quality results. Provider failure still stops the evaluator rather than silently substituting keyword scores.

No Gemini key was configured locally for this unit, so the new statement-selection schema and alias-expanded semantic queries remain unverified against a real provider. Next, verify those calls with locally configured credentials, review actual selected explanations, and broaden independent queries and academic-rule evidence. The rule set does not cover every paraphrase, infer prerequisites, switch the student's career, discover unrestricted sources, or establish complete degree/semester plans.
