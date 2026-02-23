"""harden workflow and ingestion idempotency

Revision ID: 9d2f4c6a1e77
Revises: 7a1d9d3b4c55
Create Date: 2026-02-17 01:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "9d2f4c6a1e77"
down_revision = "7a1d9d3b4c55"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("auction_imports", sa.Column("file_hash", sa.String(), nullable=True))
    op.create_index("ix_auction_imports_file_hash", "auction_imports", ["file_hash"], unique=True)

    op.add_column("cases", sa.Column("program_key", sa.String(), nullable=True))
    op.add_column("cases", sa.Column("meta", sa.JSON(), nullable=True))
    op.add_column("cases", sa.Column("auction_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("cases", sa.Column("canonical_key", sa.String(), nullable=True))
    op.create_index("ix_cases_canonical_key", "cases", ["canonical_key"], unique=True)
    op.create_unique_constraint(
        "uq_cases_property_auction_date",
        "cases",
        ["property_id", "auction_date"],
    )

    op.create_table(
        "workflow_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("instance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("case_workflow_instances.id"), nullable=False),
        sa.Column("from_step_key", sa.String(), nullable=False),
        sa.Column("to_step_key", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    op.create_index("ix_workflow_overrides_case_id", "workflow_overrides", ["case_id"])
    op.create_index("ix_workflow_overrides_instance_id", "workflow_overrides", ["instance_id"])


def downgrade() -> None:
    op.drop_index("ix_workflow_overrides_instance_id", table_name="workflow_overrides")
    op.drop_index("ix_workflow_overrides_case_id", table_name="workflow_overrides")
    op.drop_table("workflow_overrides")

    op.drop_constraint("uq_cases_property_auction_date", "cases", type_="unique")
    op.drop_index("ix_cases_canonical_key", table_name="cases")
    op.drop_column("cases", "canonical_key")
    op.drop_column("cases", "auction_date")
    op.drop_column("cases", "meta")
    op.drop_column("cases", "program_key")

    op.drop_index("ix_auction_imports_file_hash", table_name="auction_imports")
    op.drop_column("auction_imports", "file_hash")
