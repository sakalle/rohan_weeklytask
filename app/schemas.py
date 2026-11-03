from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)


class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10_000)
    customer_email: EmailStr
    priority: str = "low"

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str) -> str:
        if value not in {"low", "high"}:
            raise ValueError("priority must be either 'low' or 'high'")
        return value


class TicketUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=10_000)
    customer_email: EmailStr | None = None
    priority: str | None = None
    status: str | None = None

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "TicketUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field is required")
        return self

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str | None) -> str | None:
        if value is not None and value not in {"low", "high"}:
            raise ValueError("priority must be either 'low' or 'high'")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None and value not in {"open", "in_progress", "resolved"}:
            raise ValueError("status must be open, in_progress, or resolved")
        return value


def model_errors(error: ValidationError) -> list[dict[str, Any]]:
    return [
        {"field": ".".join(str(item) for item in item["loc"]), "message": item["msg"]}
        for item in error.errors()
    ]
