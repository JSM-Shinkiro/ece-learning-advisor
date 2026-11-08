# Final demo runbook

Prepared November 8, 2026. This is a rehearsal script, not a recording or an instructor-approved duration. Use the production entrypoint. Keep the original midproject video unchanged and create a separately named final recording.

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

Open `http://127.0.0.1:8501`. These settings disable catalog/resource checks and AI; explicit employer searches still require network access. Use a fictional profile. Select **Update my roadmap** before inspecting a result. `scripts/serve.py --check` with the same environment runs the startup preflight without listening.

The PowerShell credential values contain one space. The app strips credential whitespace, while the defined variable prevents `.env` fallback on older PowerShell versions that remove empty-valued variables. See [Microsoft's environment-variable documentation](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_Environment_Variables).

## 2. Proposed rehearsal blocks

Trim or extend these blocks after the final duration is known. Prepare the real-AI segment before recording; it may require a separate server session and restored fictional profile.

| Approximate time | Action | What to explain/show |
| --- | --- | --- |
| 0:00–0:20 | Introduce the incoming-student problem and current mode | ECE preparation suggestions, source links and explicit uncertainty |
| 0:20–1:00 | Keep Incoming / AI–Machine Learning / Getting started defaults; submit | **Start here** options and a course/resource's details; saved evidence is dated |
| 1:00–1:40 | Select ECE101 under **Currently taking (optional)** and submit; use **Mark completed** | Current study is excluded from next steps, then moves into completed work without an invented grade |
| 1:40–2:10 | Change direction to Embedded Systems and submit; search `ECE 372A` in **Courses & Resources** | Profile-driven update versus local collection browsing; source detail links |
| 2:10–3:30 | Use the prepared actual semantic/hybrid request; open **How this plan was made** | Actual PCA/query point, vector selection, cosine calculation, evidence, statements and trace |
| 3:30–4:15 | If network is available, explicitly search **Opportunities**, then check one displayed listing | Board scope, provider dates, loading feedback and source-bound detail; show actual empty/error state if returned |
| 4:15–4:40 | State the measured result and main limits | The paired offline inspector experiment; partial academic coverage and uncollected human/real-AI performance evaluation |

The preview segment supports profile/control and timing inspection. G1/G2's neural-vector demonstration needs an actual successful semantic/hybrid request. Label each segment's mode clearly.

## 3. Real-AI/vector segment

Configure a valid operator credential in the ignored local `.env` or a process environment before capture, keeping its value off screen. Stop the preview server. If using `.env`, remove the preview shell's empty Gemini/Google overrides and enable source checks before restarting:

```bash
unset GEMINI_API_KEY GOOGLE_API_KEY
export ECE_REFRESH_SOURCES=true
.venv/bin/python scripts/serve.py --address 127.0.0.1 --port 8501
```

For PowerShell, remove those two environment overrides with `Remove-Item Env:GEMINI_API_KEY, Env:GOOGLE_API_KEY -ErrorAction SilentlyContinue`, set `$env:ECE_REFRESH_SOURCES = "true"`, and use only the Windows Python launch command above, without reapplying its blank credential assignments. A new server session starts fresh; restore the fictional JSON profile if needed.

1. Open **AI and ranking options**, enable **Generate AI explanations**, choose **hybrid** or **semantic**, then submit a supported goal such as embedded programming.
2. Show the source plan while optional AI runs. Wait for the actual final result; retain any failure/fallback in the evidence record.
3. Confirm the trace's `retrieval_mode` is the chosen neural mode, actual model IDs are present, `generation_complete` is true and `generation_status` is `answered` before calling the segment a completed AI explanation.
4. Open the inspector and confirm a real vector view exists. Select a record, show the query/document components, dot product, norms and cosine. Explain that PCA is a projection and ranking uses full dimensions.
5. Download the actual request trace to a new evidence file and record the source/cache state. A warmed public embedding cache is acceptable when labeled as warm; it is not a cold-request measurement.

If the provider or network prevents that result, record the fallback honestly and keep the neural segment incomplete until it can be captured. Production runs are distinct from CI's controlled provider fixtures. The recording does not replace repeated final-release timing measurements.

## 4. Evidence to retain

Record the application Git revision, dependency/model versions, mode, data fingerprint, date/time with timezone, cache state, trace and observed failures. Capture fresh UI figures showing the roadmap, one uncertainty/source detail, the actual vector/cosine view, and an actual opportunity outcome. Use a profile with fictional history and retain only the necessary demonstration information.

Use **Saved profile → Download my profile** and **Restore a saved profile** to verify portability in a fresh browser session. The actual export/import browser flow is already checked in CI; still rehearse the visible demonstration. Keep draft notes, final figures and the final recording separately from the preserved midproject artifacts.

Before packaging, reconcile the final template/duration, check all links, rerun the relevant checks on the frozen revision and review [the evidence boundaries](EVIDENCE_MAP.md).
