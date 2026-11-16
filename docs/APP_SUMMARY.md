# ECE Learning Advisor — App Summary

Team P07 · ECE 425/525 · Updated November 15, 2026

Verified application revision `034baef173dd783697da72542ce3aa28bdfcf2c7`. [Final readiness](FINAL_READINESS.md)

## Purpose

ECE Learning Advisor helps University of Arizona ECE students connect their interests and coursework to a learning path. The Advisor offers eight career directions, including Photonics & Electro-Optics, Power & Energy Systems, and Biomedical Instrumentation & Sensors. **Still exploring** lets learners choose a direction or ask a question. Each direction has a career panel with selectable specializations, with Edge AI available in both AI / Machine Learning and Embedded Systems. Roadmaps group suggestions into **Start here**, **Build toward**, and **Later goals**. [Career directions](59_CAREER_DIRECTIONS.md)

The app opens at **Beginner**, with illustrations, a flowchart and a worked topic-count example. **Intermediate** compares ranking methods and exposes source excerpts and cosine calculations. **Advanced** carries the preset and method forward, compares a custom question, and checks an observed rank change. **Use this question in Advisor** fills the evaluated question into the profile form. In a semantic or hybrid request, the inspector compares topic counts with provider embeddings on the same seven records.

## Are we using a database?

The app uses a **file-based knowledge base and caches**, rather than a SQL/NoSQL database engine or a separate vector database service. Semantic search uses a small vector matrix in memory, backed by compressed NumPy files on the server.

| Data | Current storage | Persistence |
| --- | --- | --- |
| Reviewed courses, resources, career mappings, source metadata | Versioned JSON files under `data/reviewed/` | Saved with the repository |
| Published undergraduate ECE inventory | Versioned snapshot under `data/catalog/` | Saved with the repository; explicit maintainer refresh/restart |
| Downloaded public-source evidence and freshness metadata | JSON cache files under the configured source-cache directory | Depends on keeping the server's cache storage |
| Recent successful source-check identities | Bounded server-process memory; no personal profiles | Up to five minutes; fresh checks required after restart |
| Public document embeddings and index manifests | Compressed NumPy `.npz` files under the embedding-cache directory | Reused across requests while the cache remains available |
| Student profile, current/completed coursework, active roadmap, opportunity search state | Streamlit session state in server memory | Current session; not automatically stored in an account |
| Portable profiles and reviewer drafts/completed forms | Explicit JSON downloads and uploads | Kept by the person who downloads the file |
| Query embeddings and generated explanations | Request/session memory | Not written to the shared document-embedding cache |

There are no login accounts or database-backed profile/history records. Session data can be lost when a session ends or the server restarts. Download/upload provides the current way to carry a profile or review between sessions. Public caches persist only as long as their underlying storage is retained.

## How a roadmap request works

1. **Collect and validate the profile.** The student enters their standing, catalog year, direction, interests, experience, completed/current courses, optional grades, and learning question. Changes are applied on submission. Profile validation rejects conflicting or malformed course histories.
2. **Select career evidence and resolve catalog requests.** An exploratory question can match one direction. A question or specialization button can select a team-authored study route in that direction. The route brings in its relevant courses and practice material. Up to three explicitly requested ECE directory entries can join a request. Unmapped entries retain unreviewed preparation and enrollment status.
3. **Show a first plan and check selected official evidence.** A background job publishes the dated roadmap, then checks relevant catalog, program and resource sources. The interface remains usable. Successful checks can be reused for five minutes with their original timestamps. **Check sources again** bypasses reuse. Failed and omitted checks retain labeled saved evidence. Missing academic interpretations remain unknown.
4. **Retrieve relevant evidence.** Keyword search uses BM25. With AI configured and enabled, semantic search compares Gemini embeddings with cosine similarity. Hybrid retrieval combines keyword and semantic rankings using reciprocal rank fusion. The vector search is implemented with NumPy rather than a database service.
5. **Build the learning context.** The app filters completed/current courses out of next-step suggestions, checks recorded preparation against reviewed rules, and selects a bounded set of courses, resources and supporting evidence. Current enrollment counts as a prerequisite only where an explicit reviewed concurrent condition permits it.
6. **Optionally prepare AI explanations.** The keyword plan from the available source checks appears while Gemini prepares explanations. Gemini selects from application-owned statements. The app checks statement ownership, wording and citations. The AI phase has a shared default 45-second budget after source checks. Failures retain the source plan.
7. **Apply the current result.** New submissions supersede earlier requests. **Keep saved-data plan** rejects further updates during source checks. **Keep source plan** does the same while AI runs. The student can mark a course completed, inspect the evidence and export or restore a JSON profile.

If all four background slots are busy, the request uses dated saved evidence. Source panels remember their open or closed preference across plan updates. [Roadmap verification](evidence/saved_data_roadmap_2026-11-13.json)

Preview mode works without model credentials using keyword retrieval and saved/refreshed sources. AI requests use hosted pretrained models; the project does not train its own language model. When enabled, the submitted profile and selected evidence are sent to Gemini for the explanation workflow.

## Other app functions

| Function | What it does |
| --- | --- |
| Courses & Resources | Search the focused collection or browse 78 published ECE entries. See snapshot dates, open a class search, explore a course in the roadmap, or check the Mathematics minor overlap card. |
| Opportunities | Explicitly search public employer boards for Samsara, Nuro and Anduril, with direction/title/location filters, paging, source status and listing-level detail progress/checks that remain bound to the current search/page |
| Inspector | On opening, show retrieval rankings, full-dimensional cosine calculations, PCA, source checks, cache status, timings and a trace download; its controls update independently |
| Live request feedback | Show the actual work attempted and an expandable stage history; record sequential server phase durations |
| Human review workspace | Separate local app for reading saved evidence, entering explicit relevance grades/notes, downloading/resuming drafts, and exporting completed forms for the offline scorer |

Opportunity matching is based on configured title filters and public listings. Optional Adzuna/OpenRouter work is outside the verified core described here. The reviewer workspace does not run AI grading or display retrieval scores; reviewer roles and question provenance remain self-reported/unverified.

## Current implementation and limits

- **Collection** · 47 courses, 16 resources and eight career directions, including 32 ECE courses in the curated collection. The saved 34-chunk core supports general AI/ML and Embedded Systems queries and the archived evaluation. The separate 78-entry undergraduate ECE directory follows the official 2026–27 list's effective-date setting of January 13, 2027. Check the class search for section availability.
- **Academic conditions** · Four exact CS conditions have reviewed interpretations. ECE conditions and CSC372 remain unverified. ECE101, ECE369A, ECE372A and ECE425 show dated enrollment references. ECE101 shows the department and the 2026–27 advised plan separately because their listed math conditions differ. [Enrollment source review](evidence/focused_ece_enrollment_2026-11-13.json)
- **Technology:** Python, Streamlit, Pydantic validation, NumPy retrieval/vector math, native ranking bars and Plotly vector charts, and optional Gemini integration. Default configured models are `gemini-embedding-2` and `gemini-3.5-flash-lite`, with 768-dimensional embeddings; these settings are configurable.
- **Verification** · The latest run passed 1,803 tests and nine startup checks per OS and 39 Chromium checks. Source-only requests refreshed all 16 added course records. Chromium switched the Photonics specialization and opened the BME416 enrollment details at phone width. [Verification evidence](evidence/career_specializations_2026-11-14.json) · [Passing CI](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/43688855340)
- **Preview performance:** the native inspector opens at a median 686.7 ms versus 1,608.4 ms for the fixed baseline, with five sessions per version using the same v2 collector/runner. Native reopening takes 307.8 ms. That comparison recorded feedback/roadmap-control medians of 221.2/453.4 ms. These are offline DOM observations; live-AI/source and hosted/mobile timing remain separate. See [lightweight inspection](52_LIGHTWEIGHT_INSPECTOR.md).
- **Evaluation:** the prepared review packet has twelve development questions, 34 chunks and 408 blank grades. No genuine independent judgments or student-pilot results have been collected in the saved packet.
- **Submission** · Planning estimates are approximately 95% for the app and 72% for the complete submission. The one-request live Gemini and catalog rehearsal passed. Remaining work includes live neural and opportunity captures, independent evaluation, a student pilot, slides, report formatting, recording and packaging. [Final readiness](FINAL_READINESS.md) · [Final workspace](final/README.md)

## Code map

| Area | Main files |
| --- | --- |
| Student interface, browsing and profile changes | `app.py`, `src/collection_ui.py`, `src/opportunity_ui.py`, `src/session.py`, `src/profiles.py` |
| Self-guided lessons and local experiments | `src/learning_ui.py`, `src/learning_lab.py` |
| Request orchestration and progress | `src/controller.py`, `src/progress.py`, `src/advisor_jobs.py` |
| Source loading, published directory and live checks | `src/catalog.py`, `src/course_directory.py`, `src/directory_ui.py`, `scripts/sync_course_directory.py`, `src/sources.py`, source/discovery modules |
| Retrieval, rules and grounded explanations | `src/retrieval.py`, `src/rules.py`, `src/service.py`, `src/grounding.py` |
| Ranking and vector inspection | `src/inspector.py`, `src/inspection_views.py`, `src/retrieval.py` |
| Provider access and embedding cache | `src/providers.py` |
| Reviewer interface and input validation | `reviewer_app.py`, `src/review_workspace.py`, `src/review.py` |

Development repository: [JSM-Shinkiro/ece-learning-advisor](https://github.com/JSM-Shinkiro/ece-learning-advisor).
