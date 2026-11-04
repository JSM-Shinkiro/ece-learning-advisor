# Prototype Refinement

Implemented from the October 22 Astra review. The original Streamlit app, dark theme, two career directions, RAG pipeline, and job provider remain the project scope.

## Completed

- A shorter profile form, searchable course picker, optional details, and collapsed saved-profile controls.
- Start here, Build toward, and Later goals for courses and resources.
- A bridge course in each chosen direction and both advanced goals for Still exploring.
- Compact cards with suggested learning connections, first resource activities, source links, and expandable details.
- Mark completed actions, visible completed coursework, and change notices.
- Failed-grade rejection, preserved imported fields, and consistent profile/roadmap/job state after updates and restore.
- Server credentials removed from UI defaults. Session keys/model overrides require explicit local development mode.
- Clarification for clear vocabulary nonmatches before adding default career terms. This is a limited coverage guard, not semantic intent classification.
- Distinct handling of AI abstentions, failures, and successful recommendations.
- Subsecond timing displayed in milliseconds inside the inspector.
- A real CSC120 prerequisite condition reviewed from the current catalog program requirements. Four ECE rules remain unresolved.
- An opt-in live-verification script for three retrieval modes and optional job search.

## Academic rule evidence

The [current Computer Science program requirements](https://catalog.arizona.edu/programs/COSCBS/program-requirements-a1nCj), foundation section R1299/L40, specify a grade threshold for one of four introductory courses before CSC120. The application stores this as an OR rule. Satisfying one alternative does not require loading every alternative's full course description.

The direct course entry still exposes an internal reference. Department guidance differs on the alternatives, so the source note calls out advisor confirmation for unusual substitutions. No ECE rule was inferred from a course number or a historical syllabus.

The learning stages and first activities are team suggestions. They are stored separately from academic rules and included in the model context with that label.

## Validation

The automated checks cover both backend policy and Streamlit interactions, including the review's failing scenarios. Controlled provider data is confined to tests. See the verification file for the current result and commands.

Browser screenshot review remains pending because the Chromium download in this environment returned an invalid archive. Wide and narrow layouts still need a visual check on a normal browser.

## Still pending

- Real Gemini requests, account-specific model availability, and human review of explanation support.
- Real Adzuna results and a live job demo.
- Four unresolved ECE enrollment rules and enough reviewed supporting records for complete demonstration paths.
- Source publication dates where available, broader resource refresh coverage, and a returning-student pilot.
- Instructor sample-paper reviews, report screenshots, and narrated demonstration.

At the October 22 refinement checkpoint, live checks were pending credentials. Live Gemini checks subsequently passed on October 23; see [live verification](11_GEMINI_LIVE_VERIFICATION.md). Run `python scripts/verify_live.py` after configuring a local key. Use `--jobs` once Adzuna is configured. Saved answers still require manual comparison with their cited sources.
