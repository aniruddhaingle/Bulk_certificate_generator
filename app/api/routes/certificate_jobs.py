from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.enums import CertificateStatus
from app.db.session import get_db
from app.schemas.certificate import CertificateItem, CertificateListResponse
from app.schemas.certificate_job import (
    CertificateJobCreate,
    CertificateJobCreateResponse,
    CertificateJobStatusResponse,
)
from app.services.job_service import JobService

router = APIRouter(prefix="/api/v1/certificate-jobs", tags=["certificate-jobs"])


@router.post("", response_model=CertificateJobCreateResponse, status_code=202)
def create_certificate_job(
    payload: CertificateJobCreate, db: Session = Depends(get_db)
) -> CertificateJobCreateResponse:
    job = JobService(db).create_job(payload)
    return CertificateJobCreateResponse.model_validate(job)


@router.get("/{job_id}", response_model=CertificateJobStatusResponse)
def get_certificate_job(job_id: UUID, db: Session = Depends(get_db)) -> CertificateJobStatusResponse:
    job = JobService(db).get_job(job_id)
    pending_count = job.total_count - job.successful_count - job.failed_count
    return CertificateJobStatusResponse(
        job_id=job.id,
        status=job.status,
        total_count=job.total_count,
        successful_count=job.successful_count,
        failed_count=job.failed_count,
        pending_count=pending_count,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_summary=job.error_summary,
    )


@router.get("/{job_id}/certificates", response_model=CertificateListResponse)
def list_job_certificates(
    job_id: UUID,
    status: CertificateStatus | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> CertificateListResponse:
    job, items, total = JobService(db).list_certificates(job_id, status, page, page_size)
    return CertificateListResponse(
        job_id=job.id,
        page=page,
        page_size=page_size,
        total=total,
        items=[
            CertificateItem(
                certificate_id=item.id,
                recipient_name=item.recipient_name,
                recipient_email=item.recipient_email,
                status=item.status,
                certificate_number=item.certificate_number,
                download_url=f"/api/v1/certificates/{item.id}/download",
                error_message=item.error_message,
                created_at=item.created_at,
                completed_at=item.completed_at,
            )
            for item in items
        ],
    )
