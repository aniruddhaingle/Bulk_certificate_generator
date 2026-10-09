from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.enums import CertificateStatus
from app.db.models import CertificateRecord


class CertificateRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def bulk_create(self, records: list[CertificateRecord]) -> None:
        self.db.add_all(records)

    def get_by_id(self, certificate_id: UUID) -> CertificateRecord | None:
        return self.db.get(CertificateRecord, certificate_id)

    def list_pending_ids_for_job(self, job_id: UUID) -> list[UUID]:
        rows = self.db.execute(
            select(CertificateRecord.id).where(
                CertificateRecord.job_id == job_id,
                CertificateRecord.status == CertificateStatus.PENDING,
            )
        )
        return list(rows.scalars().all())

    def try_claim_pending(self, certificate_id: UUID) -> bool:
        """Atomically PENDING -> PROCESSING. Returns False if some other
        delivery of the same task already claimed (or finished) this
        certificate — the idempotency guard against duplicate task delivery."""
        result = self.db.execute(
            update(CertificateRecord)
            .where(CertificateRecord.id == certificate_id, CertificateRecord.status == CertificateStatus.PENDING)
            .values(status=CertificateStatus.PROCESSING)
        )
        return result.rowcount == 1

    def mark_completed(self, certificate_id: UUID, storage_key: str) -> None:
        self.db.execute(
            update(CertificateRecord)
            .where(CertificateRecord.id == certificate_id)
            .values(status=CertificateStatus.COMPLETED, storage_key=storage_key, completed_at=func.now())
        )

    def mark_failed(self, certificate_id: UUID, error_message: str) -> None:
        self.db.execute(
            update(CertificateRecord)
            .where(CertificateRecord.id == certificate_id)
            .values(status=CertificateStatus.FAILED, error_message=error_message, completed_at=func.now())
        )

    def list_by_job(
        self,
        job_id: UUID,
        status: CertificateStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[CertificateRecord], int]:
        base_query = select(CertificateRecord).where(CertificateRecord.job_id == job_id)
        count_query = select(func.count()).select_from(CertificateRecord).where(CertificateRecord.job_id == job_id)

        if status is not None:
            base_query = base_query.where(CertificateRecord.status == status)
            count_query = count_query.where(CertificateRecord.status == status)

        total = self.db.execute(count_query).scalar_one()

        items = (
            self.db.execute(
                base_query.order_by(CertificateRecord.created_at, CertificateRecord.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .scalars()
            .all()
        )
        return list(items), total
