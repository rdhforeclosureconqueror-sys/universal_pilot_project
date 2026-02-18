"""infra unshakeable controls

Revision ID: a4f8e2b7c1d3
Revises: 9d2f4c6a1e77
Create Date: 2026-02-17 02:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "a4f8e2b7c1d3"
down_revision = "9d2f4c6a1e77"
branch_labels = None
depends_on = None


override_category = sa.Enum(
    "data_correction",
    "legal_exception",
    "executive_directive",
    "system_recovery",
    name="workflowoverridecategory",
)


def upgrade() -> None:
    op.create_table(
        "ingestion_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("metric_type", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("file_hash", sa.String(), nullable=True),
        sa.Column("file_name", sa.String(), nullable=True),
        sa.Column("count_value", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    op.create_index("ix_ingestion_metrics_metric_type", "ingestion_metrics", ["metric_type"])

    op.add_column("workflow_templates", sa.Column("template_version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("workflow_steps", sa.Column("sla_days", sa.Integer(), nullable=False, server_default="30"))

    op.add_column("case_workflow_instances", sa.Column("locked_template_version", sa.Integer(), nullable=False, server_default="1"))

    override_category.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "workflow_overrides",
        sa.Column("reason_category", override_category, nullable=True),
    )
    op.execute("UPDATE workflow_overrides SET reason_category='system_recovery' WHERE reason_category IS NULL")
    op.alter_column("workflow_overrides", "reason_category", nullable=False)


def downgrade() -> None:
    op.alter_column("workflow_overrides", "reason_category", nullable=True)
    op.drop_column("workflow_overrides", "reason_category")
    override_category.drop(op.get_bind(), checkfirst=True)

    op.drop_column("case_workflow_instances", "locked_template_version")
    op.drop_column("workflow_steps", "sla_days")
    op.drop_column("workflow_templates", "template_version")

    op.drop_index("ix_ingestion_metrics_metric_type", table_name="ingestion_metrics")
    op.drop_table("ingestion_metrics")
