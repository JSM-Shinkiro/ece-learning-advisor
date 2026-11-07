# Runtime and deployment readiness

Later backend preparation: [November 6 shared-cache coordination](40_SHARED_EMBEDDING_CACHE.md) adds bounded public document-build reuse within one server process and controlled concurrent-request checks. The November 5 observations below retain their original scope and measurements.

Implemented and verified November 5, 2026. Runtime configuration is now validated before the app renders profile widgets. A separate preflight command checks local inputs and can verify both a real Streamlit server and the app's offline preview. This unit prepares the Python runtime; public hosting and live source/provider verification are separate steps.

## Configuration

`src/settings.py` reads the same environment/local `.env` settings used by the app. Defaults remain compatible with the current preview and Gemini setup:

| Setting | Default and behavior |
| --- | --- |
| `GEMINI_API_KEY` | Optional; takes precedence over `GOOGLE_API_KEY` |
| `EMBEDDING_MODEL` | `gemini-embedding-2` |
| `GENERATION_MODEL` | `gemini-3.5-flash-lite` |
| `EMBEDDING_DIMENSION` | 768; integer from 1 through 3072 |
| `ECE_REFRESH_SOURCES` | true; accepts true/false or 1/0 |
| `ECE_DEVELOPMENT_MODE` | false; accepts true/false or 1/0 |
| `ECE_CACHE_DIR` | Project `.cache`; relative paths resolve from the project root |
| `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` | Optional pair; partial configuration keeps that adapter disabled |

Model IDs use the supported Gemini naming format, optionally prefixed with `models/`. Local format/range validation does not establish account access or provider availability. The embedding bounds follow the [documented Gemini embedding controls](https://ai.google.dev/gemini-api/docs/embeddings); individual model requests still receive normal provider validation.

Malformed flags, model IDs, dimensions, or credential/path fields produce sanitized startup errors naming the setting. Submitted invalid values and credentials do not appear in those messages. Secret fields are excluded from settings representation and exports. The readiness report contains presence flags and public model options, not key values. Existing server keys remain absent from widget defaults and session values.

Source and embedding caches use separate subdirectories under `ECE_CACHE_DIR`. A writable external path supports hosts where the code directory is read-only. Existing cache schemas, content identities, atomic writes, and source revalidation remain unchanged. This is a rebuildable public-content cache, not a new profile database or background refresh service.

## Preflight and smoke test

From the repository root, use the existing environment:

```powershell
.\.venv\Scripts\python.exe scripts/check_deployment.py --smoke
```

For a new runtime, install `requirements.txt` first. Development tests additionally use `requirements-dev.txt`; the startup smoke check itself does not require pytest.

The preflight checks:

1. Runtime configuration and shared mode (`ECE_DEVELOPMENT_MODE=false`).
2. Installed versions against the seven pinned production requirements.
3. The reviewed catalog, evidence construction, and connector configuration.
4. Source/embedding cache writability using temporary probe files.
5. With `--smoke`, a fresh loopback Streamlit process returning `ok` from `/_stcore/health`.
6. The same app's offline AppTest session, including a submitted roadmap and no external HTTP attempts.

The [Streamlit deployment documentation](https://docs.streamlit.io/deploy/tutorials/docker) describes the health endpoint. Here it is treated as liveness; the separate preview check must also pass. A successful HTTP response alone cannot pass a failed app preview.

Smoke children receive explicit blank credential variables, offline source mode, development mode off, a temporary cache directory, and the validated model settings. Explicit blanks prevent a local `.env` from reintroducing keys. The application's synchronous HTTPX and urllib clients are blocked during the preview, with attempts counted as failures. The server listens only on loopback during this check and is terminated on completion or failure. Captured child diagnostics are not copied into the report.

The command saves `deployment_check.json` under `ECE_CACHE_DIR`; `--output` selects another destination. Configuration/dependency/data/cache failures or either startup failure produce exit 1. Optional remote credentials are not authenticated. Public sources, job APIs, and Gemini are not contacted, and this command does not establish academic eligibility or model-answer accuracy.

## Hosting configuration

Run from the repository root and supply credentials through the host's environment. Standard Streamlit settings control the service interface, for example:

```powershell
$env:ECE_DEVELOPMENT_MODE = "false"
$env:STREAMLIT_SERVER_ADDRESS = "0.0.0.0"
$env:STREAMLIT_SERVER_PORT = "8501"
$env:STREAMLIT_SERVER_FILE_WATCHER_TYPE = "none"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Use the address/port required by the hosting service. The [official configuration guide](https://docs.streamlit.io/develop/concepts/configuration/options) explains environment variables and command-line precedence. The host still needs appropriate networking, HTTPS/session handling, environment credentials, and access to official sources. These host-specific properties are not tested by the loopback check.

## Verification

The complete suite passes **789 tests**, including **48 settings cases**, **12 deployment cases**, and **39 Streamlit interactions**. New cases cover flag/dimension/model/path validation, credential redaction and precedence, sanitized UI failures and recovery, cache routing, missing dependencies, corrupt data, shared-mode rejection, process cleanup, credential-free child settings, liveness versus preview failures, and CLI report placement from another working directory.

The [November 5 evidence](evidence/deployment_checks_2026-11-05.json) records a fresh isolated Python 3.12 environment on Linux, installed from the unchanged production requirements. `pip check` found no broken requirements. All eight preflight/smoke checks passed, including real server liveness and an offline roadmap submission. The report retains the observed dependency versions and implementation hashes. No system-site packages, model calls, external source requests, or public deployment were used in that runtime check.

The Windows commands above are provided for the project's existing PowerShell workflow; this fresh-install observation is specifically Linux/Python 3.12. Earlier source/provider/evaluation measurements retain their own dates and scope. Broader deployment validation, independent evaluation, and remaining academic-source coverage are still open.
