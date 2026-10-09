from uuid import UUID

from sqlalchemy.orm import Session

from app.core.enums import CertificateStatus, JobStatus
from app.core.exceptions import JobNotFoundError
from app.db.models import CertificateRecord, GenerationJob
from app.repositories.certificate_repository import CertificateRepository
from app.repositories.job_repository import JobRepository
from app.schemas.certificate_job import CertificateJobCreate
from app.utils.ids import generate_certificate_number


class JobService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.job_repo = JobRepository(db)
        self.cert_repo = CertificateRepository(db)

    def create_job(self, payload: CertificateJobCreate) -> GenerationJob:
        job = GenerationJob(total_count=len(payload.recipients), status=JobStatus.PENDING)
        self.job_repo.create(job)
        self.db.flush()  # populate job.id so it can be used as the FK below

        records = [
            CertificateRecord(
                job_id=job.id,
                recipient_name=recipient.name,
                recipient_email=recipient.email,
                certificate_title=payload.certificate_title,
                course_name=payload.course_name,
                issue_date=payload.issue_date,
                certificate_number=generate_certificate_number(payload.issue_date),
                status=CertificateStatus.PENDING,
            )
            for recipient in payload.recipients
        ]
        self.cert_repo.bulk_create(records)

        self.db.commit()
        self.db.refresh(job)

        return job

    def get_job(self, job_id: UUID) -> GenerationJob:
        job = self.job_repo.get_by_id(job_id)
        if job is None:
            raise JobNotFoundError(job_id)
        return job

    def list_certificates(
        self,
        job_id: UUID,
        status: CertificateStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[GenerationJob, list[CertificateRecord], int]:
        job = self.get_job(job_id)
        items, total = self.cert_repo.list_by_job(job_id, status, page, page_size)
        return job, items, total
