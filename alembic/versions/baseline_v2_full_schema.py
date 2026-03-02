"""Canonical full schema baseline.

Revision ID: baseline_v2_full_schema
Revises: None
Create Date: 2026-02-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "baseline_v2_full_schema"
down_revision = None
branch_labels = None
depends_on = None


casestatus_enum = postgresql.ENUM(
    "intake_submitted",
    "intake_incomplete",
    "under_review",
    "in_progress",
    "program_completed_positive_outcome",
    "case_closed_other_outcome",
    "auction_intake",
    name="casestatus",
    create_type=False,
)

documenttype_enum = postgresql.ENUM(
    "id_verification",
    "income_verification",
    "lease_or_mortgage",
    "foreclosure_notice",
    "eviction_notice",
    "signed_consent",
    "taskcheck_evidence",
    "training_proof",
    "system_doc",
    "other",
    name="documenttype",
    create_type=False,
)

referralstatus_enum = postgresql.ENUM(
    "draft",
    "queued",
    "sent",
    "failed",
    "cancelled",
    name="referralstatus",
    create_type=False,
)

userrole_enum = postgresql.ENUM(
    "case_worker",
    "referral_coordinator",
    "admin",
    "audit_steward",
    "ai_policy_chair",
    "partner_org",
    name="userrole",
    create_type=False,
)

workflowoverridecategory_enum = postgresql.ENUM(
    "data_correction",
    "legal_exception",
    "executive_directive",
    "system_recovery",
    name="workflowoverridecategory",
    create_type=False,
)

workflowresponsiblerole_enum = postgresql.ENUM(
    "operator",
    "occupant",
    "system",
    "lender",
    name="workflowresponsiblerole",
    create_type=False,
)

workflowstepstatus_enum = postgresql.ENUM(
    "pending",
    "active",
    "blocked",
    "complete",
    name="workflowstepstatus",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    casestatus_enum.create(bind, checkfirst=True)
    documenttype_enum.create(bind, checkfirst=True)
    referralstatus_enum.create(bind, checkfirst=True)
    userrole_enum.create(bind, checkfirst=True)
    workflowoverridecategory_enum.create(bind, checkfirst=True)
    workflowresponsiblerole_enum.create(bind, checkfirst=True)
    workflowstepstatus_enum.create(bind, checkfirst=True)

    op.create_table(
        "ai_activity_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("policy_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ai_role", sa.String(), nullable=True),
        sa.Column("model_provider", sa.String(), nullable=True),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("model_version", sa.String(), nullable=True),
        sa.Column("prompt_hash", sa.String(), nullable=True),
        sa.Column("policy_rule_id", sa.String(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("human_override", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("incident_type", sa.String(), nullable=True),
        sa.Column("admin_review_required", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_ai_activity_logs"),
    )

    op.create_table(
        "auction_imports",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=True),
        sa.Column("file_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("file_type", sa.String(), nullable=True),
        sa.Column("file_hash", sa.String(), nullable=True),
        sa.Column("status", sa.String(), server_default=sa.text("'received'"), nullable=False),
        sa.Column("records_created", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_auction_imports"),
    )

    op.create_table(
        "bot_commands",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("target_bot", sa.String(), nullable=False),
        sa.Column("command", sa.String(), nullable=False),
        sa.Column("args_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("priority", sa.Integer(), server_default=sa.text("10"), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_bot_commands"),
    )

    op.create_table(
        "bot_inbound_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("source_bot", sa.String(), nullable=False),
        sa.Column("payload_hash", sa.String(), nullable=True),
        sa.Column("type", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_bot_inbound_logs"),
    )

    op.create_table(
        "bot_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("last_crawl", sa.DateTime(timezone=True), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_bot_pages"),
    )

    op.create_table(
        "bot_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("bot", sa.String(), nullable=False),
        sa.Column("level", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=True),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("details_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_bot_reports"),
    )

    op.create_table(
        "bot_settings",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("key", name="pk_bot_settings"),
    )

    op.create_table(
        "bot_triggers",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("metric", sa.String(), nullable=False),
        sa.Column("operator", sa.String(), server_default=sa.text("'>='"), nullable=False),
        sa.Column("threshold", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.Column("priority", sa.Integer(), server_default=sa.text("10"), nullable=False),
        sa.Column("target_bot", sa.String(), nullable=False),
        sa.Column("command", sa.String(), nullable=False),
        sa.Column("args_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_bot_triggers"),
    )

    op.create_table(
        "certifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cert_key", sa.String(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_certifications"),
    )

    op.create_table(
        "ingestion_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("metric_type", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("file_hash", sa.String(), nullable=True),
        sa.Column("file_name", sa.String(), nullable=True),
        sa.Column("count_value", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_metrics"),
    )

    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("lead_id", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("zip", sa.String(), nullable=True),
        sa.Column("apn", sa.String(), nullable=True),
        sa.Column("county", sa.String(), nullable=True),
        sa.Column("trustee", sa.String(), nullable=True),
        sa.Column("mortgagor", sa.String(), nullable=True),
        sa.Column("mortgagee", sa.String(), nullable=True),
        sa.Column("auction_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("case_number", sa.String(), nullable=True),
        sa.Column("opening_bid", sa.Float(), nullable=True),
        sa.Column("list_price", sa.Float(), nullable=True),
        sa.Column("arrears", sa.Float(), nullable=True),
        sa.Column("equity_pct", sa.Float(), nullable=True),
        sa.Column("arv", sa.Float(), nullable=True),
        sa.Column("mao", sa.Float(), nullable=True),
        sa.Column("spread_pct", sa.Float(), nullable=True),
        sa.Column("tier", sa.String(), nullable=True),
        sa.Column("south_dallas_override", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("exit_strategy", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_leads"),
    )

    op.create_table(
        "outbox_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("event_type", sa.String(), nullable=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("dedupe_key", sa.String(), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("max_attempts", sa.Integer(), server_default=sa.text("3"), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_outbox_queue"),
    )

    op.create_table(
        "partners",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("contact_email", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_partners"),
    )

    op.create_table(
        "policy_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("program_key", sa.String(), nullable=False),
        sa.Column("version_tag", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_policy_versions"),
    )

    op.create_table(
        "properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("zip", sa.String(), nullable=False),
        sa.Column("county", sa.String(), nullable=True),
        sa.Column("property_type", sa.String(), nullable=True),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("sqft", sa.Integer(), nullable=True),
        sa.Column("beds", sa.Float(), nullable=True),
        sa.Column("baths", sa.Float(), nullable=True),
        sa.Column("assessed_value", sa.Integer(), nullable=True),
        sa.Column("mortgagor", sa.String(), nullable=True),
        sa.Column("mortgagee", sa.String(), nullable=True),
        sa.Column("trustee", sa.String(), nullable=True),
        sa.Column("loan_type", sa.String(), nullable=True),
        sa.Column("interest_rate", sa.Float(), nullable=True),
        sa.Column("orig_loan_amount", sa.Integer(), nullable=True),
        sa.Column("est_balance", sa.Integer(), nullable=True),
        sa.Column("auction_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auction_time", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_properties"),
    )

    op.create_table(
        "training_quiz_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lesson_key", sa.String(), nullable=False),
        sa.Column("answers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("passed", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_training_quiz_attempts"),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("role", userrole_enum, nullable=True),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )

    op.create_table(
        "workflow_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("program_key", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("template_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_workflow_templates"),
    )

    op.create_table(
        "cert_revocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("certification_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason_code", sa.String(), nullable=False),
        sa.Column("revoked_by_system", sa.Boolean(), server_default=sa.text("true"), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_cert_revocations"),
    )

    op.create_table(
        "cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("status", casestatus_enum, nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("program_type", sa.String(), nullable=True),
        sa.Column("program_key", sa.String(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("case_type", sa.String(), nullable=True),
        sa.Column("policy_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("auction_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canonical_key", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_cases"),
    )

    op.create_table(
        "workflow_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_key", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("responsible_role", workflowresponsiblerole_enum, nullable=False),
        sa.Column("required_documents", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("required_actions", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("blocking_conditions", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("kanban_column", sa.String(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("auto_advance", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("sla_days", sa.Integer(), server_default=sa.text("30"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_workflow_steps"),
    )

    op.create_table(
        "ai_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("equity", sa.Numeric(12, 2), nullable=False),
        sa.Column("strategy", sa.String(), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_ai_scores"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_is_ai", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("reason_code", sa.String(), nullable=False),
        sa.Column("before_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("policy_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
    )

    op.create_table(
        "case_workflow_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("locked_template_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("current_step_key", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_case_workflow_instances"),
    )

    op.create_table(
        "consent_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("granted_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_consent_records"),
    )

    op.create_table(
        "deal_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("tier", sa.String(), nullable=False),
        sa.Column("exit_strategy", sa.String(), nullable=False),
        sa.Column("urgency_days", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_deal_scores"),
    )

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doc_type", documenttype_enum, nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("file_url", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
    )

    op.create_table(
        "referrals",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", referralstatus_enum, server_default=sa.text("'draft'"), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_referrals"),
    )

    op.create_table(
        "role_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_name", sa.String(), nullable=False),
        sa.Column("scope_case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scope_program_key", sa.String(), nullable=True),
        sa.Column("assumed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_role_sessions"),
    )

    op.create_table(
        "taskchecks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("skill_key", sa.String(), nullable=False),
        sa.Column("passed", sa.Boolean(), server_default=sa.text("false"), nullable=True),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_taskchecks"),
    )

    op.create_table(
        "case_workflow_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("instance_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_key", sa.String(), nullable=False),
        sa.Column("status", workflowstepstatus_enum, server_default=sa.text("'pending'"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("block_reason", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_case_workflow_progress"),
    )

    op.create_table(
        "workflow_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instance_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_step_key", sa.String(), nullable=False),
        sa.Column("to_step_key", sa.String(), nullable=False),
        sa.Column("reason_category", workflowoverridecategory_enum, nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_workflow_overrides"),
    )

    op.create_index("ix_auction_imports_file_hash", "auction_imports", ["file_hash"], unique=True)
    op.create_index("ix_bot_commands_created_at", "bot_commands", ["created_at"], unique=False)
    op.create_index("ix_bot_inbound_logs_created_at", "bot_inbound_logs", ["created_at"], unique=False)
    op.create_index("ix_bot_reports_created_at", "bot_reports", ["created_at"], unique=False)
    op.create_index("ix_ingestion_metrics_metric_type", "ingestion_metrics", ["metric_type"], unique=False)
    op.create_index("ix_properties_external_id", "properties", ["external_id"], unique=True)
    op.create_index("ix_workflow_templates_program_key", "workflow_templates", ["program_key"], unique=False)
    op.create_index("ix_cases_canonical_key", "cases", ["canonical_key"], unique=True)
    op.create_index("ix_workflow_steps_template_id", "workflow_steps", ["template_id"], unique=False)
    op.create_index("ix_case_workflow_instances_case_id", "case_workflow_instances", ["case_id"], unique=True)
    op.create_index("ix_case_workflow_instances_template_id", "case_workflow_instances", ["template_id"], unique=False)
    op.create_index("ix_workflow_overrides_case_id", "workflow_overrides", ["case_id"], unique=False)
    op.create_index("ix_workflow_overrides_instance_id", "workflow_overrides", ["instance_id"], unique=False)
    op.create_index("ix_case_workflow_progress_instance_id", "case_workflow_progress", ["instance_id"], unique=False)

    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.create_unique_constraint("uq_leads_lead_id", "leads", ["lead_id"])
    op.create_unique_constraint("uq_outbox_queue_dedupe_key", "outbox_queue", ["dedupe_key"])
    op.create_unique_constraint("uq_cases_property_id_auction_date", "cases", ["property_id", "auction_date"])

    op.create_foreign_key("fk_certifications_user_id_users", "certifications", "users", ["user_id"], ["id"])
    op.create_foreign_key("fk_cert_revocations_certification_id_certifications", "cert_revocations", "certifications", ["certification_id"], ["id"])
    op.create_foreign_key("fk_cases_created_by_users", "cases", "users", ["created_by"], ["id"])
    op.create_foreign_key("fk_cases_policy_version_id_policy_versions", "cases", "policy_versions", ["policy_version_id"], ["id"])
    op.create_foreign_key("fk_cases_property_id_properties", "cases", "properties", ["property_id"], ["id"])
    op.create_foreign_key("fk_workflow_steps_template_id_workflow_templates", "workflow_steps", "workflow_templates", ["template_id"], ["id"])
    op.create_foreign_key("fk_ai_scores_case_id_cases", "ai_scores", "cases", ["case_id"], ["id"])
    op.create_foreign_key("fk_ai_activity_logs_case_id_cases", "ai_activity_logs", "cases", ["case_id"], ["id"])
    op.create_foreign_key("fk_ai_activity_logs_policy_version_id_policy_versions", "ai_activity_logs", "policy_versions", ["policy_version_id"], ["id"])
    op.create_foreign_key("fk_audit_logs_case_id_cases", "audit_logs", "cases", ["case_id"], ["id"])
    op.create_foreign_key("fk_audit_logs_policy_version_id_policy_versions", "audit_logs", "policy_versions", ["policy_version_id"], ["id"])
    op.create_foreign_key("fk_case_workflow_instances_case_id_cases", "case_workflow_instances", "cases", ["case_id"], ["id"])
    op.create_foreign_key("fk_case_workflow_instances_template_id_workflow_templates", "case_workflow_instances", "workflow_templates", ["template_id"], ["id"])
    op.create_foreign_key("fk_consent_records_case_id_cases", "consent_records", "cases", ["case_id"], ["id"])
    op.create_foreign_key("fk_deal_scores_property_id_properties", "deal_scores", "properties", ["property_id"], ["id"])
    op.create_foreign_key("fk_deal_scores_case_id_cases", "deal_scores", "cases", ["case_id"], ["id"])
    op.create_foreign_key("fk_documents_case_id_cases", "documents", "cases", ["case_id"], ["id"])
    op.create_foreign_key("fk_documents_uploaded_by_users", "documents", "users", ["uploaded_by"], ["id"])
    op.create_foreign_key("fk_referrals_case_id_cases", "referrals", "cases", ["case_id"], ["id"])
    op.create_foreign_key("fk_referrals_partner_id_partners", "referrals", "partners", ["partner_id"], ["id"])
    op.create_foreign_key("fk_role_sessions_user_id_users", "role_sessions", "users", ["user_id"], ["id"])
    op.create_foreign_key("fk_role_sessions_scope_case_id_cases", "role_sessions", "cases", ["scope_case_id"], ["id"])
    op.create_foreign_key("fk_taskchecks_case_id_cases", "taskchecks", "cases", ["case_id"], ["id"])
    op.create_foreign_key("fk_training_quiz_attempts_user_id_users", "training_quiz_attempts", "users", ["user_id"], ["id"])
    op.create_foreign_key("fk_outbox_queue_case_id_cases", "outbox_queue", "cases", ["case_id"], ["id"])
    op.create_foreign_key("fk_case_workflow_progress_instance_id_case_workflow_instances", "case_workflow_progress", "case_workflow_instances", ["instance_id"], ["id"])
    op.create_foreign_key("fk_workflow_overrides_case_id_cases", "workflow_overrides", "cases", ["case_id"], ["id"])
    op.create_foreign_key("fk_workflow_overrides_instance_id_case_workflow_instances", "workflow_overrides", "case_workflow_instances", ["instance_id"], ["id"])

    op.execute(
        """
        CREATE OR REPLACE FUNCTION enforce_workflow_override_limit()
        RETURNS trigger AS $$
        DECLARE
            override_count INTEGER;
        BEGIN
            SELECT COUNT(*) INTO override_count
            FROM workflow_overrides
            WHERE case_id = NEW.case_id;

            IF override_count >= 3 THEN
                RAISE EXCEPTION
                'workflow override limit exceeded for case_id=%',
                NEW.case_id;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_documents_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION
            'documents are immutable; operation=% is not allowed',
            TG_OP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_audit_logs_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION
            'audit_logs are immutable; operation=% is not allowed',
            TG_OP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_enforce_workflow_override_limit
        BEFORE INSERT ON workflow_overrides
        FOR EACH ROW
        EXECUTE FUNCTION enforce_workflow_override_limit();
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_prevent_documents_update
        BEFORE UPDATE ON documents
        FOR EACH ROW
        EXECUTE FUNCTION prevent_documents_mutation();
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_prevent_documents_delete
        BEFORE DELETE ON documents
        FOR EACH ROW
        EXECUTE FUNCTION prevent_documents_mutation();
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_prevent_audit_logs_update
        BEFORE UPDATE ON audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_logs_mutation();
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_prevent_audit_logs_delete
        BEFORE DELETE ON audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_logs_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_audit_logs_delete ON audit_logs;")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_audit_logs_update ON audit_logs;")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_documents_delete ON documents;")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_documents_update ON documents;")
    op.execute("DROP TRIGGER IF EXISTS trg_enforce_workflow_override_limit ON workflow_overrides;")

    op.execute("DROP FUNCTION IF EXISTS prevent_audit_logs_mutation();")
    op.execute("DROP FUNCTION IF EXISTS prevent_documents_mutation();")
    op.execute("DROP FUNCTION IF EXISTS enforce_workflow_override_limit();")

    op.drop_constraint("fk_workflow_overrides_instance_id_case_workflow_instances", "workflow_overrides", type_="foreignkey")
    op.drop_constraint("fk_workflow_overrides_case_id_cases", "workflow_overrides", type_="foreignkey")
    op.drop_constraint("fk_case_workflow_progress_instance_id_case_workflow_instances", "case_workflow_progress", type_="foreignkey")
    op.drop_constraint("fk_outbox_queue_case_id_cases", "outbox_queue", type_="foreignkey")
    op.drop_constraint("fk_training_quiz_attempts_user_id_users", "training_quiz_attempts", type_="foreignkey")
    op.drop_constraint("fk_taskchecks_case_id_cases", "taskchecks", type_="foreignkey")
    op.drop_constraint("fk_role_sessions_scope_case_id_cases", "role_sessions", type_="foreignkey")
    op.drop_constraint("fk_role_sessions_user_id_users", "role_sessions", type_="foreignkey")
    op.drop_constraint("fk_referrals_partner_id_partners", "referrals", type_="foreignkey")
    op.drop_constraint("fk_referrals_case_id_cases", "referrals", type_="foreignkey")
    op.drop_constraint("fk_documents_uploaded_by_users", "documents", type_="foreignkey")
    op.drop_constraint("fk_documents_case_id_cases", "documents", type_="foreignkey")
    op.drop_constraint("fk_deal_scores_case_id_cases", "deal_scores", type_="foreignkey")
    op.drop_constraint("fk_deal_scores_property_id_properties", "deal_scores", type_="foreignkey")
    op.drop_constraint("fk_consent_records_case_id_cases", "consent_records", type_="foreignkey")
    op.drop_constraint("fk_case_workflow_instances_template_id_workflow_templates", "case_workflow_instances", type_="foreignkey")
    op.drop_constraint("fk_case_workflow_instances_case_id_cases", "case_workflow_instances", type_="foreignkey")
    op.drop_constraint("fk_audit_logs_policy_version_id_policy_versions", "audit_logs", type_="foreignkey")
    op.drop_constraint("fk_audit_logs_case_id_cases", "audit_logs", type_="foreignkey")
    op.drop_constraint("fk_ai_activity_logs_policy_version_id_policy_versions", "ai_activity_logs", type_="foreignkey")
    op.drop_constraint("fk_ai_activity_logs_case_id_cases", "ai_activity_logs", type_="foreignkey")
    op.drop_constraint("fk_ai_scores_case_id_cases", "ai_scores", type_="foreignkey")
    op.drop_constraint("fk_workflow_steps_template_id_workflow_templates", "workflow_steps", type_="foreignkey")
    op.drop_constraint("fk_cases_property_id_properties", "cases", type_="foreignkey")
    op.drop_constraint("fk_cases_policy_version_id_policy_versions", "cases", type_="foreignkey")
    op.drop_constraint("fk_cases_created_by_users", "cases", type_="foreignkey")
    op.drop_constraint("fk_cert_revocations_certification_id_certifications", "cert_revocations", type_="foreignkey")
    op.drop_constraint("fk_certifications_user_id_users", "certifications", type_="foreignkey")

    op.drop_constraint("uq_cases_property_id_auction_date", "cases", type_="unique")
    op.drop_constraint("uq_outbox_queue_dedupe_key", "outbox_queue", type_="unique")
    op.drop_constraint("uq_leads_lead_id", "leads", type_="unique")
    op.drop_constraint("uq_users_email", "users", type_="unique")

    op.drop_index("ix_case_workflow_progress_instance_id", table_name="case_workflow_progress")
    op.drop_index("ix_workflow_overrides_instance_id", table_name="workflow_overrides")
    op.drop_index("ix_workflow_overrides_case_id", table_name="workflow_overrides")
    op.drop_index("ix_case_workflow_instances_template_id", table_name="case_workflow_instances")
    op.drop_index("ix_case_workflow_instances_case_id", table_name="case_workflow_instances")
    op.drop_index("ix_workflow_steps_template_id", table_name="workflow_steps")
    op.drop_index("ix_cases_canonical_key", table_name="cases")
    op.drop_index("ix_workflow_templates_program_key", table_name="workflow_templates")
    op.drop_index("ix_properties_external_id", table_name="properties")
    op.drop_index("ix_ingestion_metrics_metric_type", table_name="ingestion_metrics")
    op.drop_index("ix_bot_reports_created_at", table_name="bot_reports")
    op.drop_index("ix_bot_inbound_logs_created_at", table_name="bot_inbound_logs")
    op.drop_index("ix_bot_commands_created_at", table_name="bot_commands")
    op.drop_index("ix_auction_imports_file_hash", table_name="auction_imports")

    op.drop_table("workflow_overrides")
    op.drop_table("case_workflow_progress")
    op.drop_table("taskchecks")
    op.drop_table("role_sessions")
    op.drop_table("referrals")
    op.drop_table("documents")
    op.drop_table("deal_scores")
    op.drop_table("consent_records")
    op.drop_table("case_workflow_instances")
    op.drop_table("audit_logs")
    op.drop_table("ai_scores")
    op.drop_table("workflow_steps")
    op.drop_table("cases")
    op.drop_table("cert_revocations")
    op.drop_table("workflow_templates")
    op.drop_table("users")
    op.drop_table("training_quiz_attempts")
    op.drop_table("properties")
    op.drop_table("policy_versions")
    op.drop_table("partners")
    op.drop_table("outbox_queue")
    op.drop_table("leads")
    op.drop_table("ingestion_metrics")
    op.drop_table("certifications")
    op.drop_table("bot_triggers")
    op.drop_table("bot_settings")
    op.drop_table("bot_reports")
    op.drop_table("bot_pages")
    op.drop_table("bot_inbound_logs")
    op.drop_table("bot_commands")
    op.drop_table("auction_imports")
    op.drop_table("ai_activity_logs")

    workflowstepstatus_enum.drop(op.get_bind(), checkfirst=True)
    workflowresponsiblerole_enum.drop(op.get_bind(), checkfirst=True)
    workflowoverridecategory_enum.drop(op.get_bind(), checkfirst=True)
    userrole_enum.drop(op.get_bind(), checkfirst=True)
    referralstatus_enum.drop(op.get_bind(), checkfirst=True)
    documenttype_enum.drop(op.get_bind(), checkfirst=True)
    casestatus_enum.drop(op.get_bind(), checkfirst=True)
