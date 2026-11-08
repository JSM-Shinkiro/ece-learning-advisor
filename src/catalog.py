"""Reviewed, versioned collection and evidence construction."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import Field

from .models import Catalog, Evidence, Record, Source, StrictModel

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "data" / "reviewed" / "catalog.json"


class RuntimeExtension(StrictModel):
    version: str = Field(min_length=1, max_length=100)
    baseline_corpus_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    catalog_version: str
    sources: list[Source] = Field(max_length=40)
    records: list[Record] = Field(max_length=40)


def load_catalog(path: Path = DEFAULT_CATALOG) -> Catalog:
    catalog = Catalog.model_validate_json(path.read_text(encoding="utf-8"))
    if any(r.review_status == "synthetic_fixture" for r in catalog.records):
        raise ValueError("Synthetic fixtures cannot be loaded as the live catalog")
    return catalog


def load_runtime_catalog(root: Path = ROOT) -> Catalog:
    """Add reviewed runtime coverage without altering the frozen evaluation input."""
    baseline = load_catalog(Path(root) / "data/reviewed/catalog.json")
    extension = RuntimeExtension.model_validate_json(
        (Path(root) / "data/reviewed/runtime_extension.json").read_text(encoding="utf-8"))
    if (extension.catalog_version != baseline.catalog_version
            or extension.baseline_corpus_hash != corpus_hash(baseline)):
        raise ValueError("Runtime coverage does not match the frozen baseline")
    if ({s.source_id for s in baseline.sources} & {s.source_id for s in extension.sources}
            or {r.record_id for r in baseline.records} & {r.record_id for r in extension.records}
            or {s.url for s in baseline.sources} & {s.url for s in extension.sources}):
        raise ValueError("Runtime coverage must not replace baseline identities")
    catalog = Catalog(version=baseline.version + "+" + extension.version,
        catalog_version=baseline.catalog_version, sources=baseline.sources + extension.sources,
        records=baseline.records + extension.records)
    codes = [(r.code, r.catalog_version) for r in catalog.records if r.kind == "course"]
    if (len(codes) != len(set(codes)) or len({s.url for s in catalog.sources}) != len(catalog.sources)
            or any(r.review_status == "synthetic_fixture" for r in catalog.records)
            or any(r.kind == "course" and r.catalog_version != catalog.catalog_version for r in catalog.records)):
        raise ValueError("Runtime coverage has conflicting courses, editions, sources, or synthetic fixtures")
    return catalog


def corpus_hash(catalog: Catalog) -> str:
    # Successful checks change timestamps, not the text embedded by the retriever.
    # Keep freshness in the generation context/trace instead of the vector identity.
    content = {
        "catalog_version": catalog.catalog_version,
        "evidence": [chunk.model_dump(mode="json") for chunk in build_evidence(catalog)],
        "sources": [{"source_id": s.source_id, "url": s.url, "catalog_version": s.catalog_version}
                    for s in catalog.sources],
    }
    payload = json.dumps(content, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def build_evidence(catalog: Catalog) -> list[Evidence]:
    chunks = []
    for record in catalog.records:
        text = f"{record.code or record.record_id}: {record.title}\n{record.summary}"
        if record.kind == "course":
            credits = record.credits if record.credits is not None else "Variable or unrecorded; consult the official source"
            text += f"\nCredits: {credits}. Catalog: {record.catalog_version}."
            text += "\nAcademic rule: " + (
                "Use the separate prerequisite-source evidence and application rule results." if record.rule_evidence else
                record.rule.model_dump_json() if record.rule_reviewed
                else "Unresolved. Do not infer enrollment eligibility."
            )
            if record.requirement_reference:
                text += f" Enrollment requirement reference: {record.requirement_reference}."
        if record.kind == "resource":
            if record.resource_version:
                text += f"\nResource edition/version: {record.resource_version}."
            text += "\nComplementary learning resource; this does not establish university credit or course equivalency."
        if record.review_status == "team_mapping":
            text += "\nThis is a team-authored learning connection, not a university requirement."
        if record.learning_note:
            text += "\nTeam learning suggestion (not an academic requirement): " + record.learning_note
        if record.first_activity:
            text += "\nSuggested first activity: " + record.first_activity
        rule_sources = {p.source_id for p in record.rule_evidence}
        if record.discovery:
            rule_sources.add(record.discovery.source_id)
        description_sources = [sid for sid in record.source_ids if sid not in rule_sources]
        chunks.append(Evidence(
            chunk_id=record.record_id + ":overview",
            record_id=record.record_id,
            source_ids=description_sources or record.source_ids,
            text=text,
        ))
        for proof in record.rule_evidence:
            statement = " ".join((proof.observed_text or proof.reviewed_text).split())
            chunks.append(Evidence(chunk_id=proof.evidence_id, record_id=record.record_id,
                source_ids=[proof.source_id], text=(f"Prerequisite source statement for {record.code}. "
                    f"Catalog: {proof.catalog_version}. Program: {proof.program_code}. Section: {proof.section_id}.\n"
                    + statement + "\nUse only the application rule results to assess recorded prerequisite satisfaction. "
                    "A source statement alone does not establish enrollment eligibility.")))
    return chunks


def code_lookup(catalog: Catalog):
    return {r.code: r for r in catalog.records if r.kind == "course" and r.code}
