import json
from types import SimpleNamespace

import pytest

from src.catalog import build_evidence
from src.ingest import extract_course
from src.models import GeneratedAnswer, StudentProfile
from src.providers import GeminiProvider, ProviderError
from src.service import recommend


def test_adapter_uses_separate_document_and_query_requests(catalog):
    calls=[]
    def embed(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(embeddings=[SimpleNamespace(values=[1,2,3])])
    provider=GeminiProvider("fixture",dimensions=3,client=SimpleNamespace(models=SimpleNamespace(embed_content=embed)))
    provider.embed_document(build_evidence(catalog)[0])
    provider.embed_query("neural networks")
    assert calls[0]["contents"].startswith("title:")
    assert calls[1]["contents"]=="task: search result | query: neural networks"
    assert all(isinstance(c["contents"],str) for c in calls)
    assert calls[0]["config"].output_dimensionality==3


def test_adapter_rejects_aggregated_or_wrong_dimension(catalog):
    client=SimpleNamespace(models=SimpleNamespace(embed_content=lambda **k:SimpleNamespace(
        embeddings=[SimpleNamespace(values=[1,2]),SimpleNamespace(values=[2,3])])))
    provider=GeminiProvider("fixture",dimensions=3,client=client)
    with pytest.raises(ProviderError):
        provider.embed_query("query")


def test_generator_receives_exact_serialized_context(catalog):
    context=recommend(catalog,StudentProfile()).context
    captured={}
    def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(output_text=GeneratedAnswer(status="insufficient_evidence",
            clarification="The question is outside this collection.").model_dump_json())
    provider=GeminiProvider("fixture",client=SimpleNamespace(interactions=SimpleNamespace(create=create)))
    answer=provider.generate(context)
    assert captured["input"]==context.to_prompt()
    assert captured["response_format"]["mime_type"]=="application/json"
    assert captured["store"] is False
    assert answer.status=="insufficient_evidence"


def test_ingestion_parses_data_without_executing_scripts():
    table=[
        {"code":1,"longName":2,"description":3,"credits":4,"requirementGroup":7,"effectiveStartDate":8},
        "DEMO101","Fixture course","Synthetic fixture text",
        {"creditHours":5},{"min":6,"max":6},4,"R001","2026-01-01"
    ]
    page='<script>throw new Error("must not execute")</script><script id="__NUXT_DATA__" type="application/json">'+json.dumps(table)+"</script>"
    result=extract_course(page)
    assert result["code"]=="DEMO101"
    assert result["credits"]=={"min":4,"max":4}
    assert result["review_required"]


def test_unrecognized_ingestion_format_fails():
    with pytest.raises(ValueError):
        extract_course("<html>changed layout</html>")
