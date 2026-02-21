"""workflow system + ingestion hardening

Revision ID: 001_workflow_system
Revises: "baseline_001"
Create Date: 2026-02-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "001_workflow_system"
down_revision = "baseline_001"
branch_labels = None
depends_on = None


# -------------------------------------------------
# ENUMS
# -------------------------------------------------

workflow_responsible_role = sa.Enum(
    "operator",
    "occupant",
    "system",
    "lender",
    name="workflowresponsiblerole",
)

workflow_step_status = sa.Enum(
    "pending",
    "active",
    "blocked",
    "complete",
    name="workflowstepstatus",
)

workflow_override_category = sa.Enum(
    "data_correction",
    "legal_exception",
    "executive_directive",
    "system_recovery",
    name="workflowoverridecategory",
)


# -------------------------------------------------
# UPGRADE
# -------------------------------------------------

def upgrade() -> None:

    bind = op.get_bind()

    # Create enums
    workflow_responsible_role.create(bind, checkfirst=True)
    workflow_step_status.create(bind, checkfirst=True)
    workflow_override_category.create(bind, checkfirst=True)

    # -------------------------------------------------
    # WORKFLOW CORE TABLES
    # -------------------------------------------------

    op.create_table(
        "workflow_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("program_key", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("template_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_index(
        "ix_workflow_templates_program_key",
        "workflow_templates",
        ["program_key"],
    )

    op.create_table(
        "workflow_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("workflow_templates.id"), nullable=False),
        sa.Column("step_key", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("responsible_role", workflow_responsible_role, nullable=False),
        sa.Column("required_documents", sa.JSON(), nullable=False,
                  server_default=sa.text("'[]'::json")),
        sa.Column("required_actions", sa.JSON(), nullable=False,
                  server_default=sa.text("'[]'::json")),
        sa.Column("blocking_conditions", sa.JSON(), nullable=False,
                  server_default=sa.text("'[]'::json")),
        sa.Column("kanban_column", sa.String(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("auto_advance", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("sla_days", sa.Integer(), nullable=False,
                  server_default="30"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()")),
    )

    op.create_index(
        "ix_workflow_steps_template_id",
        "workflow_steps",
        ["template_id"],
    )

    op.create_table(
        "case_workflow_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  primary_key=True, nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("cases.id"), nullable=False, unique=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("workflow_templates.id"), nullable=False),
        sa.Column("current_step_key", sa.String(), nullable=False),
        sa.Column("locked_template_version", sa.Integer(),
                  nullable=False, server_default="1"),
        sa.Column("started_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    op.create_index(
        "ix_case_workflow_instances_case_id",
        "case_workflow_instances",
        ["case_id"],
    )

    op.create_table(
        "case_workflow_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  primary_key=True, nullable=False),
        sa.Column("instance_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("case_workflow_instances.id"), nullable=False),
        sa.Column("step_key", sa.String(), nullable=False),
        sa.Column("status", workflow_step_status,
                  nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("block_reason", sa.String()),
    )

    op.create_index(
        "ix_case_workflow_progress_instance_id",
        "case_workflow_progress",
        ["instance_id"],
    )

    # -------------------------------------------------
    # WORKFLOW OVERRIDES
    # -------------------------------------------------

    op.create_table(
        "workflow_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  primary_key=True, nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("instance_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("case_workflow_instances.id"), nullable=False),
        sa.Column("from_step_key", sa.String(), nullable=False),
        sa.Column("to_step_key", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("reason_category", workflow_override_category,
                  nullable=False, server_default="system_recovery"),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True),
                  nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()")),
    )

    op.create_index(
        "ix_workflow_overrides_case_id",
        "workflow_overrides",
        ["case_id"],
    )

    op.create_index(
        "ix_workflow_overrides_instance_id",
        "workflow_overrides",
        ["instance_id"],
    )

    # -------------------------------------------------
    # INGESTION HARDENING
    # -------------------------------------------------

    op.add_column(
        "auction_imports",
        sa.Column("file_hash", sa.String(), nullable=True),
    )

    op.create_index(
        "ix_auction_imports_file_hash",
        "auction_imports",
        ["file_hash"],
        unique=True,
    )

    op.add_column("cases", sa.Column("auction_date",
                                     sa.DateTime(timezone=True)))
    op.add_column("cases", sa.Column("canonical_key", sa.String()))

    op.create_index(
        "ix_cases_canonical_key",
        "cases",
        ["canonical_key"],
        unique=True,
    )

    op.create_unique_constraint(
        "uq_cases_property_auction_date",
        "cases",
        ["property_id", "auction_date"],
    )

    # -------------------------------------------------
    # INGESTION METRICS
    # -------------------------------------------------

    op.create_table(
        "ingestion_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  primary_key=True, nullable=False),
        sa.Column("metric_type", sa.String(), nullable=False),
        sa.Column("source", sa.String()),
        sa.Column("file_hash", sa.String()),
        sa.Column("file_name", sa.String()),
        sa.Column("count_value", sa.Integer()),
        sa.Column("duration_seconds", sa.Float()),
        sa.Column("notes", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()")),
    )

    op.create_index(
        "ix_ingestion_metrics_metric_type",
        "ingestion_metrics",
        ["metric_type"],
    )


# -------------------------------------------------
# DOWNGRADE
# -------------------------------------------------

def downgrade() -> None:

    op.drop_index("ix_ingestion_metrics_metric_type",
                  table_name="ingestion_metrics")
    op.drop_table("ingestion_metrics")

    op.drop_constraint("uq_cases_property_auction_date",
                       "cases", type_="unique")
    op.drop_index("ix_cases_canonical_key", table_name="cases")
    op.drop_column("cases", "canonical_key")
    op.drop_column("cases", "auction_date")

    op.drop_index("ix_auction_imports_file_hash",
                  table_name="auction_imports")
    op.drop_column("auction_imports", "file_hash")

    op.drop_index("ix_workflow_overrides_instance_id",
                  table_name="workflow_overrides")
    op.drop_index("ix_workflow_overrides_case_id",
                  table_name="workflow_overrides")
    op.drop_table("workflow_overrides")

    op.drop_index("ix_case_workflow_progress_instance_id",
                  table_name="case_workflow_progress")
    op.drop_table("case_workflow_progress")

    op.drop_index("ix_case_workflow_instances_case_id",
                  table_name="case_workflow_instances")
    op.drop_table("case_workflow_instances")

    op.drop_index("ix_workflow_steps_template_id",
                  table_name="workflow_steps")
    op.drop_table("workflow_steps")

    op.drop_index("ix_workflow_templates_program_key",
                  table_name="workflow_templates")
    op.drop_table("workflow_templates")

    workflow_override_category.drop(op.get_bind(), checkfirst=True)
    workflow_step_status.drop(op.get_bind(), checkfirst=True)
    workflow_responsible_role.drop(op.get_bind(), checkfirst=True)
