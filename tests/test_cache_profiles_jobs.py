import io
import json
from types import SimpleNamespace

import pytest

from src.catalog import build_evidence
from src.jobs import search_jobs
from src.models import StudentProfile
from src.profiles import export_profile, import_profile, parse_completions
from src.providers import EmbeddingCache


def test_cache_reuses_only_matching_config(catalog,fake_provider,tmp_path):
    cache=EmbeddingCache(tmp_path)
    chunks=build_evidence(catalog)
    _,state,_=cache.get(catalog,chunks,fake_provider)
    calls=fake_provider.document_calls
    assert state=="miss"
    _,state,_=cache.get(catalog,chunks,fake_provider)
    assert state=="hit" and fake_provider.document_calls==calls
    fake_provider.embedding_model="different-model"
    _,state,_=cache.get(catalog,chunks,fake_provider)
    assert state=="miss" and fake_provider.document_calls==2*calls


def test_source_change_invalidates_cache(catalog,fake_provider,tmp_path):
    cache=EmbeddingCache(tmp_path)
    cache.get(catalog,build_evidence(catalog),fake_provider)
    changed=catalog.model_copy(deep=True)
    changed.records[0].summary+=" Revised source information."
    _,state,_=cache.get(changed,build_evidence(changed),fake_provider)
    assert state=="miss"


def test_corrupt_cache_rebuilds(catalog,fake_provider,tmp_path):
    cache=EmbeddingCache(tmp_path)
    cache.get(catalog,build_evidence(catalog),fake_provider)
    next(tmp_path.glob("*.npz")).write_bytes(b"invalid")
    _,state,_=cache.get(catalog,build_evidence(catalog),fake_provider)
    assert state=="rebuilt_invalid"


def test_profile_roundtrip():
    profile=StudentProfile(career_id="embedded",programming_background="experienced",completed=parse_completions("ECE 101:B, CSC120"))
    assert import_profile(export_profile(profile).encode())==profile


def test_reject_duplicate_or_executable_profile():
    with pytest.raises(ValueError):
        parse_completions("ECE101, ECE 101")
    with pytest.raises(ValueError):
        import_profile(b"__import__('os').system('echo bad')")
    with pytest.raises(ValueError):
        import_profile(b"x"*100001)


def test_job_adapter_normalizes_and_deduplicates():
    seen=[]
    listing={"id":"1","title":"Embedded Intern","company":{"display_name":"Example"},
             "location":{"display_name":"Tucson"},"redirect_url":"https://example.com/job/1",
             "created":"2026-10-22","description":"A provider snippet"}
    def open_fixture(request,timeout):
        seen.append(request.full_url)
        malformed={**listing,"id":"invalid","company":["unexpected"]}
        return io.BytesIO(json.dumps({"results":[listing,listing,malformed]}).encode())
    result=search_jobs("test-id","test-key","embedded","Tucson",True,opener=open_fixture)
    assert len(result.listings)==1
    assert result.query=="embedded software intern"
    assert result.listings[0]["url"]=="https://example.com/job/1"
    assert result.retrieved_at
    assert "where=Tucson" in seen[0]


def test_job_empty_is_not_error():
    result=search_jobs("id","key","ai_ml","Tucson",opener=lambda *a,**k:io.BytesIO(b'{"results":[]}'))
    assert result.listings==[]


def test_job_credentials_not_leaked_by_failure():
    def fail(*args,**kwargs):
        raise OSError("secret-key")
    with pytest.raises(RuntimeError) as error:
        search_jobs("id","secret-key","ai_ml","Tucson",opener=fail)
    assert "secret-key" not in str(error.value)
