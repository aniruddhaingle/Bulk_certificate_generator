from dataclasses import dataclass
from datetime import date
from io import BytesIO

from app.services.storage_service import StorageError, StorageService
from app.templates.certificate_template import draw_certificate


class CertificateGenerationError(Exception):
    pass


@dataclass(frozen=True)
class CertificateData:
    recipient_name: str
    certificate_title: str
    course_name: str
    issue_date: date
    certificate_number: str


class CertificateGenerator:
    """Renders and stores certificate PDFs. Knows nothing about the database,
    the API layer, or Celery — it only depends on a StorageService."""

    def __init__(self, storage: StorageService) -> None:
        self.storage = storage

    def render(self, data: CertificateData) -> bytes:
        """Pure rendering: returns PDF bytes, touches no storage."""
        buffer = BytesIO()
        try:
            draw_certificate(
                buffer,
                recipient_name=data.recipient_name,
                certificate_title=data.certificate_title,
                course_name=data.course_name,
                issue_date=data.issue_date,
                certificate_number=data.certificate_number,
            )
        except Exception as exc:
            raise CertificateGenerationError(
                f"failed to render certificate {data.certificate_number!r}: {exc}"
            ) from exc
        return buffer.getvalue()

    def generate(self, data: CertificateData) -> str:
        """Render the certificate and persist it through the storage service.
        Returns the storage key. Raises CertificateGenerationError on any
        rendering or storage failure."""
        if not data.recipient_name or not data.recipient_name.strip():
            raise CertificateGenerationError("recipient_name must not be blank")

        pdf_bytes = self.render(data)
        key = f"{data.certificate_number}.pdf"

        try:
            self.storage.save(key, pdf_bytes)
        except StorageError as exc:
            raise CertificateGenerationError(
                f"failed to store certificate {data.certificate_number!r}: {exc}"
            ) from exc

        return key
