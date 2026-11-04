# Grounded explanations through statement selection

Implemented November 4, 2026, in the development repository. The submitted midproject repository and preserved artifacts remain unchanged.

The November 3 audit showed that correct citation IDs could accompany false or unsupported claims. Nine authored unsupported/contradicted claims passed the old reference checker. Merely telling a model to label facts separately from recommendations also leaves a bypass: a factual assertion can be called a suggestion.

The production provider now selects application-owned statements instead of writing unrestricted explanation prose. The backend owns their wording, fact/suggestion labels, and evidence references. This is a deliberate output constraint, not a general semantic-entailment classifier. It reduces free-form personalization; selection relevance and the underlying source accuracy still need evaluation.

## Runtime contract

1. Refresh the request's sources, retrieve evidence, and compute academic results and learning stages as before.
2. Build a bounded registry from the active records and supplied evidence. Keep each recommended course's complete description/prerequisite bundle together.
3. Send the profile, question, evidence, application results, and registry to Gemini. The model selects up to five allowed records and one to four distinct owned statement IDs per record, or a fixed clarification code.
4. Rebuild the registry against the authoritative request catalog. Check schema, exact context binding, record ownership, duplicates, and supplied evidence.
5. Materialize the existing display answer using application-owned wording/types/citations, then validate them again. Invalid output leaves the source cards and academic results available, with a sanitized error category.

`src/grounding.py` implements this contract. `ExplanationSelection` is the provider schema; `GeneratedAnswer` remains the rendered shape and the frozen audit's legacy authored-answer format. The old membership checker is retained as `validate_references`; production uses `validate_answer(answer, context, catalog)`.

Contract: `statement-selection-v1`. Prompt: `p07-v7-statement-selection`. A registry contains at most 80 statements, each at most 1,400 characters with one to eight supplied evidence IDs. Oversized or raw-URL-bearing candidate wording is omitted. Registry overflow fails closed. Hashes bind statement IDs to the complete context and canonical wording; an ID from a different context is rejected.

## Allowed wording

| Statement | Authoritative input and limitation |
| --- | --- |
| Description and credits | Exact active record fields, attributed to their source; snapshot/stale descriptions are labeled saved |
| Academic result | Application-computed satisfied/unsatisfied/unknown; satisfaction never establishes complete enrollment eligibility |
| Reviewed condition | Literal bound source statement, matching catalog edition and supported snapshot/verified rule state; separate prerequisite citation |
| Source check | Verified descriptive source with a nonnull, timezone-aware successful-check timestamp; does not verify every academic condition |
| Resource scope/version | Independent study without established university credit/equivalency; resource version remains separate from the academic catalog year |
| Learning connection/activity/stage | Team-authored suggestions and application stages, explicitly labeled recommendations rather than catalog requirements |
| Clarification | One of two fixed application messages selected by code |

Unknown ECE rules remain unknown. Failed, changed, stale, or unsupported reviewed conditions cannot become positive academic facts through a model selection. No registry template establishes future offerings, guaranteed jobs/salaries, official semester placement, or complete registration clearance.

The registry is reconstructed before accepting a selection. Modified evidence, missing prerequisite chunks, changed source dates, mismatched rule results, phases, field provenance, or statement wording are rejected. Model-supplied fact/suggestion labels, citations, prose, and clarification text are not accepted. Relabeling an unsupported factual assertion as a recommendation does not bypass validation.

The inspector's **Available explanation statements** table exposes the registry and selected rows. Request traces include the contract, selected IDs, validation outcome, and error category. They do not include rejected raw model prose or credentials. Without a generation attempt the statement-validation result remains null; a fixed abstention can pass validation without counting as a completed explanation.

## Offline evidence

The [JSON report](evidence/statement_validation_2026-11-04.json) and [readable report](evidence/statement_validation_2026-11-04.md) use the unchanged frozen November 3 corpus and labels. They made zero source-refresh, embedding, or generation requests.

| Check | Result |
| --- | --- |
| Automated suite | 386 passing tests, including 67 dedicated grounding cases and 17 Streamlit interactions |
| Roadmap scenarios | 18/18 expectations pass |
| Earlier citation-integrity audit | Same 16/16 expected outcomes; same nine unsupported claims admitted by that earlier checker |
| New render contract | Zero unsupported reviewed claims admitted |
| Canonical positive controls | 82/82 statement selections accepted across the authored probe contexts |
| Legacy authored prose | 0/16 answers accepted, including true paraphrases outside the canonical wording |
| Keyword retrieval | Recall@5 0.8229; unchanged references, misses, and ranking scores |

The 82 controls include statements in multiple contexts, not 82 independently reviewed facts. The strict format rejects all unlisted prose, so rejecting legacy true paraphrases is expected. These results must not be reported as a model hallucination rate, live selection accuracy, independent review, or unrestricted factual inference.

Grounding cases cover correct facts and citations, literal OR conditions, unresolved academic status, dated/changed conditions, edition mismatch, freshness/version wording, foreign/invented/stale statement IDs, duplicate/mutated selections, schema-only prose attempts, wrong wording/type/citations, disguised factual suggestions, context/registry corruption, fixed clarifications, size/URL limits, source-card recovery, and trace states. Controlled provider tests exercise the exact JSON schema and reject legacy responses. Streamlit tests exercise statement inspection and rejected-output recovery.

Run the unchanged frozen audit with the current validator:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/evaluate_reviewed.py --output .cache/statement_validation.json --markdown .cache/statement_validation.md
```

The evaluator's current success status additionally requires zero unsupported reviewed claims admitted by the render contract and all canonical controls accepted. The earlier baseline artifacts keep their original implementation hashes, scope, and exit interpretation.

## Remaining checks

No real Gemini request tested this schema change. October 23's successful model calls used the earlier output format. Run `scripts/verify_live.py` with locally configured credentials to verify current provider compatibility and inspect actual statement selections before describing this contract as live-verified. That script uses the saved corpus for continuity; `scripts/check_sources.py` checks the current public-source path separately.

The format cannot correct an inaccurate source, parser, reviewed rule interpretation, or team-authored learning suggestion. It also cannot establish that a valid selected statement answers the student's question well. Review actual selections, add independent judgments and broader cases, and compare opt-in semantic/hybrid retrieval. The known vocabulary/coverage guard and paraphrase misses are the next backend concern. Wider academic evidence, live Adzuna verification, free-only OpenRouter integration, and account persistence remain separate unfinished work.

Later November 4: [query interpretation](20_QUERY_INTERPRETATION.md) implements bounded aliases and question-focused course selection, with a separate development measurement and 444 passing tests. The 386-test count above records this explanation unit's original verification. Source/label identities and its historical report remain unchanged. Live statement-selection verification is still pending.
