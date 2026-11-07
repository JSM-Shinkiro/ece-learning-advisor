"""Preflight and launch ECE Learning Advisor for one shared server process."""

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--address", help="IP address or localhost; defaults to STREAMLIT_SERVER_ADDRESS or 0.0.0.0")
    parser.add_argument("--port", help="Overrides PORT, STREAMLIT_SERVER_PORT, and the default 8501")
    parser.add_argument("--base-path", help="Optional simple URL prefix; overrides STREAMLIT_SERVER_BASE_URL_PATH")
    parser.add_argument("--check", action="store_true", help="Print local preflight JSON without starting a server")
    args = parser.parse_args()
    try:
        from dotenv import load_dotenv
        from src.deployment import check_deployment
        from src.hosting import launch_server, load_server_options
        from src.settings import ConfigurationError
    except ImportError:
        print("Install requirements.txt before launching the production server.", file=sys.stderr)
        return 1
    try:
        load_dotenv(ROOT / ".env")
        options = load_server_options(address=args.address, port=args.port, base_path=args.base_path)
        env = options.environment(os.environ)
        report = check_deployment(root=ROOT, environ=env)
        if args.check:
            print(json.dumps(report, indent=2))
            return 0 if report["passed"] else 1
        if not report["passed"]:
            failed = ", ".join(check["name"] for check in report["checks"] if not check["passed"])
            print("Production startup checks failed: " + failed + ". Run with --check for safe details.", file=sys.stderr)
            return 1
        os.chdir(ROOT)
        print("Starting ECE Learning Advisor.", flush=True)
        launch_server(options, env, root=ROOT)
        return 0  # A normal CLI exits/replaces this process; controlled tests can return here.
    except ConfigurationError as exc:
        print("Production startup configuration is invalid. " + str(exc), file=sys.stderr)
        return 1
    except (OSError, ValueError, RuntimeError):
        print("The production server could not start. Check the runtime, writable cache, and listen settings.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
