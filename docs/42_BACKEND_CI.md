# Automatic backend checks

Added November 6, 2026 MST. `.github/workflows/backend.yml` runs the project's existing test suite and local startup smoke in Python 3.12 on GitHub's `ubuntu-latest` and `windows-latest` runners. The current hosted follow-up passes all 1,438 tests and all nine readiness checks on both platforms. The initial Windows startup failure remains preserved alongside the launcher fix and successful follow-up. Public app hosting and independent relevance/usability review remain separate.

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

The frozen benchmark, prepared blank reviewer bundle, historical evidence, and midproject snapshot remain unchanged. The development handoff records actual hosted outcomes separately from local checks.

## Initial hosted observation and Windows follow-up

[Run 42341102188](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/42341102188), on commit `83aae8f206fd946997ce3e3c235a4145daa5632e`, remains unsuccessful. Linux (Python 3.12.16) passes 1,433 tests and all nine readiness checks. Windows (Python 3.12.10) passes 1,433 tests and seven local preflight checks, but server liveness and the dependent offline preview fail. Downloaded JUnit/readiness archives match the GitHub artifact digests; no test failure is being relabeled as a pass.

The follow-up keeps POSIX process replacement and changes Windows to execute Streamlit's public module entrypoint through `runpy` inside the monitored startup process. Windows CRT exec starts a new process, unlike POSIX replacement; this was the targeted compatibility issue inferred from the failed startup. The module is entered before any student sessions, with the validated environment/arguments and restoration on return, exit, failure, or interruption. Five new controlled cases cover both platform branches and cleanup. The separate hosted follow-up passes on both platforms after this change; the initial unsuccessful run is unchanged. See [Microsoft's exec interface](https://learn.microsoft.com/en-us/cpp/c-runtime-library/exec-wexec-functions) and [Python runpy](https://docs.python.org/3.12/library/runpy.html).

## Verified hosted follow-up

[Run 42341630907](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/42341630907), on fix commit `dd85e628727cd44e7bc1d629f3fb04080ab33ed7`, completes successfully:

| Runner | Python | Tests | Startup/readiness | Shell |
| --- | --- | ---: | --- | --- |
| `ubuntu-latest` | 3.12.16 | 1,438 passed | All nine passed | Bash |
| `windows-latest` | 3.12.10 | 1,438 passed | All nine passed | PowerShell |

Both JUnit files report zero failures, errors, or skipped tests. Both downloaded readiness reports retain blank-key presence flags, disabled source refresh, and zero model/public-source calls. All four initial/follow-up archive SHA-256 values match the artifact digests returned by GitHub. Dependency installation and artifact operations use normal GitHub/PyPI network access. The workflow uses the runner's bundled matching Python 3.12 patch version; it does not force the same patch on both OS images.

The [saved evidence](evidence/backend_ci_2026-11-06.json) binds job IDs, steps, Python/shell observations, JUnit summaries, readiness reports, artifact/log fingerprints, code hashes, and frozen-input hashes to their respective commits. It retains the initial failed status and separate successful follow-up. Local verification also passes all 1,438 tests, including five new launcher lifecycle controls (47 hosting cases overall), with the existing 62 Streamlit interactions. Times are single observations rather than a performance benchmark.

These hosted checks verify the recorded runner/profile and the local startup path. Public app hosting, a remotely connected browser/WebSocket session, student-pilot feedback, independently completed relevance judgments, and remaining ECE/edition evidence stay open. No model-quality or complete-enrollment result is inferred from a green workflow.
