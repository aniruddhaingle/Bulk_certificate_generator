import uuid

import pytest

from app.core.exceptions import JobNotFoundError
from app.schemas.certificate_job import CertificateJobCreate
from app.services.job_service import JobService


def _payload(n: int = 2) -> CertificateJobCreate:
    return CertificateJobCreate(
        certificate_title="Certificate of Completion",
        course_name="Advanced Python Programming",
        issue_date="2026-01-01",
        recipients=[{"name": f"Person {i}", "email": f"p{i}@example.com"} for i in range(n)],
    )


def test_create_job_persists_job_and_certificates(db_session):
    service = JobService(db_session)

    job = service.create_job(_payload(3))

    assert job.id is not None
    assert job.total_count == 3
    assert job.status.value == "PENDING"
    assert len(job.certificates) == 3
    assert all(cert.status.value == "PENDING" for cert in job.certificates)
    assert len({cert.certificate_number for cert in job.certificates}) == 3


def test_get_job_raises_not_found_for_unknown_id(db_session):
    service = JobService(db_session)

    with pytest.raises(JobNotFoundError):
        service.get_job(uuid.uuid4())


def test_list_certificates_returns_job_and_items(db_session):
    service = JobService(db_session)
    job = service.create_job(_payload(2))

    fetched_job, items, total = service.list_certificates(job.id, None, page=1, page_size=50)

    assert fetched_job.id == job.id
    assert total == 2
    assert len(items) == 2


def test_list_certificates_raises_not_found_for_unknown_job(db_session):
    service = JobService(db_session)

    with pytest.raises(JobNotFoundError):
        service.list_certificates(uuid.uuid4(), None, page=1, page_size=50)
