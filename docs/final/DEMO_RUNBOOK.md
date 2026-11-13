# Final demo runbook

Updated November 12, 2026. Rehearse the three segments with the production entrypoint. Agree on the final duration using the course instructions and export a separate final recording.

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
| `02_intermediate.mp4` | Open **Intermediate** with **Program a sensor** selected. Change **Keyword** to **Topic cosine**. Point to the top-three records and open **Developer view · visualization code**. End with **Create your variation** in view. | “Keyword matching and topic similarity can order the same records differently. The plot uses four topic counts, and the developer view shows the actual projection code. Next we’ll choose our own question and test an expectation.” |
| `03_advanced.mp4` | Open **Advanced** with the sensor preset. Enter the image-classification question, choose **ECE425**, compare, and explain the change in the top three. Save the observation. Open **Advisor** and show the prepared neural-mode inspection if available. | “I expect deep learning evidence to help with image classification. ECE425 enters the first three results for my variation. Its description supports that choice. Here is the full advisor’s source and vector inspection.” |

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

For PowerShell, remove those two environment overrides with `Remove-Item Env:GEMINI_API_KEY, Env:GOOGLE_API_KEY -ErrorAction SilentlyContinue`, set `$env:ECE_REFRESH_SOURCES = "true"`, and use only the Windows Python launch command above, without reapplying its blank credential assignments. A new server session starts fresh; restore the fictional JSON profile if needed.

1. Choose **Advisor**, open **AI and ranking options**, enable **Generate AI explanations**, choose **hybrid** or **semantic**, then submit a supported goal such as embedded programming.
2. Show the source plan while optional AI runs. Wait for the actual final result; retain any failure/fallback in the evidence record.
3. Confirm the trace's `retrieval_mode` is the chosen neural mode, actual model IDs are present, `generation_complete` is true and `generation_status` is `answered` before calling the segment a completed AI explanation.
4. Open the inspector and confirm a real vector view exists. Select a record, show the query/document components, dot product, norms and cosine. Explain that PCA is a projection and ranking uses full dimensions.
5. Download the actual request trace to a new evidence file and record the source/cache state. A warmed public embedding cache is acceptable when labeled as warm; it is not a cold-request measurement.

If the provider or network prevents that result, record the fallback honestly and keep the neural segment incomplete until it can be captured. Production runs are distinct from CI's controlled provider fixtures. The recording does not replace repeated final-release timing measurements.

## 4. Evidence to retain

Record the application Git revision, dependency/model versions, mode, data fingerprint, date/time with timezone, cache state, trace and observed failures. Capture fresh UI figures showing the roadmap, one uncertainty/source detail, the actual vector/cosine view, and an actual opportunity outcome. Use a profile with fictional history and retain only the necessary demonstration information.

Use **Saved profile → Download my profile** and **Restore a saved profile** to verify portability in a fresh browser session. The actual export/import browser flow is already checked in CI; still rehearse the visible demonstration. Keep draft notes, final figures and the final recording separately from the preserved midproject artifacts.

Before packaging, reconcile the final template/duration, check all links, rerun the relevant checks on the frozen revision and review [the evidence boundaries](EVIDENCE_MAP.md).
