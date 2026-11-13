# ECE Learning Advisor — App Summary

Team P07 · ECE 425/525 · Updated November 13, 2026

Based on verified application revision `07cf4b59693b16dbe6835d6639123261e637860f` and the November 13 audit. [Final readiness](FINAL_READINESS.md)

## Purpose

ECE Learning Advisor helps prospective and current University of Arizona ECE students connect their interests and recorded coursework with a practical learning path. Supported directions are AI/machine learning, embedded systems, and exploring both. Suggestions are grouped into **Start here**, **Build toward**, and **Later goals**, with source links and suggested first activities. The published undergraduate ECE directory also supports course exploration; unmapped entries appear under **Explore requested courses**, without an inferred preparation sequence.

The app opens at **Beginner**, with domain explanations, illustrations, a flowchart and a learning roadmap. **Intermediate** compares ranking methods for a preset. **Advanced** accepts a custom question and expected records, compares ranks and saves an observation. These lessons use seven saved descriptions and four visible topic counts. **Advisor** opens the personal workflow and optional pretrained-embedding inspection. The audit identifies remaining continuity and custom-question issues in the lessons. [Audit findings](58_FINAL_VERSION_AUDIT.md)

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
2. **Resolve explicitly requested catalog courses and check topic coverage.** Up to three published ECE entries can join the current request without changing the default retrieval corpus. Completed/current courses and different editions are excluded from new additions. Unmapped entries retain unknown rules and unreviewed preparation/career connections. Other requests outside the supported collection receive a clarification.
3. **Check selected official evidence.** In the AI-enabled UI, source/model work runs in a bounded background job while the page remains interactive. The app selects relevant configured catalog/program/resource sources, validates identity and edition, and records freshness. Successfully checked public pages may be reused for up to five minutes without changing their check times; **Check sources again** bypasses that reuse for the submitted profile. Downloads and course discovery are bounded. Failed or omitted checks keep labeled saved evidence; missing academic interpretations remain unknown.
4. **Retrieve relevant evidence.** Keyword search uses BM25. With AI configured and enabled, semantic search compares Gemini embeddings with cosine similarity. Hybrid retrieval combines keyword and semantic rankings using reciprocal rank fusion. The vector search is implemented with NumPy rather than a database service.
5. **Build the learning context.** The app filters completed/current courses out of next-step suggestions, checks recorded preparation against reviewed rules, and selects a bounded set of courses, resources and supporting evidence. Current enrollment counts as a prerequisite only where an explicit reviewed concurrent condition permits it.
6. **Optionally prepare AI explanations.** A usable keyword-based source plan appears before AI finishes. Gemini selects from application-owned, source-bound statements. The app validates statement ownership, wording and citations before displaying explanations. The AI phase has a shared default 45-second cooperative budget after source checks; failures/timeouts preserve the available source roadmap.
7. **Display and update the plan.** Only the current request for the current profile can apply its result; newer submissions invalidate older work. **Keep source plan** stops accepting the pending AI output. The student sees preparation stages, first activities, source links and warnings. Marking a course completed updates its status without inventing a grade. Profiles can be exported/restored as JSON.

Preview mode works without model credentials using keyword retrieval and saved/refreshed sources. AI requests use hosted pretrained models; the project does not train its own language model. When enabled, the submitted profile and selected evidence are sent to Gemini for the explanation workflow.

## Other app functions

| Function | What it does |
| --- | --- |
| Courses & Resources | Search the focused advisor collection, or browse all 78 published undergraduate ECE entries with level filters, exact code search and 15-entry local pagination; open source details on demand and explicitly explore a course in the roadmap |
| Opportunities | Explicitly search public employer boards for Samsara, Nuro and Anduril, with direction/title/location filters, paging, source status and listing-level detail progress/checks that remain bound to the current search/page |
| Inspector | On opening, show retrieval rankings, full-dimensional cosine calculations, PCA, source checks, cache status, timings and a trace download; its controls update independently |
| Live request feedback | Show the actual work attempted and an expandable stage history; record sequential server phase durations |
| Human review workspace | Separate local app for reading saved evidence, entering explicit relevance grades/notes, downloading/resuming drafts, and exporting completed forms for the offline scorer |

Opportunity matching is based on configured title filters and public listings. Optional Adzuna/OpenRouter work is outside the verified core described here. The reviewer workspace does not run AI grading or display retrieval scores; reviewer roles and question provenance remain self-reported/unverified.

## Current implementation and limits

- **Collection:** default advisor: 20 courses (15 ECE/five CSC), eight resources, two career records and 34 chunks. Separate catalog: all 78 undergraduate ECE entries in the saved official 2026–2027 published list, including variable credits. Sixty-three additional ECE descriptions are reachable on request. The list follows its official effective-date setting of January 13, 2027; availability in a current semester is not established. Graduate courses and complete supporting-subject inventory remain outside this directory.
- **Academic conditions:** four exact CS conditions have reviewed interpretations; all ECE conditions and CSC372 remain unknown. Learning stages describe preparation rather than guaranteed enrollment or semester placement.
- **Technology:** Python, Streamlit, Pydantic validation, NumPy retrieval/vector math, native ranking bars and Plotly vector charts, and optional Gemini integration. Default configured models are `gemini-embedding-2` and `gemini-3.5-flash-lite`, with 768-dimensional embeddings; these settings are configurable.
- **Verification:** The November 12 run passed 1,745 tests and nine runtime checks on Linux and Windows, plus ten student preview, sixteen lesson/controlled AI/browsing and six reviewer-workspace checks. The later audit adds seven groups of offline workflow observations. [CI evidence](evidence/midproject_feedback_2026-11-12.json) · [Audit evidence](evidence/final_version_audit_2026-11-13.json)
- **Preview performance:** the native inspector opens at a median 686.7 ms versus 1,608.4 ms for the fixed baseline, with five sessions per version using the same v2 collector/runner. Native reopening takes 307.8 ms. That comparison recorded feedback/roadmap-control medians of 221.2/453.4 ms. These are offline DOM observations; live-AI/source and hosted/mobile timing remain separate. See [lightweight inspection](52_LIGHTWEIGHT_INSPECTOR.md).
- **Evaluation:** the prepared review packet has twelve development questions, 34 chunks and 408 blank grades. No genuine independent judgments or student-pilot results have been collected in the saved packet.
- **Submission:** Current planning estimates are approximately 85% for the app and 65% for the complete submission. Lesson continuity, the neural teaching connection, focused ECE prerequisite evidence and fresh-source waiting remain application gaps. Evaluation sessions, final figures, report formatting, slides, recording and packaging remain open. [Current audit](58_FINAL_VERSION_AUDIT.md) · [Final workspace](final/README.md)

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
