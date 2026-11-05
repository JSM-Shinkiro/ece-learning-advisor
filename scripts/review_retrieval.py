"""Prepare an unscored review packet or score a separately completed form offline."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.catalog import load_catalog
from src.review import (ReviewForm, ReviewPacket, blank_form, load_review_json, make_packet,
                        packet_markdown, score_review)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Export all evidence and blank grades, with no ranking hints")
    prepare.add_argument("--packet-id", default="p07-review-v1")
    prepare.add_argument("--questions", type=Path, help="JSON list of {case_id, query}; default reuses development questions")
    prepare.add_argument("--seed", type=int, default=7)
    prepare.add_argument("--output", type=Path, required=True, help="New directory; existing directories are never overwritten")
    score = commands.add_parser("score", help="Validate a complete review, then measure keyword retrieval")
    score.add_argument("--packet", type=Path, required=True)
    score.add_argument("--review", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True, help="New JSON report; existing files are never overwritten")
    score.add_argument("--query-mode", choices=["raw", "expanded"], default="raw")
    score.add_argument("--k", type=int, default=5)
    args = parser.parse_args()
    try:
        catalog = load_catalog()
        if args.command == "prepare":
            questions = load_review_json(args.questions) if args.questions else None
            if args.questions and not isinstance(questions, list):
                raise ValueError("Custom questions must be a JSON list")
            packet = make_packet(catalog, packet_id=args.packet_id, questions=questions, seed=args.seed)
            form = blank_form(packet)
            guide = packet_markdown(packet)
            # Prepare all content before reserving a new destination.
            args.output.mkdir(parents=True, exist_ok=False)
            (args.output / "packet.json").write_text(packet.model_dump_json(indent=2) + "\n", encoding="utf-8")
            (args.output / "review_template.json").write_text(form.model_dump_json(indent=2) + "\n", encoding="utf-8")
            (args.output / "review_guide.md").write_text(guide, encoding="utf-8")
            print(f"Prepared {len(packet.questions)} questions and {len(packet.evidence)} evidence chunks; all grades are blank.")
        else:
            packet = ReviewPacket.model_validate(load_review_json(args.packet))
            form = ReviewForm.model_validate(load_review_json(args.review))
            report = score_review(catalog, packet, form, k=args.k, query_mode=args.query_mode)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(json.dumps(report, indent=2) + "\n")
            print("Scored completed review; reviewer role is self-reported. This is not proof of held-out quality.")
        return 0
    except (OSError, ValueError, TypeError, RecursionError):
        print("Review command could not complete. Check input format, snapshot binding, complete grades, and a new writable output path.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
