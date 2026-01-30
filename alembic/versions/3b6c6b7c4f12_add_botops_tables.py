"""add botops tables

Revision ID: 3b6c6b7c4f12
Revises: 0f3a9c2a9b2e
Create Date: 2025-02-14 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "3b6c6b7c4f12"
down_revision = "0f3a9c2a9b2e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "bot_settings",
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )

    op.create_table(
        "bot_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("bot", sa.String(), nullable=False),
        sa.Column("level", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=True),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=True),
    )
    op.create_index("ix_bot_reports_created_at", "bot_reports", ["created_at"])

    op.create_table(
        "bot_commands",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("target_bot", sa.String(), nullable=False),
        sa.Column("command", sa.String(), nullable=False),
        sa.Column("args_json", sa.JSON(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
    )
    op.create_index("ix_bot_commands_created_at", "bot_commands", ["created_at"])

    op.create_table(
        "bot_triggers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metric", sa.String(), nullable=False),
        sa.Column("operator", sa.String(), nullable=False, server_default=">="),
        sa.Column("threshold", sa.Float(), nullable=False, server_default="0"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("target_bot", sa.String(), nullable=False),
        sa.Column("command", sa.String(), nullable=False),
        sa.Column("args_json", sa.JSON(), nullable=True),
    )

    op.create_table(
        "bot_inbound_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("source_bot", sa.String(), nullable=False),
        sa.Column("payload_hash", sa.String(), nullable=True),
        sa.Column("type", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("raw_json", sa.JSON(), nullable=True),
    )
    op.create_index("ix_bot_inbound_logs_created_at", "bot_inbound_logs", ["created_at"])

    op.create_table(
        "bot_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("last_crawl", sa.DateTime(timezone=True), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
    )

    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lead_id", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("zip", sa.String(), nullable=True),
        sa.Column("apn", sa.String(), nullable=True),
        sa.Column("sale_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("list_price", sa.Float(), nullable=True),
        sa.Column("arrears", sa.Float(), nullable=True),
        sa.Column("equity_pct", sa.Float(), nullable=True),
        sa.Column("arv", sa.Float(), nullable=True),
        sa.Column("mao", sa.Float(), nullable=True),
        sa.Column("spread_pct", sa.Float(), nullable=True),
        sa.Column("tier", sa.String(), nullable=True),
        sa.Column("south_dallas_override", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("exit_strategy", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.UniqueConstraint("lead_id", name="uq_leads_lead_id"),
    )
    op.create_index("ix_leads_lead_id", "leads", ["lead_id"])
    op.create_index("ix_leads_created_at", "leads", ["created_at"])


def downgrade():
    op.drop_index("ix_leads_created_at", table_name="leads")
    op.drop_index("ix_leads_lead_id", table_name="leads")
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
