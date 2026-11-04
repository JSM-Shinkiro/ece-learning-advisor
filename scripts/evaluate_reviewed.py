"""Evaluate frozen references. Optional live embeddings require an explicit flag."""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.catalog import ROOT, load_catalog
from src.evaluation import DEFAULT_SUITE, evaluate_suite, load_suite, report_markdown
from src.providers import GeminiProvider, ProviderError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', type=Path, default=DEFAULT_SUITE)
    parser.add_argument('--output', type=Path, default=ROOT / '.cache' / 'reviewed_evaluation.json')
    parser.add_argument('--markdown', type=Path)
    parser.add_argument('--k', type=int, default=5)
    parser.add_argument('--methods', nargs='+', choices=['keyword', 'semantic', 'hybrid'], default=['keyword'])
    parser.add_argument('--live-embeddings', action='store_true', help='Opt in to real embedding requests and provider quota; no generation calls.')
    parser.add_argument('--embedding-model', default='gemini-embedding-2')
    parser.add_argument('--dimensions', type=int, default=768)
    args = parser.parse_args()
    if not 1 <= args.k <= 100 or args.dimensions < 1:
        parser.error('Use a cutoff from 1 to 100 and a positive embedding dimension.')
    if len(set(args.methods)) != len(args.methods):
        parser.error('Retrieval methods must be unique.')
    neural = bool(set(args.methods) & {'semantic', 'hybrid'})
    if neural != args.live_embeddings:
        parser.error('Semantic/hybrid methods require --live-embeddings; keyword-only runs do not use it.')
    provider = None
    try:
        catalog = load_catalog()
        suite = load_suite(catalog, args.suite)
        if neural:
            from dotenv import load_dotenv
            load_dotenv(ROOT / '.env')
            provider = GeminiProvider(os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY'),
                                      embedding_model=args.embedding_model, dimensions=args.dimensions)
        report = evaluate_suite(catalog, suite, k=args.k, methods=args.methods, embedder=provider,
                                embedding_origin='live_provider' if provider else None)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        if args.markdown:
            args.markdown.parent.mkdir(parents=True, exist_ok=True)
            args.markdown.write_text(report_markdown(report), encoding='utf-8')
        print(json.dumps({'suite_id': report['suite_id'], 'retrieval': report['retrieval_summary'],
            'policy': report['policy_summary'], 'claims': report['claim_summary'],
            'render_contract': report['render_contract_summary'], 'output': str(args.output)}, indent=2))
        return 0 if report['regression_checks_passed'] else 1
    except (OSError, ValueError, ProviderError) as exc:
        print('Evaluation could not complete:', str(exc), file=sys.stderr)
        return 2
    finally:
        if provider is not None:
            provider.close()


if __name__ == '__main__':
    raise SystemExit(main())
