"""All-method review scoring, exact embedding bindings, and explicit-call boundaries."""

from datetime import datetime, timedelta, timezone
import json

import pytest

from src.providers import EmbeddingCache
from src.review import (MAX_VECTOR_BYTES, blank_form, fingerprint, load_review_json, make_packet, score_review)
from src.review_vectors import ReviewVectors, make_vectors, validate_vectors, vector_hash
from test_review import NOW, fixture_form


@pytest.fixture
def inputs(catalog, fake_provider, tmp_path):
    packet = make_packet(catalog, now=NOW)
    form = fixture_form(packet, catalog)
    cache = EmbeddingCache(tmp_path / "embeddings")
    vectors = make_vectors(catalog, packet, fake_provider, cache, now=NOW + timedelta(seconds=1))
    return packet, form, vectors, cache


def offline(monkeypatch):
    def forbidden(*a, **k): pytest.fail("Offline scoring must not create providers or make HTTP calls")
    monkeypatch.setattr("httpx.Client.send", forbidden)
    monkeypatch.setattr("src.providers.GeminiProvider", forbidden)


@pytest.mark.parametrize("mode", ["raw", "expanded"])
@pytest.mark.parametrize("method", ["keyword", "semantic", "hybrid"])
def test_same_completed_judgments_score_all_methods_without_provider_calls(catalog, inputs, fake_provider, monkeypatch, mode, method):
    packet, form, raw, cache = inputs
    vectors = make_vectors(catalog, packet, fake_provider, cache, query_mode=mode)
    before = fingerprint(form)
    offline(monkeypatch)
    report = score_review(catalog, packet, form, method=method, query_mode=mode,
        embeddings=None if method == "keyword" else vectors)
    assert report["schema_version"] == 2 and report["method"] == method and report["review_hash"] == before == fingerprint(form)
    assert report["embedding_calls"] == report["generation_calls"] == report["source_refresh_calls"] == 0
    assert report["summary"]["cases"] == 16 and report["question_origin"] == "existing_development_questions"
    assert report["reviewer"]["self_reported_role"] == "controlled_fixture"
    if method == "keyword":
        assert report["embedding_snapshot"] is None
        assert report["summary"]["recall"] == pytest.approx(.8229166666666666 if mode == "raw" else .9479166666666666)
    else:
        assert report["embedding_snapshot"]["snapshot_hash"] == vectors.snapshot_hash
        assert "document_vectors" not in report["embedding_snapshot"] and "questions" not in report["embedding_snapshot"]
        assert all(row["component_scores"][0]["cosine"] is not None for row in report["cases"])
        assert all(len(row["ranked_chunk_ids"]) == len(packet.evidence) for row in report["cases"])
        assert "not authenticated" in report["limitations"]


def test_snapshot_creation_accepts_no_grades_reuses_document_cache_and_preserves_packet(catalog, inputs, fake_provider):
    packet, form, vectors, cache = inputs
    before = packet.packet_hash
    assert vectors.document_embedding_calls == 10 and vectors.query_embedding_calls == 16
    again = make_vectors(catalog, packet, fake_provider, cache, query_mode="expanded")
    assert again.document_embedding_calls == 0 and again.query_embedding_calls == 16 and again.cache_state == "hit"
    assert again.chunk_ids == vectors.chunk_ids and again.document_vectors == vectors.document_vectors
    assert any(a.effective_query != b.effective_query for a, b in zip(again.questions, vectors.questions))
    assert packet.packet_hash == before
    for key in ['"relevance"', '"reviewer_id"', '"scores"', '"ranked_chunk_ids"', '"allowed_statements"']:
        assert key not in vectors.model_dump_json()
    loaded = ReviewVectors.model_validate_json(vectors.model_dump_json())
    assert validate_vectors(loaded, catalog, packet, "raw") == vectors


@pytest.mark.parametrize("method", ["semantic", "hybrid"])
def test_each_question_uses_its_own_vector_with_analytic_unit_basis_rankings(catalog, fake_provider, tmp_path, method):
    import numpy as np
    packet = make_packet(catalog, questions=[{"case_id": "a", "query": "zzzoovectoralpha"},
        {"case_id": "b", "query": "zzzoovectorbeta"}], now=NOW)
    vectors = make_vectors(catalog, packet, fake_provider, EmbeddingCache(tmp_path / "cache"))
    count = len(packet.evidence)
    vectors.dimensions, vectors.document_vectors = count, np.eye(count).tolist()
    form = blank_form(packet)
    form.reviewer_id, form.reviewer_role = "unit-basis-fixture", "controlled_fixture"
    form.reviewed_at = NOW + timedelta(minutes=1)
    for index, question in enumerate(vectors.questions):
        question.vector = np.eye(count)[index].tolist()
        form.cases[index].relevance = {key: 3 if key == vectors.chunk_ids[index] else 0 for key in vectors.chunk_ids}
    vectors.snapshot_hash = vector_hash(vectors)
    report = score_review(catalog, packet, form, method=method, embeddings=vectors, k=1)
    assert [row["ranked_chunk_ids"][0] for row in report["cases"]] == vectors.chunk_ids[:2]
    assert report["summary"]["precision"] == report["summary"]["recall"] == 1.0
    for row in report["cases"]:
        assert row["component_scores"][0]["cosine"] == pytest.approx(1.0)
        assert row["scores"][0] == pytest.approx(1.0 if method == "semantic" else 1 / 61)


@pytest.mark.parametrize("mutation", ["zero", "dimension", "nan", "infinity", "bool", "string", "overflow",
    "missing_row", "duplicate_chunk", "duplicate_question"])
def test_invalid_vectors_are_rejected_before_ranking(catalog, inputs, mutation):
    packet, form, vectors, _ = inputs
    data = vectors.model_dump()
    if mutation == "zero": data["document_vectors"][0] = [0.0] * vectors.dimensions
    elif mutation == "dimension": data["questions"][0]["vector"].pop()
    elif mutation in {"nan", "infinity", "bool", "string", "overflow"}:
        data["document_vectors"][0][0] = {"nan": float("nan"), "infinity": float("inf"), "bool": True, "string": "1", "overflow": 1e308}[mutation]
    elif mutation == "missing_row": data["document_vectors"].pop()
    elif mutation == "duplicate_chunk": data["chunk_ids"][0] = data["chunk_ids"][1]
    else: data["questions"][0]["case_id"] = data["questions"][1]["case_id"]
    with pytest.raises(ValueError): ReviewVectors.model_validate(data)


def test_fingerprint_rejects_modified_vector_even_when_dimensions_are_still_valid(catalog, inputs):
    packet, _, vectors, _ = inputs
    vectors.document_vectors[0][0] += .01
    with pytest.raises(ValueError, match="fingerprint"): validate_vectors(vectors, catalog, packet, "raw")


@pytest.mark.parametrize("mutation", ["packet", "corpus", "catalog", "query_policy", "query_mode", "chunk_order",
    "text_hash", "query_text", "query_order", "timestamp"])
def test_rehashing_cannot_bypass_exact_input_bindings(catalog, inputs, mutation):
    packet, _, vectors, _ = inputs
    data = vectors.model_dump(mode="json")
    if mutation in {"packet", "corpus", "catalog"}:
        data[{"packet": "packet_hash", "corpus": "corpus_hash", "catalog": "catalog_snapshot_hash"}[mutation]] = "f" * 64
    elif mutation == "query_policy": data["query_policy"] = "other-policy"
    elif mutation == "query_mode": data["query_mode"] = "expanded"
    elif mutation == "chunk_order":
        for key in ["chunk_ids", "chunk_text_hashes", "document_vectors"]: data[key].reverse()
    elif mutation == "text_hash": data["chunk_text_hashes"][0] = "f" * 64
    elif mutation == "query_text": data["questions"][0]["effective_query"] = "Unrelated effective query"
    elif mutation == "query_order": data["questions"].reverse()
    else: data["created_at"] = (NOW - timedelta(seconds=1)).isoformat()
    data["snapshot_hash"] = vector_hash(data)
    with pytest.raises(ValueError): validate_vectors(ReviewVectors.model_validate(data), catalog, packet, "raw")


def test_model_name_and_vector_origin_are_explicitly_unverified(catalog, inputs):
    packet, form, vectors, _ = inputs
    vectors.embedding_model = "operator-reported-model"
    vectors.snapshot_hash = vector_hash(vectors)
    report = score_review(catalog, packet, form, method="semantic", embeddings=vectors)
    assert report["embedding_snapshot"]["vector_provenance"] == "operator_supplied_unverified"
    assert "model identity are not authenticated" in report["limitations"]


@pytest.mark.parametrize("method,with_vectors", [("semantic", False), ("hybrid", False), ("keyword", True), ("unknown", False)])
def test_missing_or_unused_embedding_snapshot_does_not_silently_change_methods(catalog, inputs, method, with_vectors):
    packet, form, vectors, _ = inputs
    with pytest.raises(ValueError): score_review(catalog, packet, form, method=method, embeddings=vectors if with_vectors else None)


def test_incomplete_grades_fail_before_embedding_validation(catalog, inputs, monkeypatch):
    packet, _, vectors, _ = inputs
    monkeypatch.setattr("src.review_vectors.validate_vectors", lambda *a: pytest.fail("Incomplete review must stop first"))
    with pytest.raises(ValueError): score_review(catalog, packet, blank_form(packet), method="semantic", embeddings=vectors)


def test_stale_catalog_metadata_invalidates_vectors_even_when_corpus_text_is_unchanged(catalog, inputs):
    packet, _, vectors, _ = inputs
    catalog.sources[0].last_checked_at = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="snapshot"): validate_vectors(vectors, catalog, packet, "raw")


@pytest.mark.parametrize("method", ["semantic", "hybrid"])
def test_all_zero_judgments_preserve_undefined_metric_counts(catalog, inputs, method):
    packet, form, vectors, _ = inputs
    for case in form.cases: case.relevance = {key: 0 for key in case.relevance}
    report = score_review(catalog, packet, form, method=method, embeddings=vectors)
    assert report["summary"]["precision"] == 0 and report["summary"]["recall"] is None
    assert report["summary"]["defined_cases"]["recall"] == 0 and report["summary"]["queries_without_relevant_evidence"] == 16


def test_embedding_creation_rejects_invalid_packet_before_any_provider_call(catalog, inputs, fake_provider, monkeypatch):
    packet, _, _, cache = inputs
    packet.questions[0].query = "Changed"
    monkeypatch.setattr(fake_provider, "embed_query", lambda *a: pytest.fail("Invalid inputs must not be uploaded"))
    with pytest.raises(ValueError): make_vectors(catalog, packet, fake_provider, cache)


def test_vector_file_size_bound_and_duplicate_key_rejection_are_preserved(tmp_path):
    path = tmp_path / "input.json"
    path.write_text(' ' * 2_000_001 + '{}')
    with pytest.raises(ValueError): load_review_json(path)
    assert load_review_json(path, max_bytes=MAX_VECTOR_BYTES) == {}
    path.write_text('{"vectors":[],"vectors":[]}')
    with pytest.raises(ValueError): load_review_json(path, max_bytes=MAX_VECTOR_BYTES)


@pytest.mark.parametrize("size", [True, -1, MAX_VECTOR_BYTES + 1])
def test_invalid_read_limit_fails_before_opening_a_file(tmp_path, size):
    with pytest.raises(ValueError): load_review_json(tmp_path / "missing", max_bytes=size)


def test_cli_embedding_creation_requires_explicit_flag_and_never_overwrites(monkeypatch, tmp_path, catalog, fake_provider):
    from scripts import review_retrieval as cli
    packet = make_packet(catalog)
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(packet.model_dump_json())
    output = tmp_path / "vectors.json"
    argv = ["review", "embed", "--packet", str(packet_path), "--output", str(output)]
    monkeypatch.setattr("sys.argv", argv)
    monkeypatch.setattr(cli, "GeminiProvider", lambda *a, **k: pytest.fail("No implicit provider calls"))
    with pytest.raises(SystemExit) as result: cli.main()
    assert result.value.code == 2 and not output.exists()
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    monkeypatch.setenv("GEMINI_API_KEY", "fixture-private-key")
    monkeypatch.setenv("ECE_CACHE_DIR", str(tmp_path / "cache"))
    closed = []
    fake_provider.close = lambda: closed.append(1)
    monkeypatch.setattr(cli, "GeminiProvider", lambda *a, **k: fake_provider)
    monkeypatch.setattr("sys.argv", argv + ["--live-embeddings"])
    assert cli.main() == 0 and closed == [1]
    saved = output.read_bytes()
    assert b"fixture-private-key" not in saved
    monkeypatch.setattr(cli, "GeminiProvider", lambda *a, **k: pytest.fail("Existing output must fail before API use"))
    assert cli.main() == 2 and output.read_bytes() == saved


def test_cli_all_methods_score_the_same_form_offline_and_keep_outputs(monkeypatch, tmp_path, catalog, inputs):
    from scripts import review_retrieval as cli
    packet, form, vectors, _ = inputs
    paths = {name: tmp_path / (name + ".json") for name in ["packet", "form", "vectors"]}
    for name, model in [("packet", packet), ("form", form), ("vectors", vectors)]: paths[name].write_text(model.model_dump_json())
    offline(monkeypatch)
    monkeypatch.setattr(cli, "GeminiProvider", lambda *a, **k: pytest.fail("Scoring must remain offline"))
    reports = []
    for method in ["keyword", "semantic", "hybrid"]:
        output = tmp_path / (method + ".json")
        argv = ["review", "score", "--packet", str(paths["packet"]), "--review", str(paths["form"]),
            "--method", method, "--output", str(output)]
        if method != "keyword": argv += ["--embeddings", str(paths["vectors"])]
        monkeypatch.setattr("sys.argv", argv)
        assert cli.main() == 0
        before = output.read_bytes()
        assert cli.main() == 2 and output.read_bytes() == before
        reports.append(json.loads(before))
    assert len({r["review_hash"] for r in reports}) == 1
    assert all(r["embedding_calls"] == r["generation_calls"] == r["source_refresh_calls"] == 0 for r in reports)


def test_failed_embedding_creation_closes_provider_and_sanitizes_errors_without_an_output(monkeypatch, tmp_path, catalog, fake_provider, capsys):
    from scripts import review_retrieval as cli
    packet_path, output = tmp_path / "packet.json", tmp_path / "vectors.json"
    packet_path.write_text(make_packet(catalog).model_dump_json())
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    monkeypatch.setenv("GEMINI_API_KEY", "fixture-private-key")
    monkeypatch.setenv("ECE_CACHE_DIR", str(tmp_path / "cache"))
    closed = []
    fake_provider.close = lambda: closed.append(1)
    def fail(*a): raise RuntimeError("private-provider-diagnostic")
    fake_provider.embed_query = fail
    monkeypatch.setattr(cli, "GeminiProvider", lambda *a, **k: fake_provider)
    monkeypatch.setattr("sys.argv", ["review", "embed", "--packet", str(packet_path), "--output", str(output), "--live-embeddings"])
    assert cli.main() == 2 and closed == [1] and not output.exists()
    assert "private-provider-diagnostic" not in capsys.readouterr().err
