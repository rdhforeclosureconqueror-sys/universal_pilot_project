"""add foreclosure workflow engine tables

Revision ID: 7a1d9d3b4c55
Revises: 6f4b2c1b2a8d
Create Date: 2026-02-17 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "7a1d9d3b4c55"
down_revision = "6f4b2c1b2a8d"
branch_labels = None
depends_on = None


workflow_responsible_role = sa.Enum("operator", "occupant", "system", "lender", name="workflowresponsiblerole", create_type=False)
workflow_step_status = sa.Enum("pending", "active", "blocked", "complete", name="workflowstepstatus", create_type=False)
workflow_responsible_role_ref = postgresql.ENUM(name="workflowresponsiblerole", create_type=False)
workflow_step_status_ref = postgresql.ENUM(name="workflowstepstatus", create_type=False)


def upgrade() -> None:
    workflow_responsible_role.create(op.get_bind(), checkfirst=True)
    workflow_step_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "workflow_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("program_key", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    op.create_index("ix_workflow_templates_program_key", "workflow_templates", ["program_key"])

    op.create_table(
        "workflow_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_templates.id"), nullable=False),
        sa.Column("step_key", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("responsible_role", workflow_responsible_role_ref, nullable=False),
        sa.Column("required_documents", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("required_actions", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("blocking_conditions", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("kanban_column", sa.String(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("auto_advance", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    op.create_index("ix_workflow_steps_template_id", "workflow_steps", ["template_id"])

    op.create_table(
        "case_workflow_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False, unique=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workflow_templates.id"), nullable=False),
        sa.Column("current_step_key", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_case_workflow_instances_case_id", "case_workflow_instances", ["case_id"])
    op.create_index("ix_case_workflow_instances_template_id", "case_workflow_instances", ["template_id"])

    op.create_table(
        "case_workflow_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("instance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("case_workflow_instances.id"), nullable=False),
        sa.Column("step_key", sa.String(), nullable=False),
        sa.Column("status", workflow_step_status_ref, nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("block_reason", sa.String(), nullable=True),
    )
    op.create_index("ix_case_workflow_progress_instance_id", "case_workflow_progress", ["instance_id"])

    op.execute(
        """
        INSERT INTO workflow_templates (id, program_key, name)
        VALUES (
            '11111111-1111-1111-1111-111111111111'::uuid,
            'foreclosure_stabilization_v1',
            'Foreclosure Stabilization v1'
        )
        ON CONFLICT DO NOTHING
        """
    )

    op.execute(
        """
        WITH t AS (
            SELECT id FROM workflow_templates WHERE program_key='foreclosure_stabilization_v1' LIMIT 1
        )
        INSERT INTO workflow_steps (
            id, template_id, step_key, display_name, responsible_role,
            required_documents, required_actions, blocking_conditions,
            kanban_column, order_index, auto_advance
        )
        SELECT s.id::uuid, t.id, s.step_key, s.display_name, s.responsible_role::workflowresponsiblerole,
               s.required_documents::json, s.required_actions::json, s.blocking_conditions::json,
               s.kanban_column, s.order_index, s.auto_advance
        FROM t
        CROSS JOIN (
            VALUES
                ('00000000-0000-0000-0000-000000000001','pdf_ingestion','PDF Ingestion','system','[]','["auction_import_created","lead_created","case_created"]','[]','📥 Lead Ingested',1,true),
                ('00000000-0000-0000-0000-000000000002','contact_homeowner','Contact Homeowner','operator','[]','["contact_attempt_logged","homeowner_response_logged"]','["requires_valid_contact_channel"]','📞 Contact & Qualification',2,false),
                ('00000000-0000-0000-0000-000000000003','qualification_review','Qualification Review','operator','["foreclosure_notice","occupancy_confirmation","id_verification"]','["qualification_review_completed"]','[]','📄 Intake Complete',3,false),
                ('00000000-0000-0000-0000-000000000004','leaseback_execution','Leaseback Execution','operator','["leaseback_signed","consent_signed"]','["leaseback_signed","consent_signed"]','[]','⚖️ Stabilization Setup',4,true),
                ('00000000-0000-0000-0000-000000000005','stabilization_monitoring','Stabilization Monitoring','operator','[]','["payment_logs_verified","compliance_window_met"]','[]','🏠 Leaseback Active',5,false),
                ('00000000-0000-0000-0000-000000000006','rehab_planning','Rehab Planning','operator','["rehab_scope_uploaded"]','["rehab_classification_set"]','[]','🔨 Rehab Planning',6,false),
                ('00000000-0000-0000-0000-000000000007','rehab_execution','Rehab Execution','operator','[]','["milestone_logs_recorded","contractor_verified","rehab_completed"]','[]','🛠 Rehab In Progress',7,false),
                ('00000000-0000-0000-0000-000000000008','performance_window','Performance Window','system','[]','["performance_window_complete"]','["compliance_overdue"]','📊 Performance Window',8,false),
                ('00000000-0000-0000-0000-000000000009','refinance_ready','Refinance Ready','system','["readiness_packet"]','["pfdr_ledger_reconciled","shared_equity_active","no_unresolved_flags","documents_complete"]','[]','💰 Refinance Ready',9,false),
                ('00000000-0000-0000-0000-000000000010','completion','Completion','lender','[]','["refinance_completed","shared_equity_extinguished","pfdr_recovered","workflow_completed"]','[]','🎓 Completed',10,false)
        ) AS s(id, step_key, display_name, responsible_role, required_documents, required_actions, blocking_conditions, kanban_column, order_index, auto_advance)
        WHERE NOT EXISTS (
            SELECT 1
            FROM workflow_steps ws
            WHERE ws.template_id = t.id
              AND ws.step_key = s.step_key
        )
        """
    )


def downgrade() -> None:
    op.drop_index("ix_case_workflow_progress_instance_id", table_name="case_workflow_progress")
    op.drop_table("case_workflow_progress")

    op.drop_index("ix_case_workflow_instances_template_id", table_name="case_workflow_instances")
    op.drop_index("ix_case_workflow_instances_case_id", table_name="case_workflow_instances")
    op.drop_table("case_workflow_instances")

    op.drop_index("ix_workflow_steps_template_id", table_name="workflow_steps")
    op.drop_table("workflow_steps")

    op.drop_index("ix_workflow_templates_program_key", table_name="workflow_templates")
    op.drop_table("workflow_templates")

    workflow_step_status.drop(op.get_bind(), checkfirst=True)
    workflow_responsible_role.drop(op.get_bind(), checkfirst=True)
