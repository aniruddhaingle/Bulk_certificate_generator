from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import CertificateStatus
from app.core.exceptions import CertificateNotReadyError
from app.db.session import get_db
from app.services.certificate_service import CertificateService
from app.services.storage_service import LocalStorageService

router = APIRouter(prefix="/api/v1/certificates", tags=["certificates"])


def get_storage() -> LocalStorageService:
    return LocalStorageService(settings.storage_dir)


@router.get("/{certificate_id}/download")
def download_certificate(
    certificate_id: UUID,
    db: Session = Depends(get_db),
    storage: LocalStorageService = Depends(get_storage),
) -> Response:
    certificate = CertificateService(db).get_certificate(certificate_id)

    if certificate.status != CertificateStatus.COMPLETED:
        raise CertificateNotReadyError(certificate_id, certificate.status.value, certificate.error_message)

    if not certificate.storage_key or not storage.exists(certificate.storage_key):
        raise CertificateNotReadyError(certificate_id, certificate.status.value, "stored file is missing")

    pdf_bytes = storage.get(certificate.storage_key)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{certificate.certificate_number}.pdf"'},
    )
