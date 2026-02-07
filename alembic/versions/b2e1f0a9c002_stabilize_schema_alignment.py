"""stabilize schema alignment for routes

Revision ID: b2e1f0a9c002
Revises: a1c9d9e0f001
Create Date: 2026-02-07 00:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b2e1f0a9c002"
down_revision = "a1c9d9e0f001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cases", sa.Column("program_key", sa.String(), nullable=True))
    op.add_column("cases", sa.Column("case_type", sa.String(), nullable=True))
    op.add_column("cases", sa.Column("meta", sa.JSON(), nullable=True))

    op.add_column("documents", sa.Column("file_url", sa.String(), nullable=True))

    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.alter_column("before_json", new_column_name="before_state")
        batch_op.alter_column("after_json", new_column_name="after_state")


    op.create_table(
        "role_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role_name", sa.String(), nullable=False),
        sa.Column("scope_case_id", sa.UUID(), nullable=True),
        sa.Column("scope_program_key", sa.String(), nullable=True),
        sa.Column("assumed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["scope_case_id"], ["cases.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("role", existing_type=sa.Enum("case_worker", "referral_coordinator", "admin", "audit_steward", "ai_policy_chair", "partner_org", name="userrole"), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.alter_column("before_state", new_column_name="before_json")
        batch_op.alter_column("after_state", new_column_name="after_json")

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("role", existing_type=sa.Enum("case_worker", "referral_coordinator", "admin", "audit_steward", "ai_policy_chair", "partner_org", name="userrole"), nullable=False)

    op.drop_table("role_sessions")

    op.drop_column("documents", "file_url")

    op.drop_column("cases", "meta")
    op.drop_column("cases", "case_type")
    op.drop_column("cases", "program_key")
