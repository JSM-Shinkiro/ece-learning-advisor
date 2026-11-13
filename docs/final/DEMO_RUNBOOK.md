# Final demo runbook

Updated November 13, 2026. Rehearse the three segments with the production entrypoint. Agree on the final duration using the course instructions and export a separate final recording.

## 1. Reproducible preview setup

Install the pinned dependencies from the repository README. From the repository root, start a local preview using saved evidence with AI disabled. The blank credential overrides below also prevent an existing local `.env` from enabling a model during this segment.

Linux/macOS Bash:

```bash
GEMINI_API_KEY= GOOGLE_API_KEY= OPENROUTER_API_KEY= ADZUNA_APP_ID= ADZUNA_APP_KEY= \
ECE_REFRESH_SOURCES=false ECE_DEVELOPMENT_MODE=false \
.venv/bin/python scripts/serve.py --address 127.0.0.1 --port 8501
```

Windows PowerShell:

```powershell
$env:GEMINI_API_KEY = " "
$env:GOOGLE_API_KEY = " "
$env:OPENROUTER_API_KEY = " "
$env:ADZUNA_APP_ID = " "
$env:ADZUNA_APP_KEY = " "
$env:ECE_REFRESH_SOURCES = "false"
$env:ECE_DEVELOPMENT_MODE = "false"
.\.venv\Scripts\python.exe scripts/serve.py --address 127.0.0.1 --port 8501
```

Open `http://127.0.0.1:8501`. These settings disable catalog/resource checks and AI; explicit employer searches still require network access. Use a fictional profile. The app opens at **Beginner**. Choose **Advisor** and select **Update my roadmap** to inspect an advisor result. `scripts/serve.py --check` with the same environment runs the startup preflight without listening.

The PowerShell credential values contain one space. The app strips credential whitespace, while the defined variable prevents `.env` fallback on older PowerShell versions that remove empty-valued variables. See [Microsoft's environment-variable documentation](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_Environment_Variables).

## 2. Three member recording plan

Each team member prepares, narrates and demonstrates one segment. Share the final app revision and agree on a common capture size, zoom and audio level. Record separate screen clips and join them in this order.

| Clip | On-screen action | Narration and handoff |
| --- | --- | --- |
| `01_beginner.mp4` | Show the landing photo, two ECE directions, roadmap and question-to-evidence flow. Answer the preparation question. End with **Try a preset experiment** in view. | “ECE combines hardware, software and data. The advisor helps us find learning evidence for a goal. Now let’s see what changes when we rank that evidence differently.” |
| `02_intermediate.mp4` | Open **Intermediate** with **Program a sensor** selected. Change **Keyword** to **Topic cosine**. Open **Inspect evidence** to show the topic counts and cosine for a record. Open **Developer view · visualization code** and end with **Create your variation** in view. | “Keyword matching and topic cosine can order the same records differently. The cosine calculation uses four counts. The developer view shows how the app projects them onto a plot. Carry this setup into Advanced and try a different question.” |
| `03_advanced.mp4` | Select **Create your variation**. Keep the inherited sensor preset and **Topic cosine**. Enter the image-classification question, select **ECE425** as expected evidence, and compare. Choose **ECE425** under **Record to explain**, select **Entered the ranking**, inspect its evidence and save an explanation. Select **Use this question in Advisor** and continue with the neural segment below. | “ECE425 enters the first three results for this question. Its description covers neural network methods. I’ll take the same question into the Advisor and compare the lesson counts with its neural embeddings.” |

Use the question “How do I train a neural network for image classification in Python?” for the shared Advanced example. Record the actual result visible on the final revision.

### Capture and edit

- Record the app content area and each member’s narration. Close Zoom and unrelated tabs, turn off the webcam and hide browser chrome, desktop notifications and account overlays.
- Keep faces and names out of the visible frames, titles, captions and narration. Identify the project as **ECE Learning Advisor · Team P07**.
- Stage the incoming screen to match the outgoing clip before recording. Leave a short silent pause at each handoff so the editor can cut on the visible control.
- Preview the stitched video from start to finish. Check that each member demonstrates their part, transitions preserve context, audio stays even and the final export contains only the intended app content.

## 3. Real-AI/vector segment

Configure a valid operator credential in the ignored local `.env` or a process environment before capture, keeping its value off screen. Stop the preview server. If using `.env`, remove the preview shell's empty Gemini/Google overrides and enable source checks before restarting:

```bash
unset GEMINI_API_KEY GOOGLE_API_KEY
export ECE_REFRESH_SOURCES=true
.venv/bin/python scripts/serve.py --address 127.0.0.1 --port 8501
```

For PowerShell, remove those two environment overrides with `Remove-Item Env:GEMINI_API_KEY, Env:GOOGLE_API_KEY -ErrorAction SilentlyContinue`, set `$env:ECE_REFRESH_SOURCES = "true"`, and use the Windows Python launch command above. Restore the fictional JSON profile if the new session needs it.

### One-request rehearsal

With `GEMINI_API_KEY` configured locally, run the verifier from the repository root. On Windows, use `.\.venv\Scripts\python.exe` in place of `.venv/bin/python`.

```bash
.venv/bin/python scripts/verify_runtime.py --live-models --demo --with-sources --output output/final-demo-live.json
```

Use a new output path for every attempt. The verifier uses the demo question, a fictional profile, and Hybrid. It checks ECE425’s lesson rank, the two interim plans, the selected answer and citations, the ECE425 source check, and the seven-record comparison. It can make up to 64 document-embedding calls for a cold cache, one query-embedding call, and one generation call. Other source failures stay in the trace. Remove `--with-sources` to rehearse with saved evidence. That run uses the dated sources and checks one interim plan. A report from either command supports the operator’s rehearsal. The browser walkthrough below is the recorded demo.

### Screen walkthrough

1. Recreate the Advanced comparison in the configured session and select **Use this question in Advisor**. Use **AI / Machine Learning** and **Comfortable with programming** with empty coursework, interests, and experience. Confirm the question is present, open **AI and ranking options**, enable **Generate AI explanations**, choose **hybrid**, and select **Update my roadmap**.
2. Show the dated saved-data roadmap while official sources are checked. Then show the updated source plan while AI runs. Wait for the final result and record any fallback you observe.
3. Confirm the trace's `retrieval_mode` is the chosen neural mode, actual model IDs are present, `generation_complete` is true and `generation_status` is `answered` before calling the segment a completed AI explanation.
4. Open **How this plan was made** and **Compare lesson and neural embeddings**. Show how the two cosine rankings compare for the seven common overviews and the displayed Advisor search text. It includes the carried question and profile terms.
5. Select a record in the vector view and show the components, dot product, norms and cosine. Explain that PCA projects the vectors to two axes and that scoring uses the full vectors.
6. Download the embedding comparison and the request trace. Record the source/cache state. Label a warmed public embedding cache as warm. Use the fictional profile for shared exports because the comparison includes the submitted question and Advisor search text.
7. Open **Why this fits and sources** for ECE425. Point out its department reference and **Open class search**. Explain that the term and class section determine which requirements to confirm. If showing ECE101, show why the department page and advised plan are listed separately.

If the provider or network prevents that result, save the failed attempt and rehearse the saved-data branch. Fix the open issue before capturing the neural segment. The recording and repeated final-release timing measurements are separate tasks.

## 4. Evidence to retain

Record the application Git revision, dependency/model versions, mode, data fingerprint, date/time with timezone, cache state, trace and observed failures. Capture fresh UI figures showing the roadmap, one uncertainty/source detail, the actual vector/cosine view, and an actual opportunity outcome. Use a profile with fictional history and retain only the necessary demonstration information.

Use **Saved profile → Download my profile** and **Restore a saved profile** to verify portability in a fresh browser session. The actual export/import browser flow is already checked in CI; still rehearse the visible demonstration. Keep draft notes, final figures and the final recording separately from the preserved midproject artifacts.

Before packaging, reconcile the final template/duration, check all links, rerun the relevant checks on the frozen revision and review [the evidence boundaries](EVIDENCE_MAP.md).
