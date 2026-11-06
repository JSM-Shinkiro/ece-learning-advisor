"""Prepare review inputs, explicitly precompute embeddings, or score judgments offline."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.catalog import load_catalog, load_runtime_catalog
from src.review import (MAX_VECTOR_BYTES, ReviewForm, ReviewPacket, blank_form, load_catalog_snapshot, load_review_json, make_packet,
                        packet_markdown, score_review)
from src.review_vectors import ReviewVectors, make_vectors
from src.providers import EmbeddingCache, GeminiProvider


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Export all evidence and blank grades, with no ranking hints")
    prepare.add_argument("--packet-id", default="p07-review-v1")
    prepare.add_argument("--questions", type=Path, help="JSON list of {case_id, query}; default reuses development questions")
    prepare.add_argument("--seed", type=int, default=7)
    prepare.add_argument("--output", type=Path, required=True, help="New directory; existing directories are never overwritten")
    embed = commands.add_parser("embed", help="Explicitly precompute a packet-bound vector snapshot; no grades or generation")
    embed.add_argument("--packet", type=Path, required=True)
    embed.add_argument("--output", type=Path, required=True, help="New JSON snapshot; existing files are never overwritten")
    embed.add_argument("--query-mode", choices=["raw", "expanded"], default="raw")
    embed.add_argument("--live-embeddings", action="store_true", help="Allow configured Gemini embedding requests/quota for exact packet evidence and questions")
    score = commands.add_parser("score", help="Validate complete judgments, then measure retrieval without provider calls")
    score.add_argument("--packet", type=Path, required=True)
    score.add_argument("--review", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True, help="New JSON report; existing files are never overwritten")
    score.add_argument("--query-mode", choices=["raw", "expanded"], default="raw")
    score.add_argument("--k", type=int, default=5)
    score.add_argument("--method", choices=["keyword", "semantic", "hybrid"], default="keyword")
    score.add_argument("--embeddings", type=Path, help="Required packet-bound snapshot for semantic/hybrid; keyword uses none")
    for command in (prepare, embed, score):
        selection = command.add_mutually_exclusive_group()
        selection.add_argument("--collection", choices=["baseline", "runtime"],
                               help="Saved collection to bind; defaults to the frozen baseline")
        selection.add_argument("--catalog-snapshot", type=Path,
                               help="Use an exported catalog_snapshot.json instead of the current repository collection")
    args = parser.parse_args()
    if args.command == "embed" and not args.live_embeddings:
        parser.error("Embedding creation requires the explicit --live-embeddings option; scoring remains offline.")
    try:
        catalog = (load_catalog_snapshot(args.catalog_snapshot) if args.catalog_snapshot else
                   load_runtime_catalog() if args.collection == "runtime" else load_catalog())
        if args.command == "prepare":
            questions = load_review_json(args.questions) if args.questions else None
            if args.questions and not isinstance(questions, list):
                raise ValueError("Custom questions must be a JSON list")
            packet = make_packet(catalog, packet_id=args.packet_id, questions=questions, seed=args.seed)
            form = blank_form(packet)
            guide = packet_markdown(packet)
            snapshot = catalog.model_dump_json(indent=2) + "\n"
            # Prepare all content before reserving a new destination.
            args.output.mkdir(parents=True, exist_ok=False)
            (args.output / "packet.json").write_text(packet.model_dump_json(indent=2) + "\n", encoding="utf-8")
            (args.output / "review_template.json").write_text(form.model_dump_json(indent=2) + "\n", encoding="utf-8")
            (args.output / "review_guide.md").write_text(guide, encoding="utf-8")
            (args.output / "catalog_snapshot.json").write_text(snapshot, encoding="utf-8")
            print(f"Prepared {len(packet.questions)} questions and {len(packet.evidence)} evidence chunks; all grades are blank.")
        elif args.command == "embed":
            from dotenv import load_dotenv
            from src.settings import load_settings
            from src.review import validate_packet
            if args.output.exists():
                raise ValueError("Choose a new embedding output path")
            packet = validate_packet(ReviewPacket.model_validate(load_review_json(args.packet)), catalog)
            load_dotenv(ROOT / ".env")
            settings = load_settings()
            if not settings.ai_configured:
                raise ValueError("An embedding provider is not configured")
            provider = GeminiProvider(settings.gemini_key.get_secret_value(), embedding_model=settings.embedding_model,
                generation_model=settings.generation_model, dimensions=settings.embedding_dimensions)
            try:
                vectors = make_vectors(catalog, packet, provider, EmbeddingCache(settings.cache_root / "embeddings"), query_mode=args.query_mode)
            finally:
                provider.close()
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(vectors.model_dump_json(indent=2) + "\n")
            print(f"Prepared embedding snapshot: {vectors.document_embedding_calls} document calls, {vectors.query_embedding_calls} query calls; no generation.")
        else:
            if args.output.exists():
                raise ValueError("Choose a new score output path")
            packet = ReviewPacket.model_validate(load_review_json(args.packet))
            form = ReviewForm.model_validate(load_review_json(args.review))
            embeddings = ReviewVectors.model_validate(load_review_json(args.embeddings, max_bytes=MAX_VECTOR_BYTES)) if args.embeddings else None
            report = score_review(catalog, packet, form, k=args.k, query_mode=args.query_mode,
                method=args.method, embeddings=embeddings)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(json.dumps(report, indent=2) + "\n")
            print("Scored completed review; reviewer role is self-reported. This is not proof of held-out quality.")
        return 0
    except (OSError, ValueError, TypeError, RecursionError, RuntimeError):
        print("Review command could not complete. Check input format, snapshot binding, complete grades, and a new writable output path.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
