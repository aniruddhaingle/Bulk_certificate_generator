from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.core.config import settings
from app.core.enums import JobStatus


class RecipientIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be blank")
        return stripped


class CertificateJobCreate(BaseModel):
    certificate_title: str = Field(min_length=1, max_length=200)
    course_name: str = Field(min_length=1, max_length=200)
    issue_date: date
    recipients: list[RecipientIn] = Field(min_length=1)

    @field_validator("recipients")
    @classmethod
    def validate_bulk_size(cls, value: list[RecipientIn]) -> list[RecipientIn]:
        if len(value) > settings.max_bulk_size:
            raise ValueError(f"recipients exceeds maximum bulk size of {settings.max_bulk_size}")
        return value

    @model_validator(mode="after")
    def validate_no_duplicate_recipients(self) -> "CertificateJobCreate":
        seen: set[tuple[str, str]] = set()
        duplicate_indices: list[int] = []
        for index, recipient in enumerate(self.recipients):
            key = (recipient.name.strip().lower(), (recipient.email or "").strip().lower())
            if key in seen:
                duplicate_indices.append(index)
            seen.add(key)
        if duplicate_indices:
            raise ValueError(f"duplicate recipients found at indices: {duplicate_indices}")
        return self


class CertificateJobCreateResponse(BaseModel):
    model_config = {"from_attributes": True}

    job_id: UUID
    status: JobStatus
    total_count: int
    successful_count: int
    failed_count: int
    created_at: datetime


class CertificateJobStatusResponse(BaseModel):
    model_config = {"from_attributes": True}

    job_id: UUID
    status: JobStatus
    total_count: int
    successful_count: int
    failed_count: int
    pending_count: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_summary: str | None
