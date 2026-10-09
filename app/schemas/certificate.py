from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.core.enums import CertificateStatus


class CertificateItem(BaseModel):
    model_config = {"from_attributes": True}

    certificate_id: UUID
    recipient_name: str
    recipient_email: str | None
    status: CertificateStatus
    certificate_number: str
    download_url: str
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class CertificateListResponse(BaseModel):
    job_id: UUID
    page: int
    page_size: int
    total: int
    items: list[CertificateItem]
