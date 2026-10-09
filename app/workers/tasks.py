import logging

from app.core.config import settings
from app.db.session import session_scope
from app.repositories.certificate_repository import CertificateRepository
from app.repositories.job_repository import JobRepository
from app.services.certificate_generator import (
    CertificateData,
    CertificateGenerationError,
    CertificateGenerator,
)
from app.services.storage_service import LocalStorageService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="process_certificate_job")
def process_certificate_job(job_id: str) -> None:
    """Orchestrator: claims the job, then fans out one independent task per
    certificate. Dispatch happens after the claim commits, so a crash before
    that point just leaves the job PENDING for a fresh dispatch, and a crash
    after it only risks re-dispatching certificates that are themselves
    idempotent (see generate_certificate)."""
    with session_scope() as db:
        job_repo = JobRepository(db)
        started = job_repo.start_processing(job_id)
        if not started:
            logger.info("job %s is not PENDING (already started elsewhere) — skipping duplicate dispatch", job_id)
            return

        cert_ids = CertificateRepository(db).list_pending_ids_for_job(job_id)
        db.commit()

    logger.info("job %s: dispatching %d certificate task(s)", job_id, len(cert_ids))
    for certificate_id in cert_ids:
        generate_certificate.delay(str(certificate_id))


@celery_app.task(name="generate_certificate")
def generate_certificate(certificate_id: str) -> None:
    """Processes exactly one certificate. A failure here is recorded against
    this certificate only and never raised back to Celery — bulk processing
    must keep going for every other recipient regardless of this one's
    outcome. No automatic retry on generation failure: the storage key is
    deterministic, so a retry wouldn't create a duplicate file, but a broken
    template or malformed recipient data will fail the same way every time,
    and retrying would just delay marking it FAILED for no benefit."""
    with session_scope() as db:
        cert_repo = CertificateRepository(db)
        certificate = cert_repo.get_by_id(certificate_id)
        if certificate is None:
            logger.warning("certificate %s not found — skipping", certificate_id)
            return

        if not cert_repo.try_claim_pending(certificate_id):
            logger.info("certificate %s is not PENDING (already claimed/finished) — skipping duplicate delivery", certificate_id)
            return

        data = CertificateData(
            recipient_name=certificate.recipient_name,
            certificate_title=certificate.certificate_title,
            course_name=certificate.course_name,
            issue_date=certificate.issue_date,
            certificate_number=certificate.certificate_number,
        )
        job_id = certificate.job_id
        db.commit()

    generator = CertificateGenerator(LocalStorageService(settings.storage_dir))

    try:
        storage_key = generator.generate(data)
    except CertificateGenerationError as exc:
        error_message = str(exc)[:500]
        logger.warning("certificate %s failed to generate: %s", certificate_id, error_message)
        with session_scope() as db:
            CertificateRepository(db).mark_failed(certificate_id, error_message)
            # Marking the row FAILED and bumping the job's failed_count happen
            # in the same commit, so a crash between them is impossible —
            # there's no window where the certificate looks done but the job
            # total doesn't reflect it yet.
            JobRepository(db).bump_counters_and_finalize(job_id, successful_delta=0, failed_delta=1)
            db.commit()
        return

    logger.info("certificate %s generated successfully -> %s", certificate_id, storage_key)
    with session_scope() as db:
        CertificateRepository(db).mark_completed(certificate_id, storage_key)
        JobRepository(db).bump_counters_and_finalize(job_id, successful_delta=1, failed_delta=0)
        db.commit()
