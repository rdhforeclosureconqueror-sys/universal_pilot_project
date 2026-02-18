"""
Baseline migration - consolidated schema

Revision ID: baseline_001
Revises: None
Create Date: 2026-02-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "baseline_001"
down_revision = None
branch_labels = None
depends_on = None


workflow_responsible_role = sa.Enum(
    "operator", "occupant", "system", "lender",
    name="workflowresponsiblerole"
)

workflow_step_status = sa.Enum(
    "pending", "active", "blocked", "complete",
    name="workflowstepstatus"
)


def upgrade():

    # --------------------------------------------------
    # ENUMS
    # --------------------------------------------------

    workflow_responsible_role.create(op.get_bind(), checkfirst=True)
    workflow_step_status.create(op.get_bind(), checkfirst=True)

    # --------------------------------------------------
    # WORKFLOW TABLES
    # --------------------------------------------------

    op.create_table(
        "workflow_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("program_key", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()")),
    )

    op.create_table(
        "workflow_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("workflow_templates.id"), nullable=False),
        sa.Column("step_key", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("responsible_role", workflow_responsible_role, nullable=False),
        sa.Column("required_documents", sa.JSON(),
                  server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("required_actions", sa.JSON(),
                  server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("blocking_conditions", sa.JSON(),
                  server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("kanban_column", sa.String(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("auto_advance", sa.Boolean(),
                  server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()")),
    )

    op.create_table(
        "case_workflow_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("cases.id"), nullable=False, unique=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("workflow_templates.id"), nullable=False),
        sa.Column("current_step_key", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "case_workflow_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("instance_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("case_workflow_instances.id"), nullable=False),
        sa.Column("step_key", sa.String(), nullable=False),
        sa.Column("status", workflow_step_status,
                  server_default="pending", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("block_reason", sa.String()),
    )

    # --------------------------------------------------
    # LEADS ADDITIONS (merged into table definition)
    # --------------------------------------------------

    op.add_column("auction_imports",
        sa.Column("file_type", sa.String())
    )

    op.add_column("leads",
        sa.Column("county", sa.String())
    )
    op.add_column("leads",
        sa.Column("trustee", sa.String())
    )
    op.add_column("leads",
        sa.Column("mortgagor", sa.String())
    )
    op.add_column("leads",
        sa.Column("mortgagee", sa.String())
    )
    op.add_column("leads",
        sa.Column("auction_date", sa.DateTime(timezone=True))
    )
    op.add_column("leads",
        sa.Column("case_number", sa.String())
    )
    op.add_column("leads",
        sa.Column("opening_bid", sa.Float())
    )


def downgrade():
    op.drop_table("case_workflow_progress")
    op.drop_table("case_workflow_instances")
    op.drop_table("workflow_steps")
    op.drop_table("workflow_templates")

    workflow_step_status.drop(op.get_bind(), checkfirst=True)
    workflow_responsible_role.drop(op.get_bind(), checkfirst=True)
