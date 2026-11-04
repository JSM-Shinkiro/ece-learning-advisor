# Team Progress

Updated October 23, 2026, Arizona time.

## Current implementation

The refined prototype includes five real course summaries, two resources, a shorter profile form, a searchable course picker, three learning stages, completion actions, profile export/import, a Gemini RAG adapter, evidence inspection, and an Adzuna adapter. Still exploring shows both career directions. Course and resource cards explain the suggested learning connection.

**The starter RAG pipeline passed live integration checks on October 23.** Both supplied credentials produced real embeddings. Keyword, semantic, and hybrid requests generated answers with valid record and citation references. Changed goals, completed-course filtering, and a clear unsupported-topic case also passed. Use `gemini-embedding-2` and the tested `gemini-3.5-flash-lite` generator. Keys are not stored in the repository. Live Adzuna requests remain unverified.

An optional OpenRouter credential passed a free-model Hello World test with reported cost zero. Structured RAG experiments encountered a rate limit, an exhausted reasoning budget, and then an overly restrictive abstention. OpenRouter is not connected to the app; Gemini remains the working generator. Any future OpenRouter use is restricted to free models. See [free-model notes](12_OPENROUTER_FREE_MODELS.md).

Four ECE academic rules remain unknown because the course entries expose internal requirement IDs. One CSC120 condition is reviewed from the current catalog program requirements. Course descriptions and credits were checked against official sources. Remaining rules and supporting records need review.

Automatic source retrieval is a target requirement, not an implemented runtime feature. The app currently reads bundled records. The saved source files are development references. The intended runtime fetches official evidence as needed, with a temporary cache and no required permanent course database.

## Milestones

| Milestone | Owner | Status | Evidence / next step |
| --- | --- | --- | --- |
| M0: Setup and sources | To assign | Partial | Environment, records, and Gemini access verified. Review sample papers and confirm job-provider access |
| M1: Complete RAG interaction | To assign | Complete for starter collection | Live keyword, semantic, and hybrid RAG passed. Answer-quality evaluation and broader academic rules remain open |
| M2: Checkpoint interface | To assign | Partial | Hybrid retrieval, inspector, plots, profile files implemented. Complete browser demo and rule review |
| M3: Midpoint submission | Team | Open | Report, screenshots, narrated video |
| M4: Returning students | To assign | Partial | Portable files work. Hosted authentication/storage remain |
| M5: Opportunities | To assign | Partial | Adapter and interface implemented. Confirm credentials and results |
| M6: Coverage and updates | To assign | Partial | Five-source review importer works. Add runtime source retrieval, edition checks, and freshness/failure handling |
| M7: Final evaluation | Team | Open | Held-out cases, student pilot, presentation |

## Verification

- Clean installation from pinned dependencies succeeded.
- 80 automated tests passed, including 12 Streamlit interaction tests.
- Streamlit started successfully and returned an `ok` health response and its root page.
- The importer fetched and parsed all five official course entries.
- All five keyword smoke cases passed, covering beginners, experienced students, changed goals, and completed coursework.
- Provider behavior has both controlled tests and six live checks. The live index contains nine evidence chunks with 768 dimensions; generated answers passed reference validation.
- Manual review found one technical-word substitution in a keyword answer. Correct citation IDs alone do not establish factual support. See [live verification](11_GEMINI_LIVE_VERIFICATION.md).
- Regression cases cover failed grades, blocked-course stages, stale results, imported fields, server-key visibility, completion actions, career choices, unsupported queries, and AI abstentions.

See [prototype verification](07_PROTOTYPE_VERIFICATION.md) for commands, timing scope, and limitations.

## Next work session

1. Configure each teammate's local key using `.env.example`; the working defaults are tested.
2. Check real generated output in the browser and capture the narrated demonstration. Review explanations against their evidence, including technical terminology.
3. Resolve and review the four remaining ECE enrollment requirement references.
4. Review the six sample papers and their tools/videos.
5. Configure Adzuna and inspect actual opportunity results.
6. Assign owners and prepare the midpoint report/demo.

## Work log

```text
Date:
Contributors:
Tasks completed:
Files or commits:
Tests and live checks:
Measurements:
Open issues:
Next task and owner:
```

## Decisions

| Date | Decision |
| --- | --- |
| Oct 22 | Put the full RAG flow in the first working milestone |
| Oct 22 | Evaluate academic rules separately from generated explanations |
| Oct 22 | Begin with two reviewed directions and one job provider |
| Oct 22 | Keep opaque catalog requirements unknown until reviewed |
| Oct 22 | Use portable profile files before hosted accounts |
| Oct 22 | Use reported programming background and coursework when choosing foundations |
| Oct 22 | Keep learning stages separate from academic eligibility and preserve state through profile edits |
| Oct 22 | Retrieve source information automatically at runtime. Keep saved files as development references and prefer a temporary cache over a required course database |
| Oct 22 | Aim for source checks when a student submits a request. Any content database must also refresh automatically on a configurable schedule, with freshness and failed checks visible |
| Oct 23 | Use `gemini-3.5-flash-lite` as the tested default generator. Larger Flash requests hit high demand; retain model configuration overrides |
| Oct 23 | Use the supplied OpenRouter access only with free models and zero-price routing limits. Keep it as a development option until recommendation quality and reliability are verified |
