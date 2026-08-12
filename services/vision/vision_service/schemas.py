from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class HealthResponse(BaseModel):
    status: Literal["ok"]


class InternalObjectReference(BaseModel):
    scan_id: UUID
    storage_backend: str = Field(min_length=1, max_length=32)
    object_key: str = Field(min_length=1, max_length=512)
    content_type: Literal["image/jpeg", "image/png"]
    checksum_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("object_key")
    @classmethod
    def validate_relative_object_key(cls, value: str) -> str:
        parts = value.split("/")
        if value.startswith("/") or "\\" in value or ".." in parts or "" in parts:
            raise ValueError("object_key must be a safe relative object key")
        return value


class AnalyzeRequest(BaseModel):
    object_reference: InternalObjectReference


class DetectedItem(BaseModel):
    label: str = Field(min_length=1, max_length=128)
    confidence: float = Field(ge=0, le=1)


class AnalyzeResponse(BaseModel):
    items: list[DetectedItem]
