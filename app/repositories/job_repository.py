from uuid import UUID

from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.core.enums import JobStatus
from app.db.models import GenerationJob


class JobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, job: GenerationJob) -> GenerationJob:
        self.db.add(job)
        return job

    def get_by_id(self, job_id: UUID) -> GenerationJob | None:
        return self.db.get(GenerationJob, job_id)

    def mark_scheduling_failed(self, job_id: UUID, error_summary: str) -> None:
        """The job itself could not be processed (e.g. the broker was
        unreachable right after creation) — distinct from a per-certificate
        failure, this is a job-level FAILED with no certificates ever having
        been attempted."""
        self.db.execute(
            update(GenerationJob)
            .where(GenerationJob.id == job_id, GenerationJob.status == JobStatus.PENDING)
            .values(status=JobStatus.FAILED, error_summary=error_summary, completed_at=func.now())
        )

    def start_processing(self, job_id: UUID) -> bool:
        """Atomically PENDING -> PROCESSING. Returns False if some other
        delivery of the same task already did this (duplicate dispatch guard)."""
        result = self.db.execute(
            update(GenerationJob)
            .where(GenerationJob.id == job_id, GenerationJob.status == JobStatus.PENDING)
            .values(status=JobStatus.PROCESSING, started_at=func.now())
        )
        return result.rowcount == 1

    def bump_counters_and_finalize(self, job_id: UUID, successful_delta: int, failed_delta: int) -> None:
        """Atomically add to the job's counters with a single UPDATE (no
        read-modify-write in Python, so concurrent workers can't lose an
        update), then finalize the job's status if every certificate has
        reached a terminal state. The finalizing UPDATE is guarded by
        `WHERE status = PROCESSING`, so if two workers both think they're
        last, only the first one's write actually changes anything — the
        second affects zero rows."""
        result = self.db.execute(
            update(GenerationJob)
            .where(GenerationJob.id == job_id)
            .values(
                successful_count=GenerationJob.successful_count + successful_delta,
                failed_count=GenerationJob.failed_count + failed_delta,
            )
            .returning(GenerationJob.successful_count, GenerationJob.failed_count, GenerationJob.total_count)
        )
        successful_count, failed_count, total_count = result.one()

        if successful_count + failed_count < total_count:
            return

        if successful_count == 0:
            final_status = JobStatus.FAILED
        elif failed_count == 0:
            final_status = JobStatus.COMPLETED
        else:
            final_status = JobStatus.COMPLETED_WITH_ERRORS

        self.db.execute(
            update(GenerationJob)
            .where(GenerationJob.id == job_id, GenerationJob.status == JobStatus.PROCESSING)
            .values(status=final_status, completed_at=func.now())
        )
