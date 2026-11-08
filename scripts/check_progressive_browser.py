"""Check progressive AI with a controlled provider; always use an isolated local UI."""

import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--executable-path")
    args=parser.parse_args()
    try:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open("x",encoding="utf-8") as handle:
            try:
                from src.browser_checks import local_browser_server
                from src.progressive_browser_checks import run_progressive_browser_checks
                with tempfile.TemporaryDirectory(prefix="ece-progressive-control-") as control:
                    with local_browser_server(progressive_control=Path(control)) as url:
                        report=run_progressive_browser_checks(url,control,executable_path=args.executable_path,
                                                              diagnostics_dir=args.output.parent)
            except Exception as exc:
                report={"passed":False,"checks":[{"name":"controlled_server","passed":False,
                    "detail":"The isolated controlled browser process could not run.","error_type":type(exc).__name__}]}
            report["checked_at"]=datetime.now(timezone.utc).isoformat()
            handle.write(json.dumps(report,indent=2)+"\n")
    except FileExistsError:
        print("Choose a new report path; existing evidence is never replaced.",file=sys.stderr);return 1
    except OSError:
        print("The browser report could not be saved.",file=sys.stderr);return 1
    for check in report["checks"]:
        print(check["name"],"passed" if check["passed"] else "failed","·",check["detail"])
        if not check["passed"]:print("Failure type:",check.get("error_type"),"· checker line:",check.get("failure_line"))
    return 0 if report["passed"] else 1


if __name__=="__main__":raise SystemExit(main())
