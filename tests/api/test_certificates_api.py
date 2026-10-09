import uuid

from app.core.enums import CertificateStatus
from app.db.models import CertificateRecord, GenerationJob


def _create_job_with_certificate(
    db_session,
    status: CertificateStatus = CertificateStatus.PENDING,
    storage_key: str | None = None,
    error_message: str | None = None,
) -> CertificateRecord:
    job = GenerationJob(total_count=1, status="PENDING")
    db_session.add(job)
    db_session.flush()

    certificate = CertificateRecord(
        job_id=job.id,
        recipient_name="Jane Doe",
        recipient_email="jane@example.com",
        certificate_title="Certificate of Completion",
        course_name="Advanced Python Programming",
        issue_date="2026-01-01",
        certificate_number=f"CERT-TEST-{uuid.uuid4().hex[:8]}",
        status=status,
        storage_key=storage_key,
        error_message=error_message,
    )
    db_session.add(certificate)
    db_session.commit()
    return certificate


def test_download_nonexistent_certificate_returns_404(client):
    response = client.get(f"/api/v1/certificates/{uuid.uuid4()}/download")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CERTIFICATE_NOT_FOUND"


def test_download_pending_certificate_returns_409(client, db_session):
    certificate = _create_job_with_certificate(db_session, status=CertificateStatus.PENDING)

    response = client.get(f"/api/v1/certificates/{certificate.id}/download")

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "CERTIFICATE_NOT_READY"
    assert body["error"]["context"]["status"] == "PENDING"


def test_download_failed_certificate_returns_409_with_error_message(client, db_session):
    certificate = _create_job_with_certificate(
        db_session, status=CertificateStatus.FAILED, error_message="template render failed"
    )

    response = client.get(f"/api/v1/certificates/{certificate.id}/download")

    assert response.status_code == 409
    assert response.json()["error"]["context"]["error_message"] == "template render failed"


def test_download_completed_certificate_returns_pdf(client, db_session, tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))
    storage_key = "some-job/some-cert.pdf"
    file_path = tmp_path / storage_key
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"%PDF-1.4 fake pdf content")

    certificate = _create_job_with_certificate(
        db_session, status=CertificateStatus.COMPLETED, storage_key=storage_key
    )

    response = client.get(f"/api/v1/certificates/{certificate.id}/download")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == b"%PDF-1.4 fake pdf content"
