# ECE core coverage and completion-aware discovery

Implemented and checked November 5, 2026. Runtime discovery now includes two more visible sections of the [2026–2027 ECE program](https://catalog.arizona.edu/programs/ECEBSECE/program-requirements-a1nCj): core coursework `R15612/L10` and computer-engineering coursework `R15487/L10`. The foundation section remains first. Across the two configured programs, discovery now checks six sections while retaining the existing two-program, eight-course, three-discovery, and three-worker limits.

## Added course identities

The program links and individual course pages were inspected before adding routing hints:

| Course | Official course identity | Program section | Units | Enrollment reference |
| --- | --- | --- | ---: | --- |
| [ECE310 — Applications of Engineering Mathematics](https://catalog.arizona.edu/courses/0362401) | `0362401` | `R15612/L10` | 4 | `016491` |
| [ECE311 — Engineering Ethics and Contemporary Issues](https://catalog.arizona.edu/courses/0397381) | `0397381` | `R15612/L10` | 1 | `017368` |
| [ECE320A — Circuit Theory](https://catalog.arizona.edu/courses/0121101) | `0121101` | `R15612/L10` | 3 | `016492` |
| [ECE340A — Introduction to Communications](https://catalog.arizona.edu/courses/0377871) | `0377871` | `R15612/L10` | 3 | `016474` |
| [ECE351C — Electronic Circuits](https://catalog.arizona.edu/courses/0366011) | `0366011` | `R15612/L10` | 4 | `016474` |
| [ECE373 — Object-Oriented Software Design](https://catalog.arizona.edu/courses/0121261) | `0121261` | `R15487/L10` | 3 | `016496` |

These codes and identities are configured routing labels. Runtime downloads still require their presence in the selected, freshly verified program sections, then matching course identity, code, edition, and fixed units. A configured hint cannot create a URL from user text. An unbound link returning a code assigned to another configured identity is rejected as a validation failure. The units and references above describe the dated inspection; each request obtains its course fields through the normal source checks.

Reviewed topic phrases include eigenvalues, circuit theory, pulse shaping, small-signal models, engineering ethics, and class hierarchies. These route to specific course descriptions; they do not establish general intent understanding or academic rules. Broad “contemporary issues” alone is not a routing phrase. Explicit codes still take precedence, then phrase matches follow mention order.

All six new courses retain **unknown academic conditions**. The enrollment-reference numbers are not decoded into prerequisites. Program completion/grade language is not converted into a course prerequisite or advanced-standing approval. The existing four saved ECE conditions also remain unresolved.

## Preparation stages and completed courses

`DiscoveryPlan.course_stages` supplies optional team learning annotations for bound course codes. The six new courses use `intermediate`; they appear under “Build toward” while their academic condition is unknown. A stage override needs a known course identity and cannot conflict with an explicit stage on a reviewed rule entry. It applies only after the downloaded code matches the candidate's bound identity. The trace records both the resulting stage and `team_learning_annotation` origin, separate from official field-source IDs.

Policy `p07-course-request-priority-v3` removes candidates whose known code is already in the supplied completion history **before** allocating download slots. An explicit completed target receives status `completed`; `skipped_completed_codes` and an inspector caption show which known candidates were skipped. The existing final recommendation filter still excludes completed records. This saves discovery slots without interpreting grades, proving prerequisite satisfaction, or treating concurrent enrollment as completed coursework. Unknown code/ID relationships still need a download before the app knows their identity. Existing bundled courses can still be checked for source freshness or prerequisite evidence.

Without completions or a specific request, defaults remain CSC110/CSC144/CSC210 for AI/ML and exploration, and ECE201/ECE220/ECE274A for embedded interests. Controlled cases show that completing those three embedded foundations frees slots for ECE310/ECE311/ECE320A. A request for ECE373 can instead reserve a slot before the remaining source-order choices. No semester assignment or enrollment clearance follows from this ordering.

Profile-derived selections and completion filters remain request-local. Public caches contain source content, not questions, grades, or completion lists. Program cache keys already include the selected-section set, so a previous foundation-only cache cannot substitute for the expanded selection. Cache schemas and HTTP limits are unchanged. The five-course frozen corpus, review packets' reference inputs, and historical metrics remain unchanged; this expands the collection during supported live requests.

## Verification and limitations

The full suite passes **889 tests**, including **38 ECE-core cases** and **42 Streamlit interactions**. New cases cover exact provenance, six phrase routes, stages with unknown conditions, three career directions, completed/concurrent histories, shared budgets, changed identities, unavailable links, stale descriptions, 304 reuse, public-cache isolation, broad-topic rejection, and interface rendering. Older fixtures now use canonical identities for bound course codes; wrong identities are rejected before a record can be recommended, while a changed enrollment reference still leaves an otherwise valid course unreviewed.

The [dated evidence](evidence/ece_core_coverage_2026-11-05.json) retains both successful and failed public-source observations:

- A normal source-only AI/ML question about eigenvalues, circuit theory, and class hierarchies added ECE310, ECE320A, and ECE373 in that order. All eight academic checks passed. PyTorch also passed, while CS50 timed out and used a labeled bundled fallback; the overall CLI exit remains 1.
- A separate source-only embedded request with a controlled completed-foundation history timed out for the program page, ECE101, and ECE369A. ECE372A was unchanged. One bounded recheck under the same limits had the same outcome. Neither request added courses without verified program links. **Live completion routing is therefore not verified by those attempts**; its expected selection is established by controlled tests only.
- All eight local readiness checks passed in the production-only Python environment, including real loopback liveness and the offline app preview. This is local runtime verification, not public hosting or remote-source availability.

No credentials, embeddings, or generation requests were used. The source observations are not an uptime, speed, independent-review, or model-quality benchmark. Earlier resource failures remain historical evidence; these observations add no connectivity-fix claim.

Exercise the normal request in PowerShell with:

```powershell
.\.venv\Scripts\python.exe scripts/check_sources.py --career ai_ml --question "eigenvalues, circuit theory, and class hierarchies"
```

For completion filtering, select Embedded Systems in the app, record ECE201/ECE220/ECE274A as completed, and update the roadmap. Inspect the source checks and skipped-completion caption. Remote failures remain visible and can prevent discovery. Next work remains exact ECE prerequisite/edition evidence, broader independent review, and source/deployment reliability.
