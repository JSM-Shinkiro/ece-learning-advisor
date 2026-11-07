# Automatic backend checks

Added November 6, 2026 MST. `.github/workflows/backend.yml` runs the project's existing test suite and local startup smoke in Python 3.12 on GitHub's `ubuntu-latest` and `windows-latest` runners. The first hosted execution must be observed before either runner is claimed as passing. Public app hosting and independent relevance/usability review remain separate.

## What runs

Code, tests, runtime/evaluation data, dependency/configuration files, and workflow changes trigger checks on pushes to `main` and pull requests targeting it. A manual `workflow_dispatch` is also available. Documentation-only changes do not trigger another run. Both OS jobs run independently, each with a fifteen-minute limit; newer runs for the same ref cancel older in-progress runs.

Each job checks out the exact event revision, selects Python 3.12, installs the unchanged pinned development requirements, runs `pip check`, executes the full pytest suite (including Streamlit interactions), then runs the production launcher/offline-preview smoke. The smoke step still runs after test failure unless the job was cancelled. Default runner shells are used, including PowerShell on Windows. UTF-8 mode is explicit in both jobs. `.gitattributes` preserves LF line endings for JSON so archived byte fingerprints survive Windows checkouts.

The workflow has repository-content read permission, disables checkout credential persistence, and uses full upstream commit IDs for the three official GitHub actions. Gemini/Google and Adzuna key variables are explicitly blank. Source refresh is disabled for the runtime smoke, and tests use their existing controlled adapters. Installing dependencies still uses package/network infrastructure; the workflow is not an isolated-network test or a provider-access check.

Each job uploads only `output/ci/tests.xml` and `output/ci/deployment.json`, retained for fourteen days. Source/vector caches, private profiles, request traces, and credentials are not included in that artifact selection. Reports may be missing when setup fails; the job retains its failure status. The workflow reports checks; this change does not configure branch protection or make a check mandatory for merges.

## Reproduce locally

Use the installed development environment:

```powershell
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q --junitxml=output/ci/tests.xml
.\.venv\Scripts\python.exe scripts/check_deployment.py --smoke --output output/ci/deployment.json
```

Use blank credential variables and `ECE_DEVELOPMENT_MODE=false`, `ECE_REFRESH_SOURCES=false` for the same credential-free smoke profile. Actual provider/source verification remains an explicit separate action. A green run establishes the tests and local smoke on that recorded runner/version; it does not establish public availability, a remote browser/WebSocket session, academic eligibility, held-out relevance quality, or student-pilot outcomes.

The frozen benchmark, prepared blank reviewer bundle, historical evidence, and midproject snapshot remain unchanged. The development handoff will record actual hosted results after the first run.
