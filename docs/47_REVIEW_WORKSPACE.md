# Human evidence-review workspace

Implemented November 7, 2026. A separate local Streamlit app lets reviewers read saved evidence, assign explicit relevance grades, add question notes, and download/resume a review. It exports the existing `ReviewForm` format for the existing offline scorer. The student app remains a separate entrypoint.

## Run locally

From the repository root, using the environment installed from `requirements.txt`:

```bash
python -m streamlit run reviewer_app.py --server.address 127.0.0.1 --server.port 8502 --browser.gatherUsageStats false
```

Open `http://127.0.0.1:8502`. No model credentials are needed. The default inputs are the immutable packet and catalog snapshot in `data/reviews/runtime_v1`: twelve assistant-authored development questions, 34 evidence chunks, and **408 blank ratings**. The app builds a fresh blank form; it does not load earlier labels or rankings.

To review another prepared packet, set `ECE_REVIEW_PACKET_DIR` to the directory containing its `packet.json` and `catalog_snapshot.json` before starting the app. For PowerShell:

```powershell
$env:ECE_REVIEW_PACKET_DIR = ".cache/review_next"
python -m streamlit run reviewer_app.py --server.address 127.0.0.1 --server.port 8502 --browser.gatherUsageStats false
```

Inputs must match their exact fingerprints, evidence text, source metadata and candidate sets. Use the existing `review_retrieval.py prepare` command to create a new directory for changed questions or data. This workspace loads saved text; it does not refresh sources or run embeddings, generation, ranking or scoring. Source links are optional references; judge the saved excerpt, as linked pages may have changed.

## Review workflow

1. Use an alias and choose the appropriate role. Project contributors should declare that role. A role is self-reported and does not authenticate independence.
2. Read the question and displayed evidence, in the packet's fixed shuffled order. No grade is preselected.
3. Choose 0 unrelated, 1 background, 2 useful support, or 3 direct evidence. Select **Save grade and next**. Zero is an explicit rating; an unchosen grade stays `null`.
4. Use Previous/Next evidence or the question selector to navigate. Notes belong to the question. Save before navigating or downloading; unsaved form changes are not part of the draft.
5. Download a review draft to keep progress between sessions. A separate session starts blank; upload the draft to resume it.
6. After every evidence chunk has a grade for every question, select **Prepare completed review**, then download the completed file. Required identity metadata and an aware completion timestamp are validated. Any saved grade/note or reviewer-detail edit invalidates a prepared export.

The grade counter reports completed ratings, not accuracy or participant count. Clearing a grade returns it to unfinished and updates the browser control explicitly. Saves are bound to the displayed question/evidence identity so a stale repeated click cannot silently copy a grade to the next excerpt. Draft upload validates duplicate JSON keys, the 2,000,000-byte limit, strict integer grades, packet identity, exact question/chunk membership, and completion metadata. A rejected upload preserves the current review.

All mutable drafts live in the current Streamlit session. Downloads are explicit; the app does not write grades to the repository or send them to another service. Keep downloaded reviews outside the immutable bundle, for example in `.cache/reviews`. Downloaded prepared files are snapshots: prepare again after changes. Saved evidence is rendered as literal text, and the workspace displays no retrieval scores, model answers or suggested labels.

## Score a completed review

Use the same saved catalog and packet that were reviewed:

```bash
python scripts/review_retrieval.py score --catalog-snapshot data/reviews/runtime_v1/catalog_snapshot.json --packet data/reviews/runtime_v1/packet.json --review .cache/reviews/completed_review.json --output .cache/reviews/completed_keyword_raw.json
```

Choose a new output path. Semantic/hybrid comparison still requires an explicitly prepared matching embedding snapshot; see [expanded review inputs](38_EXPANDED_REVIEW_COLLECTIONS.md). The review workspace itself never calculates a score. Partial drafts cannot be scored as completed reviews.

Reviewer identity, independence and question provenance remain unauthenticated. The prepared questions are development material, so independent ratings of them do not turn the experiment into a held-out study. This workflow measures relevance on a saved collection; it does not establish answer accuracy, eligibility, live-source freshness, or student usability. Actual independent judgments and a voluntary student pilot remain open.

## Verification

All **1,562 local tests** pass, including **23 new cases**: seventeen backend/CLI controls and six reviewer AppTest scenarios. There are 77 student-app and six reviewer-workspace Streamlit scenarios. New controls cover exact draft binding, duplicate/oversized uploads, zero-versus-unreviewed, stale/double saves, clearing, notes, navigation, completion timestamps, invalidating prepared exports, scorer compatibility, redacted errors and offline operation. Controlled all-zero test forms use `controlled_fixture`; they are not human evaluation results.

The local reviewer server returns HTTP 200 on its prefixed health endpoint and releases its listener after cleanup. The browser CLI adds a local-only mode:

```bash
python scripts/check_browser.py --reviewer --output output/reviewer-browser-first.json
```

This starts an isolated reviewer process with the immutable default packet and temporary downloads. It cannot target a supplied host. Six planned Chromium checks cover the blank form, explicit saves/notes, actual draft download, blocked incomplete completion, real resume in a separate session, and rejection of a foreign packet. CI verification will be recorded after the actual run.

[Dated evidence](evidence/review_workspace_2026-11-07.json) records the verification and unchanged frozen/review input hashes. No real reviewer judgments or new quality metric are added; all 408 saved template grades remain blank. Readiness remains estimated at approximately 90% app/70% submission until real evaluation and final materials are completed.
