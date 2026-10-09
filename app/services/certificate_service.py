from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import CertificateNotFoundError
from app.db.models import CertificateRecord
from app.repositories.certificate_repository import CertificateRepository


class CertificateService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.cert_repo = CertificateRepository(db)

    def get_certificate(self, certificate_id: UUID) -> CertificateRecord:
        certificate = self.cert_repo.get_by_id(certificate_id)
        if certificate is None:
            raise CertificateNotFoundError(certificate_id)
        return certificate
