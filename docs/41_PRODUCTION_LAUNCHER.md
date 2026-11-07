# Production launch command

Implemented and verified November 6, 2026 MST (November 7 UTC). The app now has one shared-server start command that validates its environment and local inputs before starting Streamlit. The readiness smoke check exercises this same launcher. Public hosting, HTTPS/access configuration, remote browser sessions, and independent student evaluation remain open.

## Start the server

Install the pinned production requirements in the host's Python environment, then use:

```bash
python -m pip install -r requirements.txt
python scripts/serve.py --check
python scripts/serve.py
```

`--check` prints the local readiness report and exits without starting a server. A valid check-only run contains seven checks. Normal startup runs the same preflight and refuses to start when configuration, shared mode, dependencies, catalog/connectors, or cache access fail. It requires `ECE_DEVELOPMENT_MODE=false`. Provider credentials stay optional for preview mode; no model or public-source requests are made by startup preflight. Credentials use the existing environment/local `.env` path and are excluded from arguments and readiness output. Host environment values take precedence over local `.env` values.

For a local PowerShell check with the project's existing environment:

```powershell
.\.venv\Scripts\python.exe scripts/serve.py --check --address 127.0.0.1
.\.venv\Scripts\python.exe scripts/serve.py --address 127.0.0.1
```

The launcher defaults to `0.0.0.0` for host networking. The explicit local address above restricts the listener to loopback. Ordinary development with `python -m streamlit run app.py` remains available.

## Host bindings

| Option | Precedence and validation |
| --- | --- |
| Port | `--port`, then `PORT`, then `STREAMLIT_SERVER_PORT`, then 8501; integer 1–65535 |
| Address | `--address`, then `STREAMLIT_SERVER_ADDRESS`, then `0.0.0.0`; IP literal or `localhost` |
| URL prefix | `--base-path`, then `STREAMLIT_SERVER_BASE_URL_PATH`, then root; simple slash-separated letters, numbers, underscores, and hyphens |

An explicitly empty/malformed port fails rather than silently selecting the default. Prefixes normalize one leading/trailing slash: `/ece/advisor/` becomes `ece/advisor`. URLs, dot/parent segments, encoded separators, repeated separators, control characters, and excessive lengths are rejected. A configured prefix changes the health path, for example `/ece/advisor/_stcore/health`. An explicit `--base-path ""` selects the root even when the environment contains a prefix.

The selected bindings are passed as validated argument-list values and normalized environment entries. The launcher uses the active Python interpreter and an absolute `app.py` path, switches to the repository root, and replaces itself with the Streamlit process through `os.execve`. It starts one server process, with headless mode enabled, file watching disabled, and usage statistics disabled. This supports a host-supplied `PORT` without shell interpolation or a custom command per platform. Credentials travel only through the environment; they are not added to command arguments or JSON reports.

The launcher preflight does not authenticate provider keys, test public sources, or prove that the chosen socket is available. Streamlit still reports binding failures after process replacement. Runtime format checks and the opt-in [provider verifier](39_RUNTIME_PROVIDER_VERIFICATION.md) remain separate. The existing [public-document cache coordination](40_SHARED_EMBEDDING_CACHE.md) applies inside this one process; additional replicas are not coordinated.

Keep the host's writable cache under `ECE_CACHE_DIR`. Its public source/vector data remains rebuildable, and on-use source revalidation retains the existing freshness and academic-evidence boundaries. No profile/content database or scheduled service is added by this launcher. The host still needs matching HTTP/WebSocket routing for any prefix, HTTPS/access settings, and remote availability checks.

## Readiness and observations

`python scripts/check_deployment.py --smoke` now records **nine checks**. The added `server_configuration` check validates the configured address/port/prefix without opening a socket. The smoke portion starts `scripts/serve.py` on a fresh loopback port with an explicitly empty prefix, blank credentials, offline source mode, and an isolated cache; it then checks liveness and the existing offline AppTest roadmap. Thus the smoke verifies a local isolated launch, while the report's configured bindings are syntax-checked separately. A configured public address or port is not tested by that isolated smoke.

All **1,433 tests pass**, including **42 new hosting cases** and the existing **62 Streamlit interactions**. New cases cover precedence, port boundaries, IP/prefix normalization, malformed private values, safe diagnostics, shell-free command construction, environment preservation, shared-mode/cache failures, check-only behavior, process replacement arguments, missing imports, operating-system errors, and execution from another working directory. The existing child-process test now requires the same launcher and an explicit root prefix.

A separate existing production-only Python 3.12.14 environment, with no pytest installed, verifies seven real command/process scenarios:

| Scenario | Observed result |
| --- | --- |
| Check-only command from another directory | Exit 0; all seven local checks pass and the prefixed health path is reported |
| Explicit port overrides malformed host `PORT` | Exit 0; validated explicit port retained without exposing the rejected fixture value |
| Malformed host port | Exit 1; safe diagnostic |
| Development mode enabled | Exit 1; shared-mode check fails |
| Cache path is an existing regular file | Exit 1; file contents preserved |
| Native launch with a host port and `/advisor/` prefix | Correct port wins over Streamlit's competing port; prefixed health returns `200 ok`, prefixed page returns 200, unprefixed health returns 404; process terminates/reaps and listener closes |
| Port already occupied | Server exits 1; existing listener preserved |

All nine readiness/smoke checks also pass in that production environment. The probes use only loopback HTTP targets, blank real credentials, no model or public-source requests, and no participant judgments. A static page/liveness response plus a separate AppTest does not establish a remotely connected browser/WebSocket session or a hosted pilot. This observation is Linux/Python 3.12; the PowerShell commands are provided for the project workflow without asserting a separate Windows execution.

The [dated evidence](evidence/production_launcher_2026-11-06.json) records these outcomes, production versions, implementation hashes, and preserved-input fingerprints. Earlier readiness and actual provider/source measurements retain their original dates and scopes. No new relevance result, academic interpretation, or public deployment is claimed. The prepared review grades remain blank and the submitted midproject artifacts remain unchanged.

The command follows the documented [Streamlit configuration precedence](https://docs.streamlit.io/develop/concepts/configuration/options), its [health endpoint](https://docs.streamlit.io/deploy/tutorials/docker), and Python's [process replacement interface](https://docs.python.org/3.12/library/os.html#os.execve). No dependency is added.
