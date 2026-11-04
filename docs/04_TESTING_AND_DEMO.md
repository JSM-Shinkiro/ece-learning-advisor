# Testing and Demo

## Core checks

| Check | Expected result |
| --- | --- |
| Vector/chunk alignment | Each vector maps to the intended evidence chunk and matches the manifest |
| Changed goal | Reviewed examples produce appropriate changes in retrieved evidence |
| Context use | The generator receives exactly the evidence shown in the inspector |
| Citation integrity | Unknown and out-of-context citations are rejected |
| Missing evidence | The answer identifies the gap rather than adding unsupported requirements |
| Academic rules | AND/OR, grades, incomplete histories, and co-requisites follow the three-state logic |
| Updated coursework | The roadmap and cached rule results update correctly |
| Provider failure | Source cards remain available with a clear degraded status |
| Index mismatch | Incompatible data/model configurations are detected |
| Fixture isolation | Synthetic data cannot silently enter a live demonstration |
| Saved profiles | A new session restores the correct user's profile |
| Jobs | Provider fields, original links, dates, and empty/error states are accurate |

Use unit tests for deterministic rules and a few integration tests for the full flow. Keep live-provider checks separate from mocked tests. Include a case where instruction-like text in a retrieved document cannot override the generation rules.

## Evaluation

Prepare 8–10 development cases, followed by approximately 20–30 separate evaluation cases if time allows. Include incoming students, mid-degree students, seniors, exact course queries, changed goals, completed prerequisites, incomplete histories, unsupported catalog versions, and out-of-scope requests.

Review expected relevant records and supported facts before scoring. Several learning choices may be reasonable.

Compare keyword, semantic, and hybrid retrieval on the same collection. Measure:

- Precision@5: relevant records in the first five divided by five, including when fewer are returned.
- Coverage of reviewed relevant records.
- Correct retrieval of an exact course code.
- Query embedding time and local ranking time.

Score unsupported requests separately for appropriate abstention.

For a small set of factual questions, compare the same generator with and without retrieved evidence. Keep the question, model, settings, and output budget matched. The baseline can answer from pretrained knowledge and should not be instructed to abstain simply because it has no supplied context.

Review factual claims as supported, unsupported, or unclear against the same source truth. Evaluate citation validity separately. A valid reference does not establish that a claim follows from it.

Use the trace to identify whether a failure came from source data, retrieval, rules, or generation. A synthetic context-update test can check evidence dependence, but belongs in tests rather than the official course collection.

## Timing and usability

Record cold/warm runs, model IDs, data version, collection size, hardware, cache state, and failures. Separate embedding, retrieval, generation, job search, and total request time.

Initial targets are under one second for cached local ranking/visualization and about ten seconds for a fresh explained roadmap under normal service conditions. Report measured results, sample counts, and ranges.

Ask 3–5 students to create a profile, find a next step, inspect its reason, change a goal, and find an opportunity. Record completion and points of confusion. Treat this as a small usability pilot.

## Midpoint video

| Time | Demonstration |
| --- | --- |
| 0:00–0:15 | Start the app and introduce the student's goal |
| 0:15–0:45 | Submit a real request and show recommendations, explanation, and sources |
| 0:45–1:10 | Open the retrieved context and embedding view |
| 1:10–1:35 | Change the goal or completed coursework and show the update |
| 1:35–1:50 | Show prerequisite uncertainty or an unsupported request |
| 1:50–2:00 | State measured timing and remaining final features |

## Report evidence

| Required section | Material to collect |
| --- | --- |
| Problem, persona, scenario | A concrete student question and walkthrough |
| Design goals G1–G4 | Latent-space view, similarity drill-down, real controls, measured response |
| Architecture and data flow | Indexing, retrieval, rules, context, generation, rendering |
| Integration status | Annotated screenshots and implemented/planned feature status |
| Compute and latency | Actual measurements and optimization choices |
| Roadblocks and roadmap | Observed issues, weekly tasks, and team assignments |

Use the instructor's editable midpoint template and bibliography. Capture figures from the running application. Sketches can explain the design but do not demonstrate integration.
