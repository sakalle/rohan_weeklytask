import json
import logging
from collections.abc import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import current_app
from pydantic import BaseModel, ConfigDict, Field, ValidationError

logger = logging.getLogger(__name__)


class ClassificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=10_000)


class ClassificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str = Field(min_length=1, max_length=100)
    priority: str
    sentiment: str

    @classmethod
    def validate_result(cls, value: object) -> "ClassificationResult":
        result = cls.model_validate(value)
        if result.priority not in {"low", "high"}:
            raise ValueError("priority must be either 'low' or 'high'")
        if result.sentiment not in {"positive", "neutral", "negative"}:
            raise ValueError("sentiment must be positive, neutral, or negative")
        return result


class ClassificationError(RuntimeError):
    """Raised when the configured LLM cannot provide a valid classification."""


class SummaryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=10_000)


class SummaryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=2_000)
    key_points: list[str] = Field(min_length=1, max_length=10)


class SummaryError(RuntimeError):
    """Raised when the configured LLM cannot provide a valid summary."""


def _request_with_retry(
    text: str, instruction: str, validate: Callable[[object], object]
) -> object:
    endpoint = current_app.config.get("LLM_API_URL")
    api_key = current_app.config.get("LLM_API_KEY")
    model = current_app.config.get("LLM_MODEL", "supportdesk-classifier")
    if not endpoint or not api_key:
        raise RuntimeError("AI service is not configured")

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": instruction},
            {"role": "user", "content": text},
        ],
        "temperature": 0,
    }
    headers = {
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
        "User-Agent": "SupportDesk/1.0",
    }
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            return validate(_request_classification(endpoint, headers, body))
        except (HTTPError, URLError, KeyError, TypeError, ValueError, ValidationError) as error:
            last_error = error
            logger.warning("AI request attempt %s failed: %s", attempt + 1, error)
    raise RuntimeError("The AI service returned invalid JSON") from last_error


def classify_text(text: str) -> ClassificationResult:
    try:
        result = _request_with_retry(
            text,
            "Classify the support message. Return only JSON with keys "
            "category, priority, sentiment. Priority must be low or high; "
            "sentiment must be positive, neutral, or negative.",
            ClassificationResult.validate_result,
        )
        return result
    except (RuntimeError, ValueError, ValidationError) as error:
        raise ClassificationError(str(error)) from error


def summarize_text(text: str) -> SummaryResult:
    try:
        result = _request_with_retry(
            text,
            "Summarize the support message. Return only JSON with keys "
            "summary and key_points, where key_points is a concise string array.",
            SummaryResult.model_validate,
        )
        return result
    except (RuntimeError, ValueError, ValidationError) as error:
        raise SummaryError(str(error)) from error


def _request_classification(
    endpoint: str, headers: dict[str, str], body: dict[str, object]
) -> object:
    request = Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urlopen(request, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if "choices" in payload:
        content = payload["choices"][0]["message"]["content"]
        return json.loads(content)
    return payload
