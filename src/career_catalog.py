"""Add career coverage alongside the versioned development corpus."""

from functools import lru_cache

from .career_paths import CAREER_PATHS, EXPANDED_DIRECTIONS
from .catalog import ROOT, load_catalog
from .models import Catalog

CAREER_CATALOG = "data/reviewed/career_paths_2026_2027.json"


@lru_cache(maxsize=4)
def load_career_catalog(root=ROOT):
    return load_catalog(root / CAREER_CATALOG)


def with_career_paths(catalog, directions=EXPANDED_DIRECTIONS, *, root=ROOT):
    directions = tuple(direction for direction in directions if direction in EXPANDED_DIRECTIONS)
    if not directions:
        return catalog
    supplement = load_career_catalog(root)
    if catalog.catalog_version != supplement.catalog_version:
        return catalog

    records = {record.record_id: record for record in catalog.records}
    sources = {source.source_id: source for source in catalog.sources}
    supplement_sources = {source.source_id: source for source in supplement.sources}
    for direction in directions:
        path = CAREER_PATHS[direction]
        mapped_codes = (*path.progression, *path.related_courses, *path.electives)
        for record in list(records.values()):
            if record.code in mapped_codes and direction not in record.career_ids:
                records[record.record_id] = record.model_copy(update={"career_ids": [*record.career_ids, direction]})
        for addition in supplement.records:
            if direction not in addition.career_ids:
                continue
            previous = records.get(addition.record_id)
            if previous is None or previous.study_stage == "unreviewed":
                records[addition.record_id] = addition
            for sid in addition.source_ids:
                sources.setdefault(sid, supplement_sources[sid])

    versions = catalog.version.split("+")
    if supplement.version not in versions:
        versions.append(supplement.version)
    return Catalog(version="+".join(versions), catalog_version=catalog.catalog_version,
                   records=list(records.values()), sources=list(sources.values()))
