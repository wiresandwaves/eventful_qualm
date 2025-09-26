from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

SCHEMA_V1: Literal[1] = 1


def utc_now() -> datetime:
    return datetime.now(UTC)


class ErrorInfo(BaseModel):
    code: Literal["bad-json", "api-mismatch", "timeout", "internal"]
    detail: str | None = None


class CommandEnvelope(BaseModel):
    schema_version: Literal[1] = Field(default=SCHEMA_V1)
    msg_id: str
    ts: datetime = Field(default_factory=utc_now)
    command: dict  # compatible with your Command Protocol shape


class ResponseEnvelope(BaseModel):
    ok: bool
    correlates_to: str
    data: Any | None = None
    error: ErrorInfo | None = None


class TelemetryEnvelope(BaseModel):
    schema_version: Literal[1] = Field(default=SCHEMA_V1)
    msg_id: str
    ts: datetime = Field(default_factory=utc_now)
    topic: str
    data: dict
