"""Exercises the actual schema constraints from alembic/versions/0001_initial.py
against a real Postgres instance — FK enforcement, cascade delete, and the
unique constraint on certificate_number. None of this is enforceable by
SQLite, so it genuinely needs the real database, not a lighter substitute."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.models import CertificateRecord, GenerationJob


def _job(db_session, total_count: int = 1) -> GenerationJob:
    job = GenerationJob(total_count=total_count, status="PENDING")
    db_session.add(job)
    db_session.flush()
    return job


def _cert(job_id, number: str, name: str = "Jane Doe") -> CertificateRecord:
    return CertificateRecord(
        job_id=job_id,
        recipient_name=name,
        certificate_title="Certificate of Completion",
        course_name="Advanced Python Programming",
        issue_date="2026-01-01",
        certificate_number=number,
    )


def test_job_certificates_relationship_loads_all_children(db_session):
    job = _job(db_session, total_count=2)
    db_session.add_all([
        _cert(job.id, "CERT-TEST-REL00001", "Person A"),
        _cert(job.id, "CERT-TEST-REL00002", "Person B"),
    ])
    db_session.commit()
    db_session.refresh(job)

    assert len(job.certificates) == 2
    assert {c.recipient_name for c in job.certificates} == {"Person A", "Person B"}


def test_certificate_back_reference_points_to_its_job(db_session):
    job = _job(db_session)
    cert = _cert(job.id, "CERT-TEST-REL00003")
    db_session.add(cert)
    db_session.commit()
    db_session.refresh(cert)

    assert cert.job.id == job.id


def test_deleting_job_cascades_to_its_certificates(db_session):
    job = _job(db_session)
    cert = _cert(job.id, "CERT-TEST-REL00004")
    db_session.add(cert)
    db_session.commit()
    cert_id = cert.id

    db_session.delete(job)
    db_session.commit()

    assert db_session.get(CertificateRecord, cert_id) is None


def test_certificate_number_uniqueness_is_enforced_by_the_database(db_session):
    job = _job(db_session, total_count=2)
    db_session.add(_cert(job.id, "CERT-TEST-DUPNUM01", "First"))
    db_session.commit()

    db_session.add(_cert(job.id, "CERT-TEST-DUPNUM01", "Second"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_certificate_cannot_reference_a_nonexistent_job(db_session):
    orphan = _cert(uuid4(), "CERT-TEST-ORPHAN01")
    db_session.add(orphan)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
