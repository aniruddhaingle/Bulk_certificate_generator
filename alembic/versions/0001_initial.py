"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None

JOB_STATUS_VALUES = ("PENDING", "PROCESSING", "COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED")
CERTIFICATE_STATUS_VALUES = ("PENDING", "PROCESSING", "COMPLETED", "FAILED")


def upgrade() -> None:
    job_status = postgresql.ENUM(*JOB_STATUS_VALUES, name="job_status")
    certificate_status = postgresql.ENUM(*CERTIFICATE_STATUS_VALUES, name="certificate_status")
    job_status.create(op.get_bind(), checkfirst=True)
    certificate_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "generation_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("status", job_status, nullable=False, server_default="PENDING"),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("successful_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
    )

    op.create_table(
        "certificate_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("generation_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("recipient_name", sa.String(length=200), nullable=False),
        sa.Column("recipient_email", sa.String(length=320), nullable=True),
        sa.Column("certificate_title", sa.String(length=200), nullable=False),
        sa.Column("course_name", sa.String(length=200), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("certificate_number", sa.String(length=40), nullable=False),
        sa.Column("status", certificate_status, nullable=False, server_default="PENDING"),
        sa.Column("storage_key", sa.String(length=500), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_certificate_records_job_id", "certificate_records", ["job_id"])
    op.create_index("ix_certificate_records_job_id_status", "certificate_records", ["job_id", "status"])
    op.create_index(
        "ix_certificate_records_certificate_number",
        "certificate_records",
        ["certificate_number"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_certificate_records_certificate_number", table_name="certificate_records")
    op.drop_index("ix_certificate_records_job_id_status", table_name="certificate_records")
    op.drop_index("ix_certificate_records_job_id", table_name="certificate_records")
    op.drop_table("certificate_records")
    op.drop_table("generation_jobs")

    postgresql.ENUM(*CERTIFICATE_STATUS_VALUES, name="certificate_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(*JOB_STATUS_VALUES, name="job_status").drop(op.get_bind(), checkfirst=True)
