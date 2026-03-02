"""Member-facing program layer.

Revision ID: v3_member_layer
Revises: baseline_v2_full_schema
Create Date: 2026-02-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "v3_member_layer"
down_revision = "baseline_v2_full_schema"
branch_labels = None
depends_on = None


applicationstatus_enum = postgresql.ENUM(
    "started",
    "submitted",
    "needs_info",
    "qualified",
    "not_qualified",
    name="applicationstatus",
    create_type=False,
)

membershipstatus_enum = postgresql.ENUM(
    "active",
    "paused",
    "expired",
    "cancelled",
    name="membershipstatus",
    create_type=False,
)

installmentstatus_enum = postgresql.ENUM(
    "due",
    "paid_cash",
    "satisfied_contribution",
    "missed",
    "waived",
    name="installmentstatus",
    create_type=False,
)

credit_type_enum = postgresql.ENUM(
    "testimonial_video",
    "referral",
    "volunteer",
    "training_module",
    "other",
    name="credit_type",
    create_type=False,
)

checkintype_enum = postgresql.ENUM(
    "hardship_notice",
    "monthly_update",
    "support_request",
    name="checkintype",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    applicationstatus_enum.create(bind, checkfirst=True)
    membershipstatus_enum.create(bind, checkfirst=True)
    installmentstatus_enum.create(bind, checkfirst=True)
    credit_type_enum.create(bind, checkfirst=True)
    checkintype_enum.create(bind, checkfirst=True)

    op.create_table(
        "applications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("program_key", sa.Text(), nullable=False),
        sa.Column(
            "status",
            applicationstatus_enum,
            server_default=sa.text("'started'"),
            nullable=False,
        ),
        sa.Column("answers_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_applications"),
    )

    op.create_table(
        "memberships",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("program_key", sa.Text(), nullable=False),
        sa.Column("term_start", sa.Date(), nullable=False),
        sa.Column("term_end", sa.Date(), nullable=False),
        sa.Column("annual_price_cents", sa.Integer(), nullable=False),
        sa.Column("installment_cents", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            membershipstatus_enum,
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column("good_standing", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_memberships"),
    )

    op.create_table(
        "membership_installments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("membership_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            installmentstatus_enum,
            server_default=sa.text("'due'"),
            nullable=False,
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_membership_installments"),
    )

    op.create_table(
        "contribution_credits",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("membership_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("installment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("credit_type", credit_type_enum, nullable=False),
        sa.Column("amount_cents_equivalent", sa.Integer(), nullable=False),
        sa.Column("evidence_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_contribution_credits"),
    )

    op.create_table(
        "member_checkins",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("membership_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", checkintype_enum, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_member_checkins"),
    )

    op.create_table(
        "stability_assessments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("program_key", sa.Text(), nullable=False),
        sa.Column("equity_estimate", sa.Numeric(12, 2), nullable=True),
        sa.Column("equity_health_band", sa.Text(), nullable=True),
        sa.Column("stability_score", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.Text(), nullable=True),
        sa.Column("breakdown_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_stability_assessments"),
    )

    op.create_index("ix_applications_program_key", "applications", ["program_key"], unique=False)
    op.create_index("ix_applications_status", "applications", ["status"], unique=False)
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"], unique=False)
    op.create_index("ix_memberships_program_key", "memberships", ["program_key"], unique=False)
    op.create_index("ix_membership_installments_membership_id", "membership_installments", ["membership_id"], unique=False)
    op.create_index("ix_membership_installments_due_date", "membership_installments", ["due_date"], unique=False)
    op.create_index("ix_contribution_credits_membership_id", "contribution_credits", ["membership_id"], unique=False)
    op.create_index("ix_contribution_credits_installment_id", "contribution_credits", ["installment_id"], unique=False)
    op.create_index("ix_member_checkins_membership_id", "member_checkins", ["membership_id"], unique=False)
    op.create_index("ix_stability_assessments_user_id", "stability_assessments", ["user_id"], unique=False)
    op.create_index("ix_stability_assessments_program_key", "stability_assessments", ["program_key"], unique=False)
    op.create_index("ix_stability_assessments_created_at", "stability_assessments", ["created_at"], unique=False)

    op.create_index(
        "uq_memberships_active_user_program",
        "memberships",
        ["user_id", "program_key"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_foreign_key("fk_memberships_user_id_users", "memberships", "users", ["user_id"], ["id"])
    op.create_foreign_key(
        "fk_membership_installments_membership_id_memberships",
        "membership_installments",
        "memberships",
        ["membership_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_contribution_credits_membership_id_memberships",
        "contribution_credits",
        "memberships",
        ["membership_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_contribution_credits_installment_id_membership_installments",
        "contribution_credits",
        "membership_installments",
        ["installment_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_contribution_credits_evidence_document_id_documents",
        "contribution_credits",
        "documents",
        ["evidence_document_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_member_checkins_membership_id_memberships",
        "member_checkins",
        "memberships",
        ["membership_id"],
        ["id"],
    )
    op.create_foreign_key("fk_stability_assessments_user_id_users", "stability_assessments", "users", ["user_id"], ["id"])
    op.create_foreign_key(
        "fk_stability_assessments_property_id_properties",
        "stability_assessments",
        "properties",
        ["property_id"],
        ["id"],
    )

    op.execute(
        """
        CREATE VIEW active_stable_members AS
        WITH latest_stability AS (
            SELECT DISTINCT ON (sa.user_id, sa.program_key)
                sa.user_id,
                sa.program_key,
                sa.stability_score,
                sa.created_at AS stability_created_at
            FROM stability_assessments sa
            ORDER BY sa.user_id, sa.program_key, sa.created_at DESC
        )
        SELECT
            m.id AS membership_id,
            m.user_id,
            m.program_key,
            ls.stability_score,
            GREATEST(
                COALESCE(mi.last_paid_cash_at, to_timestamp(0)),
                COALESCE(cc.last_contribution_at, to_timestamp(0)),
                COALESCE(d.last_document_at, to_timestamp(0)),
                COALESCE(mc.last_checkin_at, to_timestamp(0)),
                COALESCE(tqa.last_training_at, to_timestamp(0))
            ) AS last_activity_at
        FROM memberships m
        JOIN latest_stability ls
            ON ls.user_id = m.user_id
           AND ls.program_key = m.program_key
        LEFT JOIN (
            SELECT membership_id, MAX(paid_at) AS last_paid_cash_at
            FROM membership_installments
            WHERE status = 'paid_cash'
            GROUP BY membership_id
        ) mi ON mi.membership_id = m.id
        LEFT JOIN (
            SELECT membership_id, MAX(created_at) AS last_contribution_at
            FROM contribution_credits
            GROUP BY membership_id
        ) cc ON cc.membership_id = m.id
        LEFT JOIN (
            SELECT c.created_by AS user_id, c.program_key, MAX(d.uploaded_at) AS last_document_at
            FROM documents d
            JOIN cases c ON c.id = d.case_id
            GROUP BY c.created_by, c.program_key
        ) d ON d.user_id = m.user_id AND d.program_key = m.program_key
        LEFT JOIN (
            SELECT membership_id, MAX(created_at) AS last_checkin_at
            FROM member_checkins
            GROUP BY membership_id
        ) mc ON mc.membership_id = m.id
        LEFT JOIN (
            SELECT user_id, MAX(created_at) AS last_training_at
            FROM training_quiz_attempts
            GROUP BY user_id
        ) tqa ON tqa.user_id = m.user_id
        WHERE m.status = 'active'
          AND m.good_standing = true
          AND ls.stability_score >= 65
          AND GREATEST(
                COALESCE(mi.last_paid_cash_at, to_timestamp(0)),
                COALESCE(cc.last_contribution_at, to_timestamp(0)),
                COALESCE(d.last_document_at, to_timestamp(0)),
                COALESCE(mc.last_checkin_at, to_timestamp(0)),
                COALESCE(tqa.last_training_at, to_timestamp(0))
          ) >= now() - interval '30 days';
        """
    )

    op.execute(
        """
        INSERT INTO workflow_templates (id, program_key, name, template_version, created_at)
        SELECT gen_random_uuid(), 'homeowner_protection', 'Homeowner Protection Program', 1, now()
        WHERE NOT EXISTS (
            SELECT 1
            FROM workflow_templates
            WHERE program_key = 'homeowner_protection' AND template_version = 1
        );
        """
    )

    op.execute(
        """
        INSERT INTO workflow_steps (
            id,
            template_id,
            step_key,
            display_name,
            responsible_role,
            required_documents,
            required_actions,
            blocking_conditions,
            kanban_column,
            order_index,
            auto_advance,
            sla_days,
            created_at
        )
        SELECT
            gen_random_uuid(),
            wt.id,
            s.step_key,
            s.display_name,
            s.responsible_role::workflowresponsiblerole,
            '[]'::jsonb,
            '[]'::jsonb,
            '[]'::jsonb,
            s.kanban_column,
            s.order_index,
            false,
            30,
            now()
        FROM workflow_templates wt
        JOIN (
            VALUES
                ('qualification_submitted', 'Qualification Submitted', 'operator', 'intake', 1),
                ('identity_verified', 'Identity Verified', 'operator', 'verification', 2),
                ('property_snapshot', 'Property Snapshot', 'operator', 'analysis', 3),
                ('baseline_stability_generated', 'Baseline Stability Generated', 'system', 'analysis', 4),
                ('plan_activated', 'Plan Activated', 'operator', 'activation', 5),
                ('monthly_checkin_cycle', 'Monthly Check-in Cycle', 'occupant', 'monitoring', 6)
        ) AS s(step_key, display_name, responsible_role, kanban_column, order_index)
            ON true
        WHERE wt.program_key = 'homeowner_protection'
          AND wt.template_version = 1
          AND NOT EXISTS (
              SELECT 1
              FROM workflow_steps ws
              WHERE ws.template_id = wt.id
                AND ws.step_key = s.step_key
          );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM workflow_steps
        WHERE template_id IN (
            SELECT id
            FROM workflow_templates
            WHERE program_key = 'homeowner_protection'
              AND template_version = 1
              AND name = 'Homeowner Protection Program'
        )
        AND step_key IN (
            'qualification_submitted',
            'identity_verified',
            'property_snapshot',
            'baseline_stability_generated',
            'plan_activated',
            'monthly_checkin_cycle'
        );
        """
    )

    op.execute(
        """
        DELETE FROM workflow_templates
        WHERE program_key = 'homeowner_protection'
          AND template_version = 1
          AND name = 'Homeowner Protection Program'
          AND NOT EXISTS (
              SELECT 1
              FROM workflow_steps ws
              WHERE ws.template_id = workflow_templates.id
          );
        """
    )

    op.execute("DROP VIEW IF EXISTS active_stable_members;")

    op.drop_constraint("fk_stability_assessments_property_id_properties", "stability_assessments", type_="foreignkey")
    op.drop_constraint("fk_stability_assessments_user_id_users", "stability_assessments", type_="foreignkey")
    op.drop_constraint("fk_member_checkins_membership_id_memberships", "member_checkins", type_="foreignkey")
    op.drop_constraint(
        "fk_contribution_credits_evidence_document_id_documents",
        "contribution_credits",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_contribution_credits_installment_id_membership_installments",
        "contribution_credits",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_contribution_credits_membership_id_memberships",
        "contribution_credits",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_membership_installments_membership_id_memberships",
        "membership_installments",
        type_="foreignkey",
    )
    op.drop_constraint("fk_memberships_user_id_users", "memberships", type_="foreignkey")

    op.drop_index("uq_memberships_active_user_program", table_name="memberships")

    op.drop_index("ix_stability_assessments_created_at", table_name="stability_assessments")
    op.drop_index("ix_stability_assessments_program_key", table_name="stability_assessments")
    op.drop_index("ix_stability_assessments_user_id", table_name="stability_assessments")
    op.drop_index("ix_member_checkins_membership_id", table_name="member_checkins")
    op.drop_index("ix_contribution_credits_installment_id", table_name="contribution_credits")
    op.drop_index("ix_contribution_credits_membership_id", table_name="contribution_credits")
    op.drop_index("ix_membership_installments_due_date", table_name="membership_installments")
    op.drop_index("ix_membership_installments_membership_id", table_name="membership_installments")
    op.drop_index("ix_memberships_program_key", table_name="memberships")
    op.drop_index("ix_memberships_user_id", table_name="memberships")
    op.drop_index("ix_applications_status", table_name="applications")
    op.drop_index("ix_applications_program_key", table_name="applications")

    op.drop_table("stability_assessments")
    op.drop_table("member_checkins")
    op.drop_table("contribution_credits")
    op.drop_table("membership_installments")
    op.drop_table("memberships")
    op.drop_table("applications")

    checkintype_enum.drop(op.get_bind(), checkfirst=True)
    credit_type_enum.drop(op.get_bind(), checkfirst=True)
    installmentstatus_enum.drop(op.get_bind(), checkfirst=True)
    membershipstatus_enum.drop(op.get_bind(), checkfirst=True)
    applicationstatus_enum.drop(op.get_bind(), checkfirst=True)
