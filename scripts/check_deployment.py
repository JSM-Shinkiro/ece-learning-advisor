"""Validate local runtime readiness; --smoke also starts a loopback server and offline preview."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--output", type=Path, help="Defaults to deployment_check.json in ECE_CACHE_DIR")
    args = parser.parse_args()
    try:
        from dotenv import load_dotenv
        from src.deployment import check_deployment
        from src.settings import ConfigurationError, load_settings
    except ImportError:
        print("Install requirements.txt before running deployment checks.")
        return 1
    load_dotenv(ROOT / ".env")
    report = check_deployment(smoke=args.smoke)
    report["checked_at"] = datetime.now(timezone.utc).isoformat()
    for check in report["checks"]:
        print(check["name"], "passed" if check["passed"] else "failed", "·", check["detail"])
    try:
        output = args.output or load_settings().cache_root / "deployment_check.json"
    except ConfigurationError:
        output = args.output or ROOT / ".cache/deployment_check.json"
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except OSError:
        print("The readiness report could not be saved; choose a writable --output path.")
        return 1
    print("Saved", output)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
