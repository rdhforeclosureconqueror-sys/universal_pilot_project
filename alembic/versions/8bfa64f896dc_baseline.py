"""baseline

Revision ID: 8bfa64f896dc
Revises:
Create Date: 2026-01-27 07:27:25.693759
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "8bfa64f896dc"
down_revision = None
branch_labels = None
depends_on = None


USERROLE_ENUM = postgresql.ENUM(
    "case_worker",
    "referral_coordinator",
    "admin",
    "audit_steward",
    "ai_policy_chair",
    "partner_org",
    name="userrole",
    create_type=False,
)

CASESTATUS_ENUM = postgresql.ENUM(
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

DOCUMENTTYPE_ENUM = postgresql.ENUM(
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

REFERRALSTATUS_ENUM = postgresql.ENUM(
    "draft",
    "queued",
    "sent",
    "failed",
    "cancelled",
    name="referralstatus",
    create_type=False,
)


def _create_enum_type(type_name: str, values: list[str]) -> None:
    quoted = ", ".join(f"'{value}'" for value in values)
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{type_name}') THEN
                    CREATE TYPE {type_name} AS ENUM ({quoted});
                END IF;
            END
            $$;
            """
        )
    )


def upgrade() -> None:
    _create_enum_type(
        "userrole",
        [
            "case_worker",
            "referral_coordinator",
            "admin",
            "audit_steward",
            "ai_policy_chair",
            "partner_org",
        ],
    )
    _create_enum_type(
        "casestatus",
        [
            "intake_submitted",
            "intake_incomplete",
            "under_review",
            "in_progress",
            "program_completed_positive_outcome",
            "case_closed_other_outcome",
            "auction_intake",
        ],
    )
    _create_enum_type(
        "documenttype",
        [
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
        ],
    )
    _create_enum_type("referralstatus", ["draft", "queued", "sent", "failed", "cancelled"])

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("role", USERROLE_ENUM, nullable=True),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "partners",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("contact_email", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "policy_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("program_key", sa.String(), nullable=False),
        sa.Column("version_tag", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.Column("auction_date", sa.DateTime(timezone=False), nullable=True),
        sa.Column("auction_time", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index(op.f("ix_properties_external_id"), "properties", ["external_id"], unique=True)

    op.create_table(
        "certifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cert_key", sa.String(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "training_quiz_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lesson_key", sa.String(), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", CASESTATUS_ENUM, nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("program_type", sa.String(), nullable=True),
        sa.Column("program_key", sa.String(), nullable=True),
        sa.Column("case_type", sa.String(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("policy_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["policy_version_id"], ["policy_versions.id"]),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ai_activity_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("policy_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ai_role", sa.String(), nullable=True),
        sa.Column("model_provider", sa.String(), nullable=True),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("model_version", sa.String(), nullable=True),
        sa.Column("prompt_hash", sa.String(), nullable=True),
        sa.Column("policy_rule_id", sa.String(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("human_override", sa.Boolean(), nullable=True),
        sa.Column("incident_type", sa.String(), nullable=True),
        sa.Column("admin_review_required", sa.Boolean(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "outbox_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(), nullable=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("dedupe_key", sa.String(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=True),
        sa.Column("max_attempts", sa.Integer(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key"),
    )

    op.create_table(
        "cert_revocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("certification_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason_code", sa.String(), nullable=False),
        sa.Column("revoked_by_system", sa.Boolean(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["certification_id"], ["certifications.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_is_ai", sa.Boolean(), nullable=True),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("reason_code", sa.String(), nullable=False),
        sa.Column("before_state", sa.JSON(), nullable=True),
        sa.Column("after_state", sa.JSON(), nullable=True),
        sa.Column("policy_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
        sa.ForeignKeyConstraint(["policy_version_id"], ["policy_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "consent_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("granted_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doc_type", DOCUMENTTYPE_ENUM, nullable=False),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("file_url", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "referrals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", REFERRALSTATUS_ENUM, nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "taskchecks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("skill_key", sa.String(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ai_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("equity", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("strategy", sa.String(), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "deal_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("tier", sa.String(), nullable=False),
        sa.Column("exit_strategy", sa.String(), nullable=False),
        sa.Column("urgency_days", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"]),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "bot_settings",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("key"),
    )

    op.create_table(
        "bot_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("bot", sa.String(), nullable=False),
        sa.Column("level", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=True),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bot_reports_created_at", "bot_reports", ["created_at"], unique=False)

    op.create_table(
        "bot_commands",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("target_bot", sa.String(), nullable=False),
        sa.Column("command", sa.String(), nullable=False),
        sa.Column("args_json", sa.JSON(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bot_commands_created_at", "bot_commands", ["created_at"], unique=False)

    op.create_table(
        "bot_triggers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("metric", sa.String(), nullable=False),
        sa.Column("operator", sa.String(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("target_bot", sa.String(), nullable=False),
        sa.Column("command", sa.String(), nullable=False),
        sa.Column("args_json", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "bot_inbound_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("source_bot", sa.String(), nullable=False),
        sa.Column("payload_hash", sa.String(), nullable=True),
        sa.Column("type", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("raw_json", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bot_inbound_logs_created_at", "bot_inbound_logs", ["created_at"], unique=False)

    op.create_table(
        "bot_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("last_crawl", sa.DateTime(timezone=True), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.Column("south_dallas_override", sa.Boolean(), nullable=False),
        sa.Column("exit_strategy", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lead_id"),
    )

    op.create_table(
        "auction_imports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=True),
        sa.Column("file_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("file_type", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("records_created", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "role_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_name", sa.String(), nullable=False),
        sa.Column("scope_case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scope_program_key", sa.String(), nullable=True),
        sa.Column("assumed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["scope_case_id"], ["cases.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("role_sessions")
    op.drop_table("auction_imports")
    op.drop_table("leads")
    op.drop_table("bot_pages")
    op.drop_index("ix_bot_inbound_logs_created_at", table_name="bot_inbound_logs")
    op.drop_table("bot_inbound_logs")
    op.drop_table("bot_triggers")
    op.drop_index("ix_bot_commands_created_at", table_name="bot_commands")
    op.drop_table("bot_commands")
    op.drop_index("ix_bot_reports_created_at", table_name="bot_reports")
    op.drop_table("bot_reports")
    op.drop_table("bot_settings")
    op.drop_table("deal_scores")
    op.drop_table("ai_scores")
    op.drop_table("taskchecks")
    op.drop_table("referrals")
    op.drop_table("documents")
    op.drop_table("consent_records")
    op.drop_table("audit_logs")
    op.drop_table("cert_revocations")
    op.drop_table("outbox_queue")
    op.drop_table("ai_activity_logs")
    op.drop_table("cases")
    op.drop_table("training_quiz_attempts")
    op.drop_table("certifications")
    op.drop_index(op.f("ix_properties_external_id"), table_name="properties")
    op.drop_table("properties")
    op.drop_table("policy_versions")
    op.drop_table("partners")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS referralstatus")
    op.execute("DROP TYPE IF EXISTS documenttype")
    op.execute("DROP TYPE IF EXISTS casestatus")
    op.execute("DROP TYPE IF EXISTS userrole")
