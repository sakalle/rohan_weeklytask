import json
import logging
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


def classify_text(text: str) -> ClassificationResult:
    endpoint = current_app.config.get("LLM_API_URL")
    api_key = current_app.config.get("LLM_API_KEY")
    model = current_app.config.get("LLM_MODEL", "supportdesk-classifier")
    if not endpoint or not api_key:
        raise ClassificationError("AI classification is not configured")

    request_body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Classify the support message. Return only JSON with keys "
                    "category, priority, sentiment. Priority must be low or high; "
                    "sentiment must be positive, neutral, or negative."
                ),
            },
            {"role": "user", "content": text},
        ],
        "temperature": 0,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "SupportDesk/1.0",
    }

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            result = _request_classification(endpoint, headers, request_body)
            return ClassificationResult.validate_result(result)
        except (HTTPError, URLError, KeyError, TypeError, ValueError, ValidationError) as error:
            last_error = error
            logger.warning("AI classification attempt %s failed: %s", attempt + 1, error)

    raise ClassificationError("The AI service returned an invalid classification") from last_error


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
