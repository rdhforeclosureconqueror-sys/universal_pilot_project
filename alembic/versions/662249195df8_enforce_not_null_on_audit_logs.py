"""Enforce NOT NULL on audit_logs

Revision ID: 662249195df8
Revises: 3704b6821588
Create Date: 2026-01-22 05:24:53.370225

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '662249195df8'
down_revision = '3704b6821588'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.alter_column('audit_logs', 'id', nullable=False)
    op.alter_column('audit_logs', 'case_id', nullable=False)
    op.alter_column('audit_logs', 'action_type', nullable=False)
    op.alter_column('audit_logs', 'reason_code', nullable=False)
    op.alter_column('audit_logs', 'before_json', nullable=False)
    op.alter_column('audit_logs', 'after_json', nullable=False)
    op.alter_column('audit_logs', 'created_at', nullable=False)

def downgrade() -> None:
    op.alter_column('audit_logs', 'id', nullable=True)
    op.alter_column('audit_logs', 'case_id', nullable=True)
    op.alter_column('audit_logs', 'action_type', nullable=True)
    op.alter_column('audit_logs', 'reason_code', nullable=True)
    op.alter_column('audit_logs', 'before_json', nullable=True)
    op.alter_column('audit_logs', 'after_json', nullable=True)
    op.alter_column('audit_logs', 'created_at', nullable=True)
