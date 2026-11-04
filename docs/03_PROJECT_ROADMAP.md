# Project Roadmap

Build one complete RAG interaction first, then expand coverage and the student workflow.

## Milestones

| ID | Target | Work | Completion check |
| --- | --- | --- | --- |
| M0 | Oct 22–23 | Repository, environment, model access, five verified courses, required sample readings | Source records are ready and provider access is known |
| M1 | By Oct 25 | Semantic retrieval, prerequisite checks, selected context, generation, citations | A real request produces a personalized explanation using retrieved evidence |
| M2 | Oct 26–28 | More reviewed records, hybrid retrieval, inspection view, export/import | Inputs visibly change results and the evidence is inspectable |
| M3 | Oct 29–Nov 1 | Measurements, report, screenshots, narrated demo, clean setup | Mid-project package is ready |
| M4 | Nov 2–8 | Instructor feedback, rule coverage, hosted pilot, saved profiles | A returning student reloads and updates the correct profile |
| M5 | Nov 9–15 | Live job search, filters, links, dates, empty/error states | Available Opportunities returns actual provider listings |
| M6 | Nov 16–22 | Automatic official-source retrieval, complementary resources, change tracking | Submitted requests check relevant sources. Any content database refreshes automatically. Source failures and freshness are visible |
| M7 | Nov 23–Dec 11 | Evaluation, student feedback, fixes, final presentation | Core workflow is tested and final deliverables are ready |

## First sprint: M0–M1

- [x] Establish the repository and local Python environment.
- [x] Verify one embedding request and one generation request.
- [ ] Read the six instructor sample papers and inspect their tools/videos.
- [ ] Prepare five real course records and the prerequisites needed for the example.
- [x] Create evidence chunks, vectors, and an index manifest.
- [x] Build a small profile form and semantic retrieval.
- [x] Implement prerequisite evaluation and context assembly. Resolve actual course conditions separately.
- [x] Generate an explanation and validate its source references.
- [ ] Show recommendations, citations, and the exact evidence used.
- [x] Test a changed career goal and an unsupported-information case using controlled providers and live checks.
- [x] Record the configuration and actual response time.
- [ ] Check job-provider access early, even though its full interface comes later.

If credentials are pending, work on records, academic rules, local tests, and the interface. Keep live integration checks open until they run successfully.

The first implementation is in place. Five source summaries, the profile UI, retrieval modes, citation checks, portable profiles, plots, and opportunity search adapters are implemented. Six live Gemini checks passed on October 23. The remaining unchecked items include Adzuna access, academic-rule review, and the browser demo. See [team progress](06_TEAM_PROGRESS.md) and [live verification](11_GEMINI_LIVE_VERIFICATION.md).

## Midpoint scope

Aim for approximately 20–30 reviewed course records and 8–12 resources, with complete prerequisite chains for the demonstration. Start smaller if necessary.

Add BM25/RRF comparison, a fixed embedding plot, and a similarity drill-down after the full RAG loop works. Keep unfinished features clearly identified.

**Deadline: November 1, 2026, at 11:59 PM MST.**

Each member submits P07_MidProject_FullName.zip with a 3–4 page technical report, repository link, and two-minute narrated demonstration. The main branch must run, with setup instructions and dependencies.

## Final build

The final workflow includes saved progress, two reviewed career directions, complementary resources, actual on-demand opportunities, and automatic academic-source retrieval. Start with one ECE source connector and the selected catalog edition. Saved exports and plans are development references, not the deployed app's required catalog. Use a temporary evidence cache and an in-memory index before adding a database.

After the first live RAG interaction, verify one runtime source-fetch path early. Complete discovery, freshness handling, and wider ECE coverage in M6. Check that clearing the cache allows the app to retrieve the evidence again without manually uploading files, and that a failed refresh produces a dated cached result or an explicit unavailable state. Verify that a new submitted request checks relevant sources and reuses unchanged evidence. If a content database is added, also verify its scheduled refresh without manual intervention.

Use Nov 23–29 for the held-out evaluation and a small student pilot. Use Nov 30–Dec 6 for fixes and deployment stability, with a feature freeze on Dec 4. Reserve Dec 7–11 for presentation, documentation, and reproducibility checks.

Final presentation and submission are December 11. Confirm any separate final instructions when issued.

## Scope control

Keep one Python app, one embedding provider, one generator, and one job provider. Prioritize correct sources, academic rules, and the complete RAG interaction over visual polish.

One optional reranker or graph-retrieval experiment can follow passing core tests. Graduate advising, full semester optimization, multimodal processing, and autonomous web research remain later work.

Assign milestone owners in [06_TEAM_PROGRESS.md](06_TEAM_PROGRESS.md). Record completed work, test results, decisions, and the next task there.
