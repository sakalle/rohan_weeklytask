import re

from .models import KnowledgeDocument


def retrieve_documents(query: str, limit: int = 3) -> list[dict]:
    query_terms = set(re.findall(r"[a-z0-9]+", query.lower()))
    scored: list[tuple[int, KnowledgeDocument]] = []
    for document in KnowledgeDocument.query.all():
        terms = set(re.findall(r"[a-z0-9]+", (document.title + " " + document.content).lower()))
        score = len(query_terms & terms)
        if score:
            scored.append((score, document))
    scored.sort(key=lambda item: (-item[0], item[1].id))
    return [
        {
            "id": document.id,
            "title": document.title,
            "source": document.source,
            "snippet": document.content[:500],
        }
        for _, document in scored[:limit]
    ]
