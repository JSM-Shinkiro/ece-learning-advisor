"""Expanded review evidence, immutable catalog inputs, and offline CLI boundaries."""

from datetime import datetime, timedelta, timezone
import json

import pytest

from src.catalog import ROOT, build_evidence, corpus_hash, load_catalog, load_runtime_catalog
from src.evaluation import catalog_snapshot_hash
from src.providers import EmbeddingCache
from src.review import (MAX_REVIEW_BYTES, ReviewPacket, blank_form, fingerprint, load_catalog_snapshot,
                        load_review_json, make_packet, packet_hash, packet_markdown, score_review, validate_packet)
from src.review_vectors import make_vectors, validate_vectors
from test_review import fixture_form

NOW = datetime(2026, 11, 6, 20, tzinfo=timezone.utc)
QUESTIONS = ROOT / "data/evaluation/runtime_questions_v1.json"


def controlled_form(packet):
    """Tooling-only zeros, never supplied as human or quality judgments."""
    form = blank_form(packet)
    form.reviewer_id = "runtime-fixture"
    form.reviewer_role = "controlled_fixture"
    form.reviewed_at = packet.created_at + timedelta(minutes=1)
    for case in form.cases:
        case.relevance = {key: 0 for key in case.relevance}
    return form


def offline(monkeypatch):
    def forbidden(*a, **k): pytest.fail("Review preparation/scoring must not use remote services")
    monkeypatch.setattr("httpx.Client.send", forbidden)
    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr("src.providers.GeminiProvider", forbidden)


def test_legacy_packet_hash_and_schema_remain_compatible():
    packet = make_packet(load_catalog(), now=datetime(2026, 11, 5, 23, tzinfo=timezone.utc))
    # Captured before adding runtime support, rather than computed by this test.
    assert packet.packet_hash == "f3290347bdf4d7bb6e0dd1e64b90b50adef09efb4b089dfbe7e96b45ce56b8f2"
    assert packet.schema_version == 1 and len(packet.evidence) == 10


def test_runtime_reuses_only_questions_from_the_original_suite(monkeypatch):
    offline(monkeypatch)
    baseline = make_packet(load_catalog(), now=NOW)
    runtime = make_packet(load_runtime_catalog(), now=NOW)
    assert runtime.source_suite_hash == baseline.source_suite_hash
    assert runtime.question_origin == "existing_development_questions"
    assert [(q.case_id, q.query) for q in runtime.questions] == [(q.case_id, q.query) for q in baseline.questions]
    assert len(runtime.evidence) == 34 and len(runtime.questions) == 16
    assert runtime.corpus_hash != baseline.corpus_hash and runtime.packet_hash != baseline.packet_hash
    form = blank_form(runtime)
    assert sum(len(case.relevance) for case in form.cases) == 544
    assert all(grade is None for case in form.cases for grade in case.relevance.values())
    assert '"relevance"' not in runtime.model_dump_json()
    guide = packet_markdown(runtime)
    assert "16 questions × 34 chunks = 544 grades" in guide and "not held out" in guide
    assert runtime.catalog_snapshot_hash in guide


def test_runtime_question_examples_have_no_grades_or_verified_provenance(monkeypatch):
    def forbidden(*a, **k): pytest.fail("Custom questions must not load previous labels")
    monkeypatch.setattr("src.review.load_suite", forbidden)
    questions = load_review_json(QUESTIONS)
    assert len(questions) == 12 and all(set(q) == {"case_id", "query"} for q in questions)
    packet = make_packet(load_runtime_catalog(), questions=questions, now=NOW)
    assert packet.source_suite_hash is None and packet.question_origin == "custom_questions_unverified"
    assert sum(len(case.relevance) for case in blank_form(packet).cases) == 408
    assert all(grade is None for case in blank_form(packet).cases for grade in case.relevance.values())


def test_original_grades_cannot_be_rebound_or_padded_implicitly():
    baseline, runtime = load_catalog(), load_runtime_catalog()
    old = make_packet(baseline, now=NOW)
    packet = make_packet(runtime, now=NOW)
    form = fixture_form(old, baseline)
    form.reviewed_at = NOW + timedelta(minutes=1)
    with pytest.raises(ValueError, match="different packet"):
        score_review(runtime, packet, form)
    form.packet_hash = packet.packet_hash
    with pytest.raises(ValueError, match="Every evidence chunk"):
        score_review(runtime, packet, form)


@pytest.mark.parametrize("question_change", ["text", "suite_hash", "origin"])
def test_reused_question_provenance_cannot_be_forged(question_change):
    catalog = load_runtime_catalog()
    data = make_packet(catalog, now=NOW).model_dump(mode="json")
    if question_change == "text": data["questions"][0]["query"] = "An unrelated question"
    elif question_change == "suite_hash": data["source_suite_hash"] = "0" * 64
    else: data["question_origin"] = "custom_questions_unverified"
    data["packet_hash"] = packet_hash(data)
    with pytest.raises(ValueError): validate_packet(ReviewPacket.model_validate(data), catalog)


@pytest.mark.parametrize("change", ["summary", "rule", "freshness", "stage", "data_version", "url"])
def test_saved_review_rejects_changes_to_the_bound_catalog(tmp_path, change):
    catalog = load_runtime_catalog()
    packet = make_packet(catalog, now=NOW)
    path = tmp_path / "catalog_snapshot.json"
    path.write_text(catalog.model_dump_json())
    restored = load_catalog_snapshot(path)
    assert validate_packet(packet, restored) == packet
    if change == "summary": restored.records[-1].summary = "Changed saved description"
    elif change == "rule": restored.records[0].rule.note = "Changed rule interpretation"
    elif change == "freshness": restored.sources[0].last_checked_at = NOW
    elif change == "stage": restored.records[0].study_stage = "advanced"
    elif change == "data_version": restored.version += "-changed"
    else: restored.sources[0].url = "https://catalog.arizona.edu/courses/9999999"
    with pytest.raises(ValueError, match="snapshot"):
        validate_packet(packet, restored)


@pytest.mark.parametrize("bad", ["duplicate_key", "oversized", "synthetic", "missing_source", "wrong_schema"])
def test_catalog_snapshot_loader_checks_size_schema_and_provenance(tmp_path, bad):
    catalog = load_runtime_catalog().model_dump(mode="json")
    path = tmp_path / "input.json"
    if bad == "duplicate_key": path.write_text('{"version":"first","version":"second"}')
    elif bad == "oversized": path.write_bytes(b" " * (MAX_REVIEW_BYTES + 1))
    else:
        if bad == "synthetic": catalog["records"][0]["review_status"] = "synthetic_fixture"
        elif bad == "missing_source": catalog["sources"] = []
        else: catalog = {"packet_hash": "0" * 64}
        path.write_text(json.dumps(catalog))
    with pytest.raises(ValueError): load_catalog_snapshot(path)


@pytest.mark.parametrize("mode", ["raw", "expanded"])
@pytest.mark.parametrize("method", ["keyword", "semantic", "hybrid"])
def test_runtime_methods_use_the_same_complete_form_offline(tmp_path, monkeypatch, fake_provider, mode, method):
    offline(monkeypatch)
    catalog = load_runtime_catalog()
    packet = make_packet(catalog, questions=load_review_json(QUESTIONS), now=NOW)
    form = controlled_form(packet)
    before = fingerprint(form)
    vectors = None if method == "keyword" else make_vectors(catalog, packet, fake_provider,
        EmbeddingCache(tmp_path / "vectors"), query_mode=mode, now=NOW + timedelta(seconds=1))
    report = score_review(catalog, packet, form, query_mode=mode, method=method, embeddings=vectors)
    assert report["review_hash"] == before == fingerprint(form)
    assert report["catalog"]["courses"] == 20 and report["catalog"]["resources"] == 8
    assert report["catalog"]["evidence_chunks"] == 34 and report["summary"]["cases"] == 12
    assert report["embedding_calls"] == report["generation_calls"] == report["source_refresh_calls"] == 0
    assert report["reviewer"]["self_reported_role"] == "controlled_fixture"
    assert report["summary"]["queries_without_relevant_evidence"] == 12


def test_baseline_vectors_cannot_supply_the_larger_collection(tmp_path, fake_provider):
    baseline, runtime = load_catalog(), load_runtime_catalog()
    old = make_packet(baseline, now=NOW)
    packet = make_packet(runtime, now=NOW)
    vectors = make_vectors(baseline, old, fake_provider, EmbeddingCache(tmp_path), now=NOW + timedelta(seconds=1))
    with pytest.raises(ValueError, match="do not match"):
        validate_vectors(vectors, runtime, packet, "raw")


@pytest.mark.parametrize("selection,expected", [(None, 10), ("baseline", 10), ("runtime", 34), ("snapshot", 34)])
def test_cli_exports_the_selected_collection_and_matching_catalog(monkeypatch, tmp_path, selection, expected):
    from scripts import review_retrieval as cli
    offline(monkeypatch)
    output = tmp_path / "review"
    argv = ["review", "prepare", "--output", str(output)]
    if selection == "snapshot":
        saved = tmp_path / "catalog.json"
        saved.write_text(load_runtime_catalog().model_dump_json())
        argv += ["--catalog-snapshot", str(saved)]
    elif selection: argv += ["--collection", selection]
    monkeypatch.setattr("sys.argv", argv)
    assert cli.main() == 0
    packet = ReviewPacket.model_validate(load_review_json(output / "packet.json"))
    catalog = load_catalog_snapshot(output / "catalog_snapshot.json")
    assert len(packet.evidence) == expected and validate_packet(packet, catalog) == packet
    assert {p.name for p in output.iterdir()} == {"packet.json", "catalog_snapshot.json", "review_template.json", "review_guide.md"}
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    assert cli.main() == 2
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}


def runtime_bundle(cli, monkeypatch, tmp_path):
    output = tmp_path / "packet"
    monkeypatch.setattr("sys.argv", ["review", "prepare", "--collection", "runtime", "--questions", str(QUESTIONS), "--output", str(output)])
    assert cli.main() == 0
    packet = ReviewPacket.model_validate(load_review_json(output / "packet.json"))
    form = controlled_form(packet)
    form_path = tmp_path / "controlled_form.json"
    form_path.write_text(form.model_dump_json())
    return output, packet, form, form_path


def test_archived_catalog_scores_after_current_catalog_moves_on(monkeypatch, tmp_path):
    from scripts import review_retrieval as cli
    offline(monkeypatch)
    bundle, packet, form, form_path = runtime_bundle(cli, monkeypatch, tmp_path)
    def moved_on(*a, **k): pytest.fail("Explicit archived catalog must not load a current collection")
    monkeypatch.setattr(cli, "load_runtime_catalog", moved_on)
    monkeypatch.setattr(cli, "load_catalog", moved_on)
    report_path = tmp_path / "report.json"
    monkeypatch.setattr("sys.argv", ["review", "score", "--catalog-snapshot", str(bundle / "catalog_snapshot.json"),
        "--packet", str(bundle / "packet.json"), "--review", str(form_path), "--output", str(report_path)])
    assert cli.main() == 0
    report = load_review_json(report_path)
    assert report["catalog_snapshot_hash"] == packet.catalog_snapshot_hash
    assert report["review_hash"] == fingerprint(form)
    assert report["catalog"]["evidence_chunks"] == 34


def test_wrong_collection_and_blank_runtime_form_cannot_create_a_score(monkeypatch, tmp_path):
    from scripts import review_retrieval as cli
    offline(monkeypatch)
    bundle, packet, form, form_path = runtime_bundle(cli, monkeypatch, tmp_path)
    output = tmp_path / "result.json"
    argv = ["review", "score", "--packet", str(bundle / "packet.json"), "--review", str(form_path), "--output", str(output)]
    monkeypatch.setattr("sys.argv", argv)
    assert cli.main() == 2 and not output.exists()  # Default remains baseline.
    argv += ["--collection", "runtime"]
    argv[argv.index("--review") + 1] = str(bundle / "review_template.json")
    assert cli.main() == 2 and not output.exists()


@pytest.mark.parametrize("command", ["prepare", "embed", "score"])
def test_cli_cannot_choose_both_current_and_archived_catalogs(monkeypatch, tmp_path, command):
    from scripts import review_retrieval as cli
    argv = ["review", command, "--collection", "runtime", "--catalog-snapshot", str(tmp_path / "catalog.json"), "--output", str(tmp_path / "out")]
    if command in {"embed", "score"}: argv += ["--packet", str(tmp_path / "packet.json")]
    if command == "score": argv += ["--review", str(tmp_path / "review.json")]
    monkeypatch.setattr("sys.argv", argv)
    with pytest.raises(SystemExit) as error: cli.main()
    assert error.value.code == 2 and not (tmp_path / "out").exists()


def test_runtime_embeddings_still_require_opt_in_and_validate_before_provider(monkeypatch, tmp_path):
    from scripts import review_retrieval as cli
    offline(monkeypatch)
    bundle, packet, form, form_path = runtime_bundle(cli, monkeypatch, tmp_path)
    monkeypatch.setattr(cli, "GeminiProvider", lambda *a, **k: pytest.fail("Invalid selection must fail before provider use"))
    output = tmp_path / "vectors.json"
    argv = ["review", "embed", "--collection", "runtime", "--packet", str(bundle / "packet.json"), "--output", str(output)]
    monkeypatch.setattr("sys.argv", argv)
    with pytest.raises(SystemExit) as error: cli.main()
    assert error.value.code == 2
    # A baseline selection mismatches the runtime packet, even with opt-in.
    argv[argv.index("--collection") + 1] = "baseline"
    monkeypatch.setattr("sys.argv", argv + ["--live-embeddings"])
    assert cli.main() == 2 and not output.exists()


def test_archived_catalog_can_create_vectors_after_repository_data_changes(monkeypatch, tmp_path, fake_provider):
    from scripts import review_retrieval as cli
    offline(monkeypatch)
    bundle, packet, form, form_path = runtime_bundle(cli, monkeypatch, tmp_path)
    def moved_on(*a, **k): pytest.fail("Archived embedding inputs must not reload the current collection")
    monkeypatch.setattr(cli, "load_catalog", moved_on)
    monkeypatch.setattr(cli, "load_runtime_catalog", moved_on)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    monkeypatch.setenv("GEMINI_API_KEY", "fixture-not-in-output")
    monkeypatch.setenv("ECE_CACHE_DIR", str(tmp_path / "cache"))
    closed = []
    fake_provider.close = lambda: closed.append(1)
    fake_provider.generate = lambda *a, **k: pytest.fail("Snapshot creation must not generate answers")
    monkeypatch.setattr(cli, "GeminiProvider", lambda *a, **k: fake_provider)
    output = tmp_path / "vectors.json"
    argv = ["review", "embed", "--catalog-snapshot", str(bundle / "catalog_snapshot.json"),
        "--packet", str(bundle / "packet.json"), "--output", str(output), "--live-embeddings"]
    monkeypatch.setattr("sys.argv", argv)
    assert cli.main() == 0 and closed == [1]
    data = load_review_json(output)
    assert data["packet_hash"] == packet.packet_hash
    assert data["document_embedding_calls"] == 34 and data["query_embedding_calls"] == 12
    assert b"fixture-not-in-output" not in output.read_bytes()
    original = output.read_bytes()
    monkeypatch.setattr(cli, "GeminiProvider", moved_on)
    assert cli.main() == 2 and output.read_bytes() == original


@pytest.mark.parametrize("method", ["keyword", "semantic", "hybrid"])
def test_cli_runtime_scoring_accepts_only_bound_vectors(monkeypatch, tmp_path, fake_provider, method):
    from scripts import review_retrieval as cli
    offline(monkeypatch)
    bundle, packet, form, form_path = runtime_bundle(cli, monkeypatch, tmp_path)
    catalog = load_catalog_snapshot(bundle / "catalog_snapshot.json")
    output = tmp_path / "report.json"
    argv = ["review", "score", "--collection", "runtime", "--packet", str(bundle / "packet.json"),
        "--review", str(form_path), "--method", method, "--output", str(output)]
    if method != "keyword":
        vectors = make_vectors(catalog, packet, fake_provider, EmbeddingCache(tmp_path / "index"))
        path = tmp_path / "vectors.json"
        path.write_text(vectors.model_dump_json())
        argv += ["--embeddings", str(path)]
    monkeypatch.setattr("sys.argv", argv)
    assert cli.main() == 0
    assert load_review_json(output)["catalog"]["evidence_chunks"] == 34
