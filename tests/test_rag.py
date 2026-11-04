import pytest

from src.catalog import build_evidence
from src.models import GeneratedAnswer, Reason, Recommendation, StudentProfile
from src.providers import ProviderError
from src.service import CitationError, recommend, validate_answer


def answer_for(context, citation=None, record_id=None):
    rid=record_id or context.allowed_record_ids[0]
    chunk=next(e for e in context.evidence if e.record_id==context.allowed_record_ids[0])
    return GeneratedAnswer(status="answered",recommendations=[
        Recommendation(record_id=rid,reasons=[Reason(text="A learning connection.",claim_type="recommendation",
            evidence_ids=[citation or chunk.chunk_id])])
    ])


def test_real_orchestration_passes_exact_context(catalog,fake_provider,tmp_path):
    result=recommend(catalog,StudentProfile(),provider=fake_provider,cache_dir=tmp_path)
    assert result.generation_complete
    assert fake_provider.context is result.context
    assert result.trace["context_chunk_ids"]==[e.chunk_id for e in result.context.evidence]
    assert result.retrieval_mode=="hybrid"
    assert all(v.status=="unknown" for v in result.context.rule_results.values())


def test_unknown_citation_is_rejected(catalog):
    context=recommend(catalog,StudentProfile()).context
    with pytest.raises(CitationError):
        validate_answer(answer_for(context,citation="invented"),context)


def test_known_but_unsupplied_evidence_rejected(catalog):
    context=recommend(catalog,StudentProfile()).context
    unsupplied=next(e.chunk_id for e in build_evidence(catalog) if e.chunk_id not in {x.chunk_id for x in context.evidence})
    with pytest.raises(CitationError):
        validate_answer(answer_for(context,citation=unsupplied),context)


def test_unknown_recommendation_is_rejected(catalog):
    context=recommend(catalog,StudentProfile()).context
    with pytest.raises(CitationError):
        validate_answer(answer_for(context,record_id="invented-course"),context)


def test_generation_failure_preserves_cards(catalog,fake_provider,tmp_path):
    def fail(context):
        raise ProviderError("Unavailable")
    fake_provider.generate=fail
    result=recommend(catalog,StudentProfile(),provider=fake_provider,cache_dir=tmp_path)
    assert result.context.allowed_record_ids
    assert not result.generation_complete
    assert result.answer is None
    assert result.issues


def test_bad_citations_do_not_render_as_valid_rag(catalog,fake_provider,tmp_path):
    fake_provider.generate=lambda context: answer_for(context,citation="invented")
    result=recommend(catalog,StudentProfile(),provider=fake_provider,cache_dir=tmp_path)
    assert result.answer is None
    assert not result.trace["reference_checks_passed"]


def test_generation_abstention_is_supported(catalog,fake_provider,tmp_path):
    fake_provider.generate=lambda context: GeneratedAnswer(status="insufficient_evidence",clarification="That topic is outside this collection.")
    result=recommend(catalog,StudentProfile(),provider=fake_provider,cache_dir=tmp_path)
    assert result.answer.status=="insufficient_evidence"
    assert result.answer.recommendations==[]


def test_keyword_mode_can_still_use_generation(catalog,fake_provider,tmp_path):
    result=recommend(catalog,StudentProfile(),provider=fake_provider,method="keyword",cache_dir=tmp_path)
    assert result.generation_complete
    assert fake_provider.document_calls==0
    assert result.retrieval_mode=="keyword"


def test_source_exploration_is_not_reported_as_generation(catalog):
    result=recommend(catalog,StudentProfile())
    assert not result.generation_complete
    assert result.answer is None
