import json
import logging
from collections.abc import Iterator

from flask import current_app

from .ai import _request_with_retry
from .rag import retrieve_documents

logger = logging.getLogger(__name__)
_cache: dict[str, dict] = {}
_usage: dict[str, tuple[str, int]] = {}


class ChatError(RuntimeError):
    """Raised when chat generation is unavailable."""


def answer_question(question: str, user_key: str) -> dict:
    sources = retrieve_documents(question)
    if not sources:
        return {
            "answer": "I don't know based on the available support documents.",
            "sources": [],
            "cached": False,
        }

    cache_key = question.strip().lower()
    if cache_key in _cache:
        cached = dict(_cache[cache_key])
        cached["cached"] = True
        return cached

    _check_quota(user_key)
    context = "\n\n".join(f"[{item['id']}] {item['snippet']}" for item in sources)
    try:
        answer = _request_with_retry(
            question,
            "Answer only from the provided context. Return JSON with an answer string. "
            "If context is insufficient, say you do not know.\n\nContext:\n" + context,
            lambda value: _validate_answer(value),
        )
    except RuntimeError as error:
        raise ChatError("The chat service is unavailable") from error

    result = {"answer": answer, "sources": sources, "cached": False}
    _cache[cache_key] = result
    return result


def stream_answer(question: str, user_key: str) -> Iterator[str]:
    result = answer_question(question, user_key)
    yield f"data: {json.dumps({'type': 'sources', 'sources': result['sources']})}\n\n"
    yield f"data: {json.dumps({'type': 'answer', 'answer': result['answer']})}\n\n"
    yield "data: [DONE]\n\n"


def _validate_answer(value: object) -> str:
    if not isinstance(value, dict) or not isinstance(value.get("answer"), str):
        raise ValueError("answer must be a string")
    answer = value["answer"].strip()
    if not answer or len(answer) > 4_000:
        raise ValueError("answer is empty or too long")
    return answer


def _check_quota(user_key: str) -> None:
    date = current_app.config.get("CURRENT_DATE", "daily")
    limit = current_app.config.get("CHAT_DAILY_QUOTA", 20)
    usage_date, count = _usage.get(user_key, (date, 0))
    if usage_date != date:
        count = 0
    if count >= limit:
        raise ChatError("Daily chat quota exceeded")
    _usage[user_key] = (date, count + 1)
