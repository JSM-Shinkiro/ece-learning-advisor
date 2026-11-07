"""Concurrent public document reuse; provider/source requests are controlled."""

from concurrent.futures import ThreadPoolExecutor
import gc
import hashlib
import json
from pathlib import Path
import threading
import time

import numpy as np
import pytest

from src import providers
from src.catalog import build_evidence, load_runtime_catalog
from src.controller import run_advisor
from src.models import Completion, ExplanationSelection, SelectedRecommendation, StudentProfile
from src.providers import EmbeddingCache, ProviderError
from src.sources import CatalogRefresh


class Calls:
    def __init__(self):
        self.guard = threading.Lock()
        self.documents, self.queries, self.contexts, self.closed = [], [], [], []

    def add(self, name, value):
        with self.guard:
            getattr(self, name).append(value)


class ControlledProvider:
    def __init__(self, calls, *, model="gemini-concurrency-fixture", dimensions=7, first=None):
        self.calls, self.first = calls, first
        self.embedding_model, self.dimensions = model, dimensions
        self.generation_model = "gemini-concurrency-generator"

    def embed_document(self, chunk):
        self.calls.add("documents", (self.embedding_model, self.dimensions, chunk.record_id, chunk.text))
        if self.first:
            callback, self.first = self.first, None
            callback()
        seed = hashlib.sha256(chunk.text.encode()).digest()
        return np.array([seed[i % len(seed)] + 1.0 for i in range(self.dimensions)])

    def embed_query(self, query):
        self.calls.add("queries", query)
        return np.arange(1, self.dimensions + 1, dtype=float)

    def generate(self, context):
        self.calls.add("contexts", context)
        return ExplanationSelection(status="answered", recommendations=[SelectedRecommendation(
            record_id=rid, statement_ids=[next(s.statement_id for s in context.allowed_statements if s.record_id == rid)])
            for rid in context.allowed_record_ids])

    def close(self):
        self.calls.add("closed", self)


def contention_gate(monkeypatch):
    """Keep the owner in its first embedding until a real lock contender arrives."""
    entered, contended = threading.Event(), threading.Event()
    original = providers._cache_lock_for

    def observed(path):
        lock = original(path)
        if lock.locked():
            contended.set()
        return lock

    monkeypatch.setattr(providers, "_cache_lock_for", observed)

    def first():
        entered.set()
        assert contended.wait(5), "A second cache request did not reach the held lock"

    return entered, first


@pytest.mark.parametrize("shared_instance", [False, True])
def test_simultaneous_cold_requests_build_one_index(tmp_path, monkeypatch, shared_instance):
    catalog = load_runtime_catalog()
    chunks, calls = build_evidence(catalog), Calls()
    entered, first = contention_gate(monkeypatch)
    owner = ControlledProvider(calls, first=first)
    waiter = ControlledProvider(calls)
    cache = EmbeddingCache(tmp_path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        initial = pool.submit(cache.get, catalog, chunks, owner)
        assert entered.wait(5)
        following = pool.submit((cache if shared_instance else EmbeddingCache(tmp_path)).get, catalog, chunks, waiter)
        results = [initial.result(timeout=10), following.result(timeout=10)]
    assert [result[1] for result in results] == ["miss", "hit"]
    assert len(calls.documents) == len(chunks) == 34
    assert len(set(calls.documents)) == 34
    np.testing.assert_allclose(results[0][0], results[1][0], rtol=1e-14, atol=1e-14)
    assert len(list(tmp_path.glob("*.npz"))) == 1
    assert len(list((tmp_path / "documents").glob("*.npz"))) == 34


def test_overlapping_catalogs_share_unchanged_documents_during_build(tmp_path, monkeypatch):
    original = load_runtime_catalog()
    changed = original.model_copy(deep=True)
    next(r for r in changed.records if r.code == "ECE352").summary += " Updated public description."
    calls = Calls()
    entered, first = contention_gate(monkeypatch)
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(EmbeddingCache(tmp_path).get, original, build_evidence(original), ControlledProvider(calls, first=first))
        assert entered.wait(5)
        b = pool.submit(EmbeddingCache(tmp_path).get, changed, build_evidence(changed), ControlledProvider(calls))
        results = [a.result(timeout=10), b.result(timeout=10)]
    assert all(result[1] == "miss" for result in results)
    assert len(calls.documents) == len(set(calls.documents)) == 35
    assert len(list(tmp_path.glob("*.npz"))) == 2
    assert results[0][2]["corpus_hash"] != results[1][2]["corpus_hash"]


@pytest.mark.parametrize("difference", ["model", "dimensions", "directory"])
def test_independent_cache_identities_build_without_blocking_each_other(tmp_path, difference):
    catalog = load_runtime_catalog()
    calls, barrier = Calls(), threading.Barrier(2)
    a = ControlledProvider(calls, first=lambda: barrier.wait(5))
    b = ControlledProvider(calls, first=lambda: barrier.wait(5),
        model="gemini-other-fixture" if difference == "model" else a.embedding_model,
        dimensions=8 if difference == "dimensions" else a.dimensions)
    other = tmp_path / "other" if difference == "directory" else tmp_path
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(EmbeddingCache(path).get, catalog, build_evidence(catalog), provider)
                   for path, provider in [(tmp_path, a), (other, b)]]
        results = [future.result(timeout=10) for future in futures]
    assert all(result[1] == "miss" for result in results)
    assert len(calls.documents) == 68
    assert results[1][0].shape == (34, b.dimensions)


@pytest.mark.parametrize("failure", ["provider", "invalid_vector", "interrupted"])
def test_owner_failure_releases_both_locks_for_the_waiter(tmp_path, monkeypatch, failure):
    catalog, calls = load_runtime_catalog(), Calls()
    entered, first = contention_gate(monkeypatch)

    class Broken(ControlledProvider):
        def embed_document(self, chunk):
            super().embed_document(chunk)
            if failure == "provider":
                raise ProviderError("controlled provider failure")
            if failure == "interrupted":
                raise KeyboardInterrupt()
            return [1, 2]

    with ThreadPoolExecutor(max_workers=2) as pool:
        owner = pool.submit(EmbeddingCache(tmp_path).get, catalog, build_evidence(catalog), Broken(calls, first=first))
        assert entered.wait(5)
        waiter = pool.submit(EmbeddingCache(tmp_path).get, catalog, build_evidence(catalog), ControlledProvider(calls))
        with pytest.raises(KeyboardInterrupt if failure == "interrupted" else ProviderError):
            owner.result(timeout=10)
        result = waiter.result(timeout=10)
    assert result[1] == "miss" and result[0].shape == (34, 7)
    assert len(calls.documents) == 35  # One failed owner call, 34 successful waiter calls.
    assert EmbeddingCache(tmp_path).get(catalog, build_evidence(catalog), ControlledProvider(calls))[1] == "hit"
    assert len(calls.documents) == 35


def test_simultaneous_invalid_index_rebuild_reuses_documents_once(tmp_path, monkeypatch):
    catalog, calls = load_runtime_catalog(), Calls()
    cache = EmbeddingCache(tmp_path)
    cache.get(catalog, build_evidence(catalog), ControlledProvider(calls))
    next(tmp_path.glob("*.npz")).write_bytes(b"invalid index")
    calls.documents.clear()
    entered, first = contention_gate(monkeypatch)
    original_write, index_writes = EmbeddingCache._write, []

    def write(path, vectors, manifest):
        if path.parent == tmp_path:
            index_writes.append(path)
            first()
        original_write(path, vectors, manifest)

    monkeypatch.setattr(EmbeddingCache, "_write", staticmethod(write))
    with ThreadPoolExecutor(max_workers=2) as pool:
        owner = pool.submit(cache.get, catalog, build_evidence(catalog), ControlledProvider(calls))
        assert entered.wait(5)
        waiter = pool.submit(EmbeddingCache(tmp_path).get, catalog, build_evidence(catalog), ControlledProvider(calls))
        results = [owner.result(timeout=10), waiter.result(timeout=10)]
    assert [result[1] for result in results] == ["rebuilt_invalid", "hit"]
    assert not calls.documents and len(index_writes) == 1


@pytest.mark.parametrize("busy_kind", ["index", "document"])
def test_busy_cache_uses_existing_controller_fallback_without_duplicate_embedding(tmp_path, monkeypatch, busy_kind):
    catalog, calls = load_runtime_catalog(), Calls()
    EmbeddingCache(tmp_path).get(catalog, build_evidence(catalog), ControlledProvider(calls))
    if busy_kind == "index":
        path = next(tmp_path.glob("*.npz"))
    else:
        path = None
        for candidate in (tmp_path / "documents").glob("*.npz"):
            with np.load(candidate, allow_pickle=False) as archive:
                if json.loads(str(archive["manifest"].item()))["record_id"] == "uofa:ECE101:2026-2027":
                    path = candidate
                    break
        assert path is not None
        # Different index, same public documents: the document wait is bounded too.
        next(r for r in catalog.records if r.code == "ECE352").summary += " Updated public description."
    lock = providers._cache_lock_for(path)
    monkeypatch.setattr(providers, "_CACHE_WAIT_SECONDS", 0.0)
    before = len(calls.documents)
    lock.acquire()
    try:
        result = run_advisor(catalog, StudentProfile(question="ECE101 programming"), api_key="fixture-key",
            use_ai=True, method="semantic", refresh_sources=False, cache_dir=tmp_path,
            provider_factory=lambda *a, **k: ControlledProvider(calls))
    finally:
        lock.release()
    assert result.retrieval_mode == "keyword" and result.generation_complete
    assert result.statement_validation_passed and result.context.allowed_record_ids
    assert len(calls.documents) == before and not calls.queries
    assert len(calls.contexts) == len(calls.closed) == 1
    assert "Semantic retrieval is unavailable" in " ".join(result.issues)
    assert str(path) not in json.dumps(result.trace)


def test_cache_waits_share_one_deadline_and_release_acquired_locks(tmp_path, monkeypatch):
    timeouts, releases = [], []

    class SpyLock:
        def acquire(self, *, timeout):
            timeouts.append(timeout)
            return True

        def release(self):
            releases.append(True)

    clock = iter([100.0, 111.0, 140.0])
    monkeypatch.setattr(providers.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(providers, "_cache_lock_for", lambda path: SpyLock())
    for name in ["index", "first-document", "second-document"]:
        with providers._cache_build_lock(tmp_path / name, deadline=130.0):
            pass
    assert timeouts == [30.0, 19.0, 0.0] and len(releases) == 3


def test_write_failure_status_is_local_to_each_concurrent_get(tmp_path, monkeypatch):
    catalog, calls = load_runtime_catalog(), Calls()
    entered, bad_done = threading.Event(), threading.Event()
    cache, write = EmbeddingCache(tmp_path), EmbeddingCache._write

    def good_first():
        entered.set()
        assert bad_done.wait(5)

    def sometimes_write(path, vectors, manifest):
        if manifest["model"] == "gemini-uncached-fixture":
            raise OSError("controlled write failure")
        write(path, vectors, manifest)

    monkeypatch.setattr(EmbeddingCache, "_write", staticmethod(sometimes_write))
    with ThreadPoolExecutor(max_workers=2) as pool:
        good = pool.submit(cache.get, catalog, build_evidence(catalog), ControlledProvider(calls, first=good_first))
        assert entered.wait(5)
        bad = pool.submit(cache.get, catalog, build_evidence(catalog), ControlledProvider(calls, model="gemini-uncached-fixture"))
        try:
            bad_result = bad.result(timeout=10)
        finally:
            bad_done.set()
        good_result = good.result(timeout=10)
    assert bad_result[1] == "miss_uncached" and good_result[1] == "miss"
    assert len(calls.documents) == 68


def test_controller_requests_share_only_documents_and_keep_profiles_queries_answers_separate(tmp_path, monkeypatch):
    monkeypatch.setattr("httpx.Client.send", lambda *a, **k: pytest.fail("No actual network requests"))
    catalog, calls = load_runtime_catalog(), Calls()
    profiles = [StudentProfile(career_id="embedded", programming_background="experienced",
        question="How can ECE352 help me study hardware?", completed=completed)
        for completed in [[], [Completion(course_code="ECE101", grade="B")]]]
    entered, first = contention_gate(monkeypatch)
    source_profiles = []

    def source_refresh(catalog, profile, **kwargs):
        source_profiles.append(profile.model_dump())
        return CatalogRefresh(catalog=catalog.model_copy(deep=True))

    def request(index):
        return run_advisor(catalog, profiles[index], api_key="fixture-private-key-" + str(index), use_ai=True,
            method="semantic", dimensions=7, cache_dir=tmp_path,
            provider_factory=lambda *a, **k: ControlledProvider(calls, first=first if index == 0 else None),
            source_refresher=source_refresh)

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(request, 0)
        assert entered.wait(5)
        b = pool.submit(request, 1)
        results = [a.result(timeout=10), b.result(timeout=10)]
    assert len(calls.documents) == 34 and len(calls.queries) == len(calls.contexts) == len(calls.closed) == 2
    assert calls.queries[0] == calls.queries[1]  # Even identical query embeddings are request-local.
    assert len(source_profiles) == 2 and all(r.trace["source_refresh"]["enabled"] for r in results)
    assert all(r.generation_complete and r.statement_validation_passed and r.retrieval_mode == "semantic" for r in results)
    assert results[0].context.profile == profiles[0] and results[1].context.profile == profiles[1]
    assert results[0].answer is not results[1].answer and results[0].context is not results[1].context
    assert "uofa:ECE101:2026-2027" not in results[1].context.allowed_record_ids
    for path in tmp_path.rglob("*.npz"):
        with np.load(path, allow_pickle=False) as archive:
            assert set(archive.files) == {"manifest", "vectors"}
            manifest = json.loads(str(archive["manifest"].item()))
        assert not {"profile", "query", "answer", "api_key", "generation_model"}.intersection(manifest)
        assert "fixture-private-key" not in json.dumps(manifest) and profiles[0].question not in json.dumps(manifest)


def test_idle_registry_entries_are_reclaimed_and_path_aliases_share_active_lock(tmp_path):
    path = tmp_path / "cache.npz"
    alias = tmp_path / "nonexistent" / ".." / "cache.npz"
    lock = providers._cache_lock_for(path)
    assert providers._cache_lock_for(alias) is lock
    reference = str(path.resolve())
    assert reference in providers._CACHE_LOCKS
    del lock
    gc.collect()
    assert reference not in providers._CACHE_LOCKS
    for i in range(50):
        with providers._cache_build_lock(tmp_path / str(i), time.monotonic() + 1):
            pass
    gc.collect()
    assert not any(str((tmp_path / str(i)).resolve()) in providers._CACHE_LOCKS for i in range(50))


def test_unresolvable_lock_path_has_a_sanitized_error(monkeypatch):
    def broken(self):
        raise OSError("fixture-private-path-diagnostic")

    monkeypatch.setattr(Path, "resolve", broken)
    with pytest.raises(ProviderError) as error:
        providers._cache_lock_for(Path("unused"))
    assert "fixture-private-path-diagnostic" not in str(error.value)
