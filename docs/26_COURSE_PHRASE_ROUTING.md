# Course title and topic routing

Implemented and live-checked November 4, 2026; final automated verification and documentation completed November 5. Students can now use reviewed course titles and topic phrases to request bounded discovery without knowing a course code. The midproject files, saved corpus, frozen evaluation labels, and academic interpretations are unchanged.

## Reviewed scope

`data/connectors/course_discovery.json` binds phrases to the same six course identities already available through the configured foundation sections. Examples include:

| Course | Reviewed routing examples |
| --- | --- |
| CSC110 | Introduction to Computer Programming I; introductory computer programming |
| CSC144 | Discrete mathematics; discrete math; predicate logic |
| CSC210 | Software development; unit testing; version control |
| ECE201 | Programming 2; object-oriented programming; C++ programming |
| ECE220 | Basic circuits; circuit analysis; phasors |
| ECE274A | Digital logic; register transfer language |

These are application-reviewed routing hints, not university requirements or independently validated semantic judgments. Each phrase must bind a known course code/ID. Configuration rejects empty, oversized, duplicate, unbound, or ambiguous phrases, plus generic standalone labels such as “programming” and “logic.” A course accepts at most eight phrases of at most 80 characters. Normalization handles case, spaces, and hyphens while preserving language names such as C++. Whole-phrase matching avoids substrings such as “metaphasors.”

Policy `p07-course-request-priority-v2` considers at most 16 combined distinct targets. Explicit course codes come first; matched phrases follow their first-mention order. The question takes precedence, with interests used only when it is empty. Several phrases for the same course use one slot. Remaining candidates retain source order. The matcher does not infer negation, unstated intent, general synonyms, or arbitrary course titles.

## Source and generation boundaries

The three-discovery, eight-course, two-program, and three-worker limits remain unchanged. Career and catalog-edition scope still apply. A phrase cannot invent a URL, fetch a course absent from freshly verified selected sections, or silently select another career's program. Downloaded metadata must confirm the configured identity, code, edition, and existing metadata constraints.

A reviewed phrase can open the initial source gate even when the saved collection lacks its vocabulary. After fetching, only added, dated cached, or already collected records can supply preferences. The application checks their career scope, edition, and recorded completion before adding missing canonical course codes to the bounded retrieval query. `discovery_query_terms` records those additions; the first eligible target supplies the focus preference. Missing or mismatched records cannot force generation through a phrase hint. Explicit offline mode creates no new discovery preferences.

This allocates downloads and guides relevance. It does not approve enrollment, alter grades or placement, establish substitutions, or add model-authored facts. Descriptions, separate prerequisite proofs, source freshness, context limits, and application-owned explanation statements retain their existing contracts. Fetching several records does not guarantee a complete comparison answer.

Matched phrases, course codes, selection reasons, and outcomes appear in the inspector and request trace. Public content caches contain no free-text question or per-user routing priority. Changing a question recomputes the matches even when HTTP 304 reuses public program metadata.

## Verification and source recovery

The complete suite passes **725 tests**, including **45 phrase-routing cases** and **35 Streamlit interactions**. Controlled cases cover reviewed titles/topics, punctuation and boundaries, C++ versus C, code precedence, scope, mention limits, configuration ambiguity, source failures, offline behavior, conditional caches, grounded provider integration, and the two new UI paths without rerender fetches. These are controlled integration cases, not live model-accuracy measurements.

The [November 4 live evidence](evidence/phrase_routing_2026-11-04.json) records a normal source-check request for “phasors and unit testing.” It added ECE220, CSC210, and default CSC110 in that order. All six selected course pages, both programs, and both learning resources passed their checks. The preview focused ECE220 and added ECE220/CSC210 as retrieval terms. The run took about 16.6 seconds, used no credentials, and made no embedding, generation, or opportunity requests. This is one observation, not a performance or uptime benchmark.

Separate bounded resource-adapter probes also succeeded under the existing HTTP limits, validating [PyTorch Quickstart](https://docs.pytorch.org/tutorials/beginner/basics/quickstart_tutorial.html) version 2.15.0+cu132 and [CS50](https://cs50.harvard.edu/x/) edition 2026. Saved diagnostic events include only event names, elapsed times, and exception type names when present; they exclude raw transport settings, headers, cookies, credentials, and response bodies. Successful proxy response headers arrived after roughly 3.8–4.4 seconds, followed by TLS setup and successful page reads.

Those observations do not identify the cause of the earlier timeouts. The [previous failed checks](25_REQUESTED_COURSE_DISCOVERY.md) retain their original results. No timeout increase, automatic retry, alternate host, or permanent reliability fix is claimed; ordinary failures still retain clearly dated evidence.

Reproduce the source-only path with:

```powershell
.\.venv\Scripts\python.exe scripts/check_sources.py --career ai_ml --question "How can I learn phasors and unit testing?"
```

Current responses may differ from the saved observation. The command verifies selected sources and reports target outcomes separately; success is not an academic eligibility decision. Frozen retrieval metrics remain historical development measurements. Broader phrases, independent selection/source-interpretation review, catalog editions, and deployment evaluation remain open work.
