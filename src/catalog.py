"""Reviewed, versioned collection and evidence construction."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .models import Catalog, Evidence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "data" / "reviewed" / "catalog.json"


def load_catalog(path: Path = DEFAULT_CATALOG) -> Catalog:
    catalog = Catalog.model_validate_json(path.read_text(encoding="utf-8"))
    if any(r.review_status == "synthetic_fixture" for r in catalog.records):
        raise ValueError("Synthetic fixtures cannot be loaded as the live catalog")
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
            text += f"\nCredits: {record.credits}. Catalog: {record.catalog_version}."
            text += "\nAcademic rule: " + (
                "Use the separate prerequisite-source evidence and application rule results." if record.rule_evidence else
                record.rule.model_dump_json() if record.rule_reviewed
                else "Unresolved. Do not infer enrollment eligibility."
            )
            if record.requirement_reference:
                text += f" Enrollment requirement reference: {record.requirement_reference}."
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
