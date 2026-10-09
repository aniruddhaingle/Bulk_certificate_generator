from app.core.enums import CertificateStatus, JobStatus
from app.db.models import CertificateRecord, GenerationJob
from app.repositories.certificate_repository import CertificateRepository
from app.repositories.job_repository import JobRepository


def _make_job(db_session, total_count: int) -> GenerationJob:
    job = GenerationJob(total_count=total_count, status=JobStatus.PENDING)
    db_session.add(job)
    db_session.commit()
    return job


def test_start_processing_transitions_pending_to_processing(db_session):
    job = _make_job(db_session, total_count=3)
    repo = JobRepository(db_session)

    claimed = repo.start_processing(job.id)
    db_session.commit()

    assert claimed is True
    refreshed = repo.get_by_id(job.id)
    assert refreshed.status == JobStatus.PROCESSING
    assert refreshed.started_at is not None


def test_start_processing_is_a_one_time_guard(db_session):
    job = _make_job(db_session, total_count=3)
    repo = JobRepository(db_session)

    first = repo.start_processing(job.id)
    db_session.commit()
    second = repo.start_processing(job.id)
    db_session.commit()

    assert first is True
    assert second is False  # already PROCESSING, not PENDING anymore


def test_bump_counters_does_not_finalize_until_all_certificates_done(db_session):
    job = _make_job(db_session, total_count=3)
    repo = JobRepository(db_session)
    repo.start_processing(job.id)
    db_session.commit()

    repo.bump_counters_and_finalize(job.id, successful_delta=1, failed_delta=0)
    db_session.commit()

    refreshed = repo.get_by_id(job.id)
    assert refreshed.status == JobStatus.PROCESSING
    assert refreshed.successful_count == 1


def test_bump_counters_finalizes_as_completed_when_all_succeed(db_session):
    job = _make_job(db_session, total_count=2)
    repo = JobRepository(db_session)
    repo.start_processing(job.id)
    db_session.commit()

    repo.bump_counters_and_finalize(job.id, successful_delta=1, failed_delta=0)
    repo.bump_counters_and_finalize(job.id, successful_delta=1, failed_delta=0)
    db_session.commit()

    refreshed = repo.get_by_id(job.id)
    assert refreshed.status == JobStatus.COMPLETED
    assert refreshed.completed_at is not None


def test_bump_counters_finalizes_as_completed_with_errors_on_partial_failure(db_session):
    job = _make_job(db_session, total_count=2)
    repo = JobRepository(db_session)
    repo.start_processing(job.id)
    db_session.commit()

    repo.bump_counters_and_finalize(job.id, successful_delta=1, failed_delta=0)
    repo.bump_counters_and_finalize(job.id, successful_delta=0, failed_delta=1)
    db_session.commit()

    refreshed = repo.get_by_id(job.id)
    assert refreshed.status == JobStatus.COMPLETED_WITH_ERRORS


def test_bump_counters_finalizes_as_failed_when_all_fail(db_session):
    job = _make_job(db_session, total_count=2)
    repo = JobRepository(db_session)
    repo.start_processing(job.id)
    db_session.commit()

    repo.bump_counters_and_finalize(job.id, successful_delta=0, failed_delta=1)
    repo.bump_counters_and_finalize(job.id, successful_delta=0, failed_delta=1)
    db_session.commit()

    refreshed = repo.get_by_id(job.id)
    assert refreshed.status == JobStatus.FAILED


def test_try_claim_pending_succeeds_exactly_once(db_session):
    job = _make_job(db_session, total_count=1)
    cert = CertificateRecord(
        job_id=job.id,
        recipient_name="Jane Doe",
        certificate_title="Certificate",
        course_name="Course",
        issue_date="2026-01-01",
        certificate_number="CERT-TEST-00000001",
        status=CertificateStatus.PENDING,
    )
    db_session.add(cert)
    db_session.commit()

    repo = CertificateRepository(db_session)
    first = repo.try_claim_pending(cert.id)
    db_session.commit()
    second = repo.try_claim_pending(cert.id)
    db_session.commit()

    assert first is True
    assert second is False
