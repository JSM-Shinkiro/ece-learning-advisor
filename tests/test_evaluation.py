"""Evaluation math, frozen-reference binding, and provider-call boundaries."""

import json
import math

import pytest
from pydantic import ValidationError

from src.catalog import corpus_hash
from src.evaluation import (DEFAULT_SUITE, EvaluationSuite, catalog_snapshot_hash, evaluate_suite,
                            labels_hash, load_suite, rank_metrics, report_markdown, validate_suite)
from src.providers import ProviderError


@pytest.fixture
def suite(catalog):
    return load_suite(catalog)


def test_rank_metrics_match_hand_calculated_graded_example():
    grades = {'a': 3, 'b': 2, 'c': 1, 'd': 0}
    result = rank_metrics(['b', 'd', 'a'], grades, k=3)
    assert result['precision'] == pytest.approx(2 / 3)
    assert result['recall'] == 1 and result['reciprocal_rank'] == 1
    assert result['ndcg'] == pytest.approx((2 + 3 / 2) / (3 + 2 / math.log2(3) + 1 / 2))


def test_short_rankings_keep_the_fixed_k_precision_denominator():
    result = rank_metrics(['a'], {'a': 3, 'b': 2}, k=5)
    assert result['precision'] == .2 and result['recall'] == .5
    assert result['reciprocal_rank'] == 1
    assert result['ndcg'] == pytest.approx(3 / (3 + 2 / math.log2(3)))


def test_cutoff_and_background_grade_are_distinct_from_binary_relevance():
    result = rank_metrics(['a', 'b', 'c'], {'a': 0, 'b': 1, 'c': 3}, k=2)
    assert result['precision'] == result['recall'] == result['reciprocal_rank'] == 0
    assert 0 < result['ndcg'] < 1  # Background gets graded gain, not a binary hit.


@pytest.mark.parametrize('ranking', [[], ['b']])
def test_no_relevant_result_scores_zero(ranking):
    assert rank_metrics(ranking, {'a': 3, 'b': 0}, k=5) == {
        'precision': 0, 'recall': 0, 'reciprocal_rank': 0, 'ndcg': 0}


def test_undefined_metrics_remain_absent_instead_of_becoming_perfect_scores():
    result = rank_metrics(['a'], {'a': 0})
    assert result['precision'] == 0 and result['recall'] is None
    assert result['reciprocal_rank'] is None and result['ndcg'] is None


@pytest.mark.parametrize('k', [0, -1, 101, True, 2.5, '5'])
def test_invalid_cutoffs_are_rejected(k):
    with pytest.raises(ValueError, match='cutoff'):
        rank_metrics([], {'a': 3}, k=k)


@pytest.mark.parametrize('threshold', [0, 4, True, '2'])
def test_invalid_binary_thresholds_are_rejected(threshold):
    with pytest.raises(ValueError, match='threshold'):
        rank_metrics([], {'a': 3}, relevant_minimum=threshold)


@pytest.mark.parametrize('grade', [True, -1, 4, '3', 2.5])
def test_invalid_grades_are_rejected(grade):
    with pytest.raises(ValueError, match='grades'):
        rank_metrics([], {'a': grade})


@pytest.mark.parametrize('ids', [['a', 'a'], ['unknown']])
def test_duplicate_and_unjudged_ids_cannot_inflate_metrics(ids):
    with pytest.raises(ValueError, match='unique and judged'):
        rank_metrics(ids, {'a': 3})


def test_saved_suite_has_complete_judgments_and_separate_review_scopes(catalog, suite):
    assert len(suite.retrieval_cases) == 16 and len(suite.policy_cases) == 18 and len(suite.claim_probes) == 16
    assert suite.label_origin == 'assistant-authored source review'
    assert suite.labels_hash == labels_hash(suite)
    assert suite.catalog_snapshot_hash == catalog_snapshot_hash(catalog)
    assert {case.split for case in suite.retrieval_cases} == {'development', 'validation'}


@pytest.mark.parametrize('change', ['summary', 'stage', 'freshness', 'rule'])
def test_full_snapshot_binding_catches_more_than_embedding_content(catalog, suite, change):
    before = corpus_hash(catalog)
    if change == 'summary': catalog.records[0].summary = 'Changed fixture source summary.'
    elif change == 'stage': catalog.records[0].study_stage = 'advanced'
    elif change == 'freshness': catalog.sources[0].verification_status = 'verified'
    else: next(r for r in catalog.records if r.code == 'CSC120').rule.minimum_grade = 'B'
    if change != 'summary':
        assert corpus_hash(catalog) == before
    with pytest.raises(ValueError, match='corpus changed'):
        validate_suite(suite, catalog)


def test_changing_a_frozen_judgment_requires_explicit_review(catalog, suite):
    suite.retrieval_cases[0].query += ' extra fixture wording'
    with pytest.raises(ValueError, match='reference labels changed'):
        validate_suite(suite, catalog)


@pytest.mark.parametrize('corruption', ['partial_judgments', 'unknown_policy', 'split_bundle', 'unprovided_review', 'duplicate_context'])
def test_explicitly_rehashed_but_inconsistent_references_are_rejected(catalog, suite, corruption):
    if corruption == 'partial_judgments':
        suite.retrieval_cases[0].relevance.pop(next(iter(suite.retrieval_cases[0].relevance)))
    elif corruption == 'unknown_policy':
        suite.policy_cases[0].required_records.append('outside:record')
    elif corruption == 'split_bundle':
        probe = next(p for p in suite.claim_probes if p.case_id == 'claim_or_supported')
        probe.context_chunk_ids = [rid for rid in probe.context_chunk_ids if ':rule:' not in rid]
    elif corruption == 'unprovided_review':
        suite.claim_probes[0].reviews[0].reference_evidence_ids = ['unprovided:chunk']
    else:
        suite.claim_probes[0].context_chunk_ids.append(suite.claim_probes[0].context_chunk_ids[0])
    suite.labels_hash = labels_hash(suite)
    with pytest.raises(ValueError):
        validate_suite(suite, catalog)


@pytest.mark.parametrize('bad', ['duplicate_case', 'missing_reason_review', 'wrong_claim_type'])
def test_review_schema_rejects_ambiguous_reference_labels(suite, bad):
    data = suite.model_dump(mode='json')
    if bad == 'duplicate_case': data['policy_cases'][0]['case_id'] = data['retrieval_cases'][0]['case_id']
    elif bad == 'missing_reason_review': data['claim_probes'][0]['reviews'][0]['reason_index'] = 1
    else: data['claim_probes'][0]['reviews'][0]['verdict'] = 'recommendation'
    with pytest.raises(ValidationError):
        EvaluationSuite.model_validate(data)


def test_offline_evaluation_has_no_provider_or_source_calls(catalog, suite, monkeypatch, fake_provider):
    import httpx
    before = DEFAULT_SUITE.read_bytes()
    def forbidden(*args, **kwargs): raise AssertionError('Offline evaluation must not make network or generation calls')
    monkeypatch.setattr(httpx, 'Client', forbidden)
    fake_provider.generate = forbidden
    report = evaluate_suite(catalog, suite, embedder=fake_provider)
    assert report['embedding']['document_calls'] == report['embedding']['query_calls'] == 0
    assert fake_provider.document_calls == 0
    assert report['generation_calls'] == report['source_refresh_calls'] == 0
    assert report['policy_summary'] == {'cases': 18, 'passed': 18}
    assert report['claim_summary']['integrity_expectations_matched'] == 16
    assert report['claim_summary']['unsupported_claims_admitted_by_reference_checks'] == 9
    assert all(case['answer_origin'] == 'authored_probe' for case in report['claim_probes'])
    assert DEFAULT_SUITE.read_bytes() == before
    markdown = report_markdown(report)
    assert 'not an independent held-out benchmark' in markdown and 'admitted by citation checks: 9' in markdown


def test_repeated_local_scores_are_deterministic(catalog, suite):
    first, second = evaluate_suite(catalog, suite), evaluate_suite(catalog, suite)
    assert first['retrieval_summary'] == second['retrieval_summary']
    assert first['policy_cases'] == second['policy_cases'] and first['claim_probes'] == second['claim_probes']
    assert [r['ranked_chunk_ids'] for r in first['retrieval_cases']] == [r['ranked_chunk_ids'] for r in second['retrieval_cases']]


@pytest.mark.parametrize('origin', [None, 'unverified'])
def test_semantic_evaluation_cannot_silently_fall_back(catalog, suite, fake_provider, origin):
    with pytest.raises(ValueError, match='no silent keyword fallback'):
        evaluate_suite(catalog, suite, methods=['semantic'], embedder=fake_provider, embedding_origin=origin)
    assert fake_provider.document_calls == 0


def test_controlled_vectors_remain_labeled_and_are_shared_between_methods(catalog, suite, fake_provider, tmp_path):
    def forbidden(*args): raise AssertionError('Evaluation must not generate answers')
    fake_provider.generate = forbidden
    report = evaluate_suite(catalog, suite, methods=['keyword', 'semantic', 'hybrid'], embedder=fake_provider,
                            embedding_origin='controlled_fixture', cache_dir=tmp_path)
    assert report['embedding']['origin'] == 'controlled_fixture'
    assert report['embedding']['document_calls'] == 10 and report['embedding']['query_calls'] == 16
    assert len(report['retrieval_cases']) == 48 and report['generation_calls'] == 0
    assert set(report['retrieval_summary']) == {'keyword', 'semantic', 'hybrid'}


def test_embedding_failure_does_not_publish_mislabeled_keyword_scores(catalog, suite, fake_provider, tmp_path):
    def fail(*args): raise ProviderError('Controlled fixture embedding failure')
    fake_provider.embed_query = fail
    with pytest.raises(ProviderError):
        evaluate_suite(catalog, suite, methods=['hybrid'], embedder=fake_provider,
                       embedding_origin='controlled_fixture', cache_dir=tmp_path)


def test_invalid_methods_fail_before_provider_calls(catalog, suite, fake_provider):
    for methods in [[], ['keyword', 'keyword'], ['unknown']]:
        with pytest.raises(ValueError):
            evaluate_suite(catalog, suite, methods=methods, embedder=fake_provider)
    assert fake_provider.document_calls == 0


def test_cli_default_saves_a_complete_offline_report(monkeypatch, tmp_path):
    from scripts import evaluate_reviewed as cli
    output, markdown = tmp_path / 'report.json', tmp_path / 'report.md'
    monkeypatch.setattr('sys.argv', ['evaluate_reviewed', '--output', str(output), '--markdown', str(markdown)])
    def forbidden(*args, **kwargs): raise AssertionError('Default CLI must not construct a provider')
    monkeypatch.setattr(cli, 'GeminiProvider', forbidden)
    assert cli.main() == 0
    assert json.loads(output.read_text())['generation_calls'] == 0
    assert 'Reviewed development evaluation' in markdown.read_text()


def test_cli_requires_explicit_quota_opt_in(monkeypatch):
    from scripts import evaluate_reviewed as cli
    monkeypatch.setattr('sys.argv', ['evaluate_reviewed', '--methods', 'semantic'])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2


@pytest.mark.parametrize('options', [['--k', '0'], ['--dimensions', '0'], ['--methods', 'semantic', 'semantic']])
def test_cli_rejects_invalid_configuration_before_constructing_a_provider(monkeypatch, options):
    from scripts import evaluate_reviewed as cli
    def forbidden(*args, **kwargs): raise AssertionError('Invalid configuration must not construct a provider')
    monkeypatch.setattr(cli, 'GeminiProvider', forbidden)
    monkeypatch.setattr('sys.argv', ['evaluate_reviewed', '--methods', 'semantic', '--live-embeddings', *options])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2


def test_cli_reports_policy_regression_without_hiding_the_report(monkeypatch, tmp_path, suite):
    from scripts import evaluate_reviewed as cli
    suite.policy_cases[0].first_course = 'uofa:ECE425:2026-2027'
    suite.labels_hash = labels_hash(suite)
    path = tmp_path / 'controlled_regression_suite.json'
    path.write_text(suite.model_dump_json())
    output = tmp_path / 'report.json'
    monkeypatch.setattr('sys.argv', ['evaluate_reviewed', '--suite', str(path), '--output', str(output)])
    assert cli.main() == 1
    report = json.loads(output.read_text())
    assert report['policy_summary']['passed'] < report['policy_summary']['cases']
    assert not report['regression_checks_passed']
