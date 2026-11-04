"""Extract review candidates from public Coursedog catalog page data."""

from __future__ import annotations

import hashlib
import json
import re


def extract_course(page: str) -> dict:
    match = re.search(r'<script[^>]*id=["\']__NUXT_DATA__["\'][^>]*>(.*?)</script>', page, re.S)
    if not match:
        raise ValueError("The catalog page format is not recognized")
    table = json.loads(match.group(1))
    if not isinstance(table, list):
        raise ValueError("Expected a Nuxt reference table")

    def resolve(index, visited=()):
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

    raw = next((v for v in table if isinstance(v, dict) and
                {"code", "longName", "description", "credits", "requirementGroup"} <= set(v)), None)
    if raw is None:
        raise ValueError("Course metadata is missing")
    fields = {key: resolve(raw[key]) for key in
              ["code", "longName", "description", "credits", "requirementGroup", "effectiveStartDate"] if key in raw}
    return {
        "code": fields["code"],
        "title": fields["longName"],
        "credits": fields["credits"].get("creditHours"),
        "requirement_reference": fields["requirementGroup"],
        "effective_start": fields.get("effectiveStartDate"),
        "description_hash": hashlib.sha256(fields["description"].encode()).hexdigest(),
        "page_hash": hashlib.sha256(page.encode()).hexdigest(),
        "review_required": True,
    }
