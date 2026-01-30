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
    with op.batch_alter_table('audit_logs') as batch_op:
        batch_op.alter_column('id', existing_type=sa.UUID(), nullable=False)
        batch_op.alter_column('case_id', existing_type=sa.UUID(), nullable=False)
        batch_op.alter_column('action_type', existing_type=sa.String(), nullable=False)
        batch_op.alter_column('reason_code', existing_type=sa.String(), nullable=False)
        batch_op.alter_column('before_json', existing_type=sa.JSON(), nullable=False)
        batch_op.alter_column('after_json', existing_type=sa.JSON(), nullable=False)
        batch_op.alter_column('created_at', existing_type=sa.DateTime(timezone=True), nullable=False)

def downgrade() -> None:
    with op.batch_alter_table('audit_logs') as batch_op:
        batch_op.alter_column('id', existing_type=sa.UUID(), nullable=True)
        batch_op.alter_column('case_id', existing_type=sa.UUID(), nullable=True)
        batch_op.alter_column('action_type', existing_type=sa.String(), nullable=True)
        batch_op.alter_column('reason_code', existing_type=sa.String(), nullable=True)
        batch_op.alter_column('before_json', existing_type=sa.JSON(), nullable=True)
        batch_op.alter_column('after_json', existing_type=sa.JSON(), nullable=True)
        batch_op.alter_column('created_at', existing_type=sa.DateTime(timezone=True), nullable=True)
