"""Explicitly refresh the published undergraduate ECE inventory; never run in the UI."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from src.course_directory import COURSE_LIST_URL, DEFAULT_DIRECTORY, SEARCH_URL, build_directory
from src.ingest import _active_edition, _nuxt_data


def fetch_directory(client):
    response = client.get(COURSE_LIST_URL)
    response.raise_for_status()
    table, resolve = _nuxt_data(response.text)
    settings = [x for x in table if isinstance(x, dict)
                and {"host", "school", "activeCatalog", "coursesFilters", "effectiveDatesRange"} <= x.keys()]
    if len(settings) != 1:
        raise ValueError("Ambiguous published catalog settings")
    config = settings[0]
    if (resolve(config["host"]) != "catalog.arizona.edu"
            or resolve(config["school"]) != "arizona_peoplesoft"):
        raise ValueError("Unexpected catalog source")
    edition = _active_edition(table, resolve)
    dates = resolve(config["effectiveDatesRange"])
    start = dates["effectiveStartDate"]
    effective_dates = start + "," + (dates["effectiveEndDate"] or start)
    filters = {"condition":"AND", "filters":[resolve(config["coursesFilters"]),
        {"condition":"AND", "filters":[{"id":"subjectCode-course", "condition":"field",
            "name":"subjectCode", "inputType":"subjectCodeSelect", "group":"course", "type":"is", "value":"ECE"}]}]}
    params = dict(catalogId=resolve(config["activeCatalog"]), skip=0, limit=100, orderBy="code",
        formatDependents="false", effectiveDatesRange=effective_dates,
        ignoreEffectiveDating="false", ignoreTotalCount="false")
    pages = []
    for _ in range(10):
        response = client.post(SEARCH_URL, params=params, json=filters)
        response.raise_for_status()
        if len(response.content) > 5_000_000:
            raise ValueError("Course search response exceeds its budget")
        page = response.json()
        pages.append(page)
        if not page["data"] or page["listLength"] > 1000:
            raise ValueError("Empty or excessive published course inventory")
        params["skip"] += len(page["data"])
        if params["skip"] >= page["listLength"]:
            break
    return build_directory(pages, catalog_version=edition, catalog_id=params["catalogId"],
        effective_dates=effective_dates, retrieved_at=datetime.now(timezone.utc), filters=filters)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_DIRECTORY)
    args = parser.parse_args()
    with httpx.Client(timeout=35, follow_redirects=False,
            headers={"X-Requested-With":"catalog", "Origin":"https://catalog.arizona.edu"}) as client:
        directory = fetch_directory(client)
    # Validate everything before replacing the previous snapshot.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".tmp")
    temporary.write_text(directory.model_dump_json(indent=2)+"\n", encoding="utf-8")
    temporary.replace(args.output)
    print(json.dumps({"catalog":directory.catalog_version, "undergraduate_ece_courses":len(directory.courses),
                      "published_ece_total":directory.published_ece_total, "pages":len(directory.pages)}))


if __name__ == "__main__":
    main()
