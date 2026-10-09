import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import CertificateStatus, JobStatus
from app.db.base import Base


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus, name="job_status"),
        nullable=False,
        default=JobStatus.PENDING,
        server_default=JobStatus.PENDING.value,
    )
    total_count: Mapped[int] = mapped_column(Integer, nullable=False)
    successful_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    certificates: Mapped[list["CertificateRecord"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )


class CertificateRecord(Base):
    __tablename__ = "certificate_records"
    __table_args__ = (
        Index("ix_certificate_records_job_id_status", "job_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generation_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    recipient_name: Mapped[str] = mapped_column(String(200), nullable=False)
    recipient_email: Mapped[str | None] = mapped_column(String(320), nullable=True)

    certificate_title: Mapped[str] = mapped_column(String(200), nullable=False)
    course_name: Mapped[str] = mapped_column(String(200), nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    certificate_number: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)

    status: Mapped[CertificateStatus] = mapped_column(
        SQLEnum(CertificateStatus, name="certificate_status"),
        nullable=False,
        default=CertificateStatus.PENDING,
        server_default=CertificateStatus.PENDING.value,
    )
    storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    job: Mapped["GenerationJob"] = relationship(back_populates="certificates")
