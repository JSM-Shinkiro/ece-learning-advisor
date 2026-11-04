# Prerequisite evidence and revalidation

Implemented November 3, 2026, in the development repository. This extends the [course-source connector](14_RUNTIME_SOURCES.md). The submitted midproject files remain unchanged.

**Follow-up, November 3:** [Bounded course discovery](16_COURSE_DISCOVERY.md) shares program downloads with these prerequisite checks, adds linked descriptions with field provenance, and advances the prompt to `p07-v5-course-discovery`. The prerequisite milestone and measurements below retain their original scope and results.

## Implemented scope

CSC120's reviewed condition is bound to the [2026–2027 Computer Science BS program requirements](https://catalog.arizona.edu/programs/COSCBS/program-requirements-a1nCj), section `R1299/L40`. The stored interpretation preserves the catalog's four alternatives and minimum grade. It checks a supplied completion history; it does not establish complete enrollment eligibility.

The development collection contains five courses, two learning resources, two career mappings, and ten evidence chunks. The extra chunk is CSC120's prerequisite statement. The data version is `pilot-2026-11-03-rule-provenance-v1`; the generator prompt version is `p07-v4-rule-provenance`.

The four ECE conditions remain unknown. Candidate department pages are useful review material, but no matching current-edition interpretation has been approved for this connector:

| Course | Candidate reference | Backend state |
| --- | --- | --- |
| ECE101 | [Department course page](https://ecse.engineering.arizona.edu/undergrad-programs/courses/ECE101) | Unknown; no bound 2026–2027 proof |
| ECE369A | [Department course page](https://ecse.engineering.arizona.edu/course/ece/369a) | Unknown; page includes older catalog material |
| ECE372A | [Department course page](https://ecse.engineering.arizona.edu/undergrad-programs/courses/ECE372A) | Unknown; page includes older catalog material |
| ECE425 | [Department course page](https://ecse.engineering.arizona.edu/undergrad-programs/courses/ECE425) | Unknown; no bound 2026–2027 proof |

Do not infer Engineering advanced standing from the profile's Junior/Senior selection. Catalog requirement identifiers are references, not interpretable prerequisite statements. Department guidance that differs from a versioned catalog condition needs explicit review; a fetch must not silently choose or rewrite alternatives.

## Provenance contract

Each `RuleEvidence` entry identifies its course, catalog edition, official program source, exact section, evidence chunk, review time, normalized reviewed statement, and statement/interpretation fingerprints. Catalog validation rejects inconsistent bindings, changed reviewed text without a new fingerprint, duplicate evidence IDs, and rule citations that do not resolve to bound prerequisite chunks.

`rule_hash` includes the complete validated rule tree and its citation IDs. These hashes detect changes relative to the reviewed data; they do not prove that a human interpretation was correct. A changed interpretation needs a deliberate review and updated provenance before it can be used.

On a submitted roadmap, the backend:

1. Checks the relevant configured course pages and collects explicit prerequisite-source jobs.
2. Downloads only configured HTTPS program-requirement paths on `catalog.arizona.edu`, without following redirects or executing page scripts.
3. Validates the primary program identity, active catalog edition, and unique descriptions for the named sections.
4. Compares each observed statement with its reviewed fingerprint. Whitespace normalization is allowed; substantive changes are not auto-approved.
5. Requires every bound proof and the course-page identity/reference check to succeed before evaluating the reviewed condition as current.
6. Sends separate prerequisite evidence, application rule results, and source freshness to retrieval/generation and the inspector.

Several sections on one configured program page share a download. Several proof sources are aggregated conservatively: one successful source cannot override another unavailable or changed proof. A changed course enrollment identifier also revokes the reviewed interpretation.

## Source freshness and academic status

Page freshness and rule verification are separate. A program page can be freshly downloaded while its statement differs from the reviewed interpretation. Its source is then verified, but the rule remains changed and the academic result is unknown.

| Rule verification | Academic evaluation |
| --- | --- |
| `verified` | Evaluate the reviewed tree against recorded coursework and grades |
| `snapshot` in explicit offline use | Evaluate the dated reviewed tree and append a snapshot limitation |
| `changed` | Unknown; statement, interpretation, or enrollment reference needs review |
| `stale` | Unknown; dated cached evidence cannot establish verification for this request |
| `unavailable` | Unknown; no usable current proof or the check budget was exhausted |
| `unsupported` | Unknown; requested edition or provenance is unsupported |
| Unreviewed condition | Unknown, regardless of description freshness |

The rule result records provenance status, evidence IDs, source IDs, and reasons. The request trace records source HTTP/check status separately from aggregate `rule_status`. Last successful checks and content downloads retain separate timestamps. Failure does not advance the successful-check date.

## Evidence, context, and caching

CSC120's description cites only its course source. Its prerequisite chunk cites only the program source. Context limits include the course overview and all its prerequisite chunks as one bundle; the course cannot remain an allowed recommendation after its proof is dropped by a chunk or character cutoff. Alternative prerequisite descriptions outside the pilot collection do not invalidate a recorded, satisfied OR branch.

The generator is instructed to cite the prerequisite chunk for prerequisite claims and obey application-owned rule results. Citation checks still establish reference integrity, not semantic truth for every generated sentence. Claim-support evaluation remains open.

Both connectors share bounded HTTP downloads: at most eight course sources and two program sources per submitted request, three workers, a 3 MB response cap, connection/read timeouts, and a per-page streaming budget. These limits do not promise a fixed total request time. Each program job accepts at most 16 selected sections; each course record accepts at most eight proofs.

Program caches live under `.cache/sources/rules`, keyed by source URL, program, edition, and selected sections. Reads validate the exact identity, section set, hashes, size, and timestamp order. Atomic writes preserve rebuildability; a write failure keeps fresh in-memory evidence usable. Conditional validators are reused when supplied by the server. Failed checks use a valid dated cache or saved reviewed wording as reference material while the academic result stays unknown.

Freshness timestamps and status do not enter embedding identity. The evidence text does: changed prerequisite wording rebuilds its vector; an unchanged check reuses compatible vectors. No permanent content database or scheduled refresh job has been added.

## Verification

The pinned environment passes 172 tests, including 47 prerequisite-source cases and 14 Streamlit interactions. Controlled cases cover identity/edition/section mismatches, changed statements and interpretations, grade alternatives, complete/incomplete histories, outages, corrupt/incompatible caches, conditional checks, cache-write failures, multiple sections and proof sources, request budgets, atomic context limits, generator integration, and whole-refresh failure recovery. The interface regression confirms that a previously satisfied condition becomes unverified and displays the changed source evidence.

[Public-source observations](evidence/prerequisite_checks_2026-11-03.json) use a controlled AI/ML profile with a recorded ECE101 grade B. They made no embedding, generation, or opportunity-provider calls. UTC timestamps in the trace fall on November 4; the local development date was November 3 in Arizona.

| Observation | Result | Total backend time |
| --- | --- | --- |
| First prerequisite check, existing course cache | Course checks timed out; program section fetched; CSC120 remained unknown/stale | 12.450 s |
| Next submitted request | All requested sources unchanged and verified; CSC120's recorded condition satisfied | 4.632 s |

Both observations have the same corpus hash. The failed observation is retained. These are individual observations, not a latency benchmark or an answer-quality evaluation. Historical Gemini, Adzuna, and midproject evidence retains its original scope.

Run the public-source checker without model credentials:

```powershell
.\.venv\Scripts\python.exe scripts/check_sources.py --career ai_ml
```

Exit zero requires every requested source check and bound rule interpretation to be verified. A current source response with changed prerequisite wording returns a nonzero result.

The final command-line check returned zero with all three requested course pages and the program section verified. An unsupported 2025–2026 edition returned one without making source requests. Both outcomes are included under `cli_checks` in the evidence file; neither used a model provider.

## Next backend work

Expand bounded course/resource coverage with exact source identities and reviewed parser examples. Resolve additional academic conditions only when edition-specific evidence supports them. Keep unsupported conditions unknown, then add held-out retrieval and claim-support cases before treating the broader collection as a reliable advisor.
