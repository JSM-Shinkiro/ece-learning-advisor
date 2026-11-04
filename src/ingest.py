"""Extract review candidates from public Coursedog catalog page data."""

from __future__ import annotations

import hashlib
import json
import re
from html.parser import HTMLParser


class _DescriptionText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.hidden += 1
        elif tag in {"br", "p", "div", "li"} and not self.hidden:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"}:
            self.hidden = max(0, self.hidden - 1)
        elif tag in {"p", "div", "li"} and not self.hidden:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def description_text(value: str) -> str:
    parser = _DescriptionText()
    parser.feed(value)
    parser.close()
    return " ".join("".join(parser.parts).split())


def _nuxt_data(page: str):
    match = re.search(r'<script[^>]*id=["\']__NUXT_DATA__["\'][^>]*>(.*?)</script>', page, re.S)
    if not match:
        raise ValueError("The catalog page format is not recognized")
    table = json.loads(match.group(1))
    if not isinstance(table, list) or len(table) > 60000:
        raise ValueError("Expected a Nuxt reference table")

    def resolve(index, visited=()):
        if len(visited) > 40:
            raise ValueError("Catalog data is too deeply nested")
        if not isinstance(index, int) or index < 0:
            return None
        if index >= len(table) or index in visited:
            raise ValueError("Invalid or cyclic reference in catalog data")
        value = table[index]
        if isinstance(value, dict):
            return {key: resolve(ref, visited + (index,)) for key, ref in value.items()}
        if isinstance(value, list):
            if value and isinstance(value[0], str):
                if value[0] in {"Reactive", "ShallowReactive", "Ref", "ShallowRef"} and len(value) == 2:
                    return resolve(value[1], visited + (index,))
                raise ValueError("Unsupported catalog wrapper")
            return [resolve(ref, visited + (index,)) for ref in value]
        return value

    return table, resolve


def _active_edition(table, resolve):
    editions = set()
    for value in table:
        if isinstance(value, dict) and {"activeCatalog", "catalogDisplayName"} <= value.keys():
            label = resolve(value["catalogDisplayName"])
            active_id = resolve(value["activeCatalog"])
            if isinstance(label, str) and isinstance(active_id, str) and active_id.strip():
                year = re.search(r"(?<!\d)(20\d{2})\s*[-–]\s*(20\d{2})(?!\d)", label)
                if year and int(year[2]) == int(year[1]) + 1:
                    editions.add(year[1] + "-" + year[2])
    if len(editions) > 1:
        raise ValueError("The active catalog edition is ambiguous")
    return next(iter(editions), None)


def extract_course(page: str) -> dict:
    table, resolve = _nuxt_data(page)
    raw = next((v for v in table if isinstance(v, dict) and
                {"code", "longName", "description", "credits", "requirementGroup"} <= set(v)), None)
    if raw is None:
        raise ValueError("Course metadata is missing")
    fields = {key: resolve(raw[key]) for key in
              ["code", "longName", "description", "credits", "requirementGroup", "effectiveStartDate", "courseGroupId"] if key in raw}
    if not isinstance(fields["description"], str) or len(fields["description"]) > 50000:
        raise ValueError("The course description is invalid")
    if not isinstance(fields["credits"], dict):
        raise ValueError("Course credits are missing")
    return {
        "code": fields["code"],
        "course_id": fields.get("courseGroupId"),
        "title": fields["longName"],
        "credits": fields["credits"].get("creditHours"),
        "requirement_reference": fields["requirementGroup"],
        "effective_start": fields.get("effectiveStartDate"),
        "summary": description_text(fields["description"]),
        "catalog_version": _active_edition(table, resolve),
        "description_hash": hashlib.sha256(fields["description"].encode()).hexdigest(),
        "page_hash": hashlib.sha256(page.encode()).hexdigest(),
        "review_required": True,
    }


def extract_program_statements(page: str, program_code: str, sections: list[str]) -> dict:
    table, resolve = _nuxt_data(page)
    primary = next((v for v in table if isinstance(v, dict) and
                    {"code", "programGroupId", "degreeDesignation", "longName"} <= v.keys()), None)
    if primary is None or resolve(primary["code"]) != program_code or resolve(primary["programGroupId"]) != program_code:
        raise ValueError("The primary program identity does not match")
    statements = {}
    for section in sections:
        matches = set()
        for value in table:
            if not isinstance(value, dict) or not {"id", "name", "description"} <= value.keys():
                continue
            name = resolve(value["name"])
            if isinstance(name, str) and "(" + section + ")" in name:
                text = resolve(value["description"])
                if not isinstance(text, str) or not text.strip() or len(text) > 20000:
                    raise ValueError("The prerequisite source statement is invalid")
                matches.add(description_text(text))
        if len(matches) != 1:
            raise ValueError("The prerequisite source section is missing or ambiguous")
        statements[section] = matches.pop()
    return {"program_code": program_code, "catalog_version": _active_edition(table, resolve),
            "statements": statements}


def _visible_program_sections(page: str, program_code: str, sections: list[str]) -> dict:
    """Resolve unique visible sections within the primary program's tree."""
    table, resolve = _nuxt_data(page)
    primary = next((v for v in table if isinstance(v, dict) and
                    {"code", "programGroupId", "degreeDesignation", "longName"} <= v.keys()), None)
    if primary is None or resolve(primary["code"]) != program_code or resolve(primary["programGroupId"]) != program_code:
        raise ValueError("The primary program identity does not match")
    requisites = resolve(primary.get("requisites"))
    if not isinstance(requisites, dict) or not isinstance(requisites.get("requisitesSimple"), list):
        raise ValueError("Program requirement groups are missing")
    queue = [(group, 0) for group in requisites["requisitesSimple"] if isinstance(group, dict)
             and group.get("showInCatalog") is True and group.get("requirementLevel") == "programRequirements"]
    matches = {section: [] for section in sections}
    visited = 0
    while queue:
        node, depth = queue.pop(0)
        visited += 1
        if visited > 2000 or depth > 20 or not isinstance(node, dict):
            raise ValueError("Program requirement traversal exceeds the supported limits")
        if node.get("showInCatalog") is False:
            continue
        name = node.get("name", "")
        if isinstance(name, str):
            for section in sections:
                if "(" + section + ")" in name:
                    matches[section].append(node)
        for key in ("rules", "subRules"):
            children = node.get(key, [])
            if not isinstance(children, list):
                raise ValueError("The program requirement structure is invalid")
            queue.extend((child, depth + 1) for child in children)
    for section, nodes in matches.items():
        if len(nodes) != 1:
            raise ValueError("The course-discovery section is missing or ambiguous")
    return {"program_code": program_code, "catalog_version": _active_edition(table, resolve),
            "nodes": {section: nodes[0] for section, nodes in matches.items()}}


def extract_program_courses(page: str, program_code: str, sections: list[str]) -> dict:
    """Read explicit course-ID lists from the primary visible program sections."""
    selected = _visible_program_sections(page, program_code, sections)
    courses = {}
    for section, node in selected["nodes"].items():
        value = node.get("value")
        if (not isinstance(value, dict) or value.get("condition") != "courses"
                or value.get("subSelections") not in (None, []) or not isinstance(value.get("values"), list)):
            raise ValueError("Only explicit course-ID lists can be discovered")
        ids = []
        for entry in value["values"]:
            if not isinstance(entry, dict) or not isinstance(entry.get("value"), list):
                raise ValueError("The course-ID list is invalid")
            for course_id in entry["value"]:
                if not isinstance(course_id, str) or not re.fullmatch(r"\d{7}", course_id):
                    raise ValueError("The course-ID list contains an unsupported reference")
                ids.append(course_id)
        ids = list(dict.fromkeys(ids))
        if not 1 <= len(ids) <= 40:
            raise ValueError("The course-ID list exceeds the supported limits")
        courses[section] = ids
    return {"program_code": program_code, "catalog_version": selected["catalog_version"], "course_ids": courses}


def extract_visible_program_statements(page: str, program_code: str, sections: list[str]) -> dict:
    """Read condition text from the exact visible nodes supplying course links."""
    selected = _visible_program_sections(page, program_code, sections)
    statements = {}
    for section, node in selected["nodes"].items():
        raw = node.get("description")
        if not isinstance(raw, str) or not raw.strip() or len(raw) > 20000:
            raise ValueError("The discovery condition statement is missing or invalid")
        text = description_text(raw)
        if not 1 <= len(text) <= 3000:
            raise ValueError("The discovery condition statement exceeds its limits")
        statements[section] = text
    return {"program_code": program_code, "catalog_version": selected["catalog_version"],
            "statements": statements}
