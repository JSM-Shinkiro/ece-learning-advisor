"""Local catalog filtering; no retrieval, academic decisions or source requests."""

import re


def filter_collection(catalog,query="",kind="all",direction="all"):
    if not isinstance(query,str) or len(query)>200:
        raise ValueError("Keep collection searches within 200 characters")
    if kind not in {"all","course","resource"} or direction not in {"all","ai_ml","embedded"}:
        raise ValueError("Choose an available collection filter")
    # Accept the spaces students commonly type inside a course code.
    query=re.sub(r"\b([A-Z]{2,8})\s+(\d{3}[A-Z]{0,2})\b",r"\1\2",query,flags=re.I)
    terms=query.casefold().split()
    found=[]
    for record in catalog.records:
        if record.kind not in {"course","resource"} or kind!="all" and record.kind!=kind:
            continue
        if direction!="all" and record.career_ids and direction not in record.career_ids:
            continue
        text=" ".join([record.code or "",record.title,record.summary," ".join(record.topics),
                       record.learning_note or "",record.first_activity or ""]).casefold()
        if all(term in text for term in terms):
            found.append(record)
    return found
