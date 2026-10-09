"""Exercises the actual race condition the architecture is designed to avoid:
many real DB connections bumping the same job's counters at once. Uses the
session-scoped `engine` fixture directly (real commits across threads), not
`db_session` (which is one rolled-back transaction per test and wouldn't let
separate threads see each other's writes)."""

import threading

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.enums import JobStatus
from app.db.models import GenerationJob
from app.repositories.job_repository import JobRepository


def test_concurrent_counter_updates_are_accurate(engine):
    with Session(engine) as setup_session:
        job = GenerationJob(total_count=50, status=JobStatus.PROCESSING)
        setup_session.add(job)
        setup_session.commit()
        job_id = job.id

    def bump(successful_delta: int, failed_delta: int) -> None:
        with Session(engine) as session:
            JobRepository(session).bump_counters_and_finalize(job_id, successful_delta, failed_delta)
            session.commit()

    threads = [threading.Thread(target=bump, args=(1, 0)) for _ in range(40)]
    threads += [threading.Thread(target=bump, args=(0, 1)) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    try:
        with Session(engine) as session:
            job = session.get(GenerationJob, job_id)
            assert job.successful_count == 40
            assert job.failed_count == 10
            assert job.status == JobStatus.COMPLETED_WITH_ERRORS
    finally:
        with Session(engine) as session:
            session.execute(delete(GenerationJob).where(GenerationJob.id == job_id))
            session.commit()
