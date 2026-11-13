# Midproject feedback response

Team P07 · November 12, 2026 MST · ECE Learning Advisor

The submission review asks for a visual introduction, a self-guided path through Bloom’s Taxonomy, access to visualization code and a coordinated final recording. The learning path starts on the app’s landing page and leads to the advisor.

| Feedback | Implementation |
| --- | --- |
| Teach the domain before opening the interface | Beginner explains AI and machine learning, embedded systems, example applications, and who benefits. Short explanations introduce retrieval, vectors and prerequisites. A question checks whether the learner can distinguish relevance from course preparation. |
| Add images, icons, a flowchart and a roadmap | The landing page includes an electronics lab illustration, stage icons, a four-step question-to-evidence flowchart and a three-stage roadmap. Intermediate includes a second illustration and a live plot. Advisor cards place explanations and detailed citations behind a labeled control. |
| Remember and understand | Identify the evidence needed to check preparation and explain why the advisor ranks sources. |
| Apply and analyze | Run a sensor, image-classification or data-structures preset. Switch keyword, topic cosine and hybrid ranking, then compare the top records and inspect their source excerpts. |
| Evaluate and create | Write a variation, choose expected useful records, compare ranks against a preset with the same method, and save an evidence-based explanation. Export the comparison and observation as JSON. |
| Inspect the visualization code | The lesson developer view exposes the actual topic counts, score table, PCA and plotting functions. The advisor inspector includes the ranking and PCA source. |
| Prepare a private, coordinated final recording | The runbook assigns one segment to each of the three team members and specifies matching handoffs, app-only capture, voice narration, and removal of names, faces and Zoom from the export. Recording, editing and review remain open. |

The lesson uses seven saved course and resource overviews. Four visible counts of distinct topic terms support a reproducible cosine and PCA demonstration. The shared retrieval implementation supplies BM25, cosine and reciprocal rank fusion. In the Advanced example, ECE425 moves from sixth to second with hybrid ranking when the learner changes the sensor question to image classification. That changes the learner-selected top-three count from 0 of 1 to 1 of 1. The Advisor exposes optional Gemini embeddings and source-linked explanations for the full student workflow.

The app can open each lesson directly through its navigation. Choosing **Advisor** opens the profile, roadmap, collection and opportunities. The exercise runs locally using the saved overviews, and the developer panel opens on demand.

The two illustrations are bundled WebP images generated with ImageGen. The flowchart uses responsive HTML and CSS. The ranking bars and scatter plot use the calculated results. [Illustration prompts and file hashes](evidence/midproject_feedback_2026-11-12.json)

The stage mapping follows the University of Arkansas description of remembering, understanding, applying, analyzing, evaluating and creating. [Bloom’s Taxonomy](https://tips.uark.edu/using-blooms-taxonomy/)

Linux and Windows each passed 1,745 tests and nine production readiness checks. Chromium passed 32 gates, including the three lesson checks, a 390-pixel landing viewport and a real JSON download. The first run’s Advanced submit timeout and the passing follow-up are retained in the verification record. [Passing CI run](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/43361506460) · [Verification record](evidence/midproject_feedback_2026-11-12.json)

This implementation checkpoint estimated **90% for the app and 70% for the complete submission**. The subsequent audit revises the assessment after examining broader lesson behavior and the final learning goals. [Current audit](58_FINAL_VERSION_AUDIT.md) · [Final readiness](FINAL_READINESS.md) · [Recording runbook](final/DEMO_RUNBOOK.md)
