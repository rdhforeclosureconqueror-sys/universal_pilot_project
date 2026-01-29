"""add properties and ai scores

Revision ID: 0f3a9c2a9b2e
Revises: 8bfa64f896dc
Create Date: 2026-01-28 06:05:12.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0f3a9c2a9b2e'
down_revision = '8bfa64f896dc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE casestatus ADD VALUE IF NOT EXISTS 'auction_intake'")

    op.create_table(
        'properties',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('external_id', sa.String(), nullable=False),
        sa.Column('address', sa.String(), nullable=False),
        sa.Column('city', sa.String(), nullable=False),
        sa.Column('state', sa.String(), nullable=False),
        sa.Column('zip', sa.String(), nullable=False),
        sa.Column('county', sa.String(), nullable=True),
        sa.Column('property_type', sa.String(), nullable=True),
        sa.Column('year_built', sa.Integer(), nullable=True),
        sa.Column('sqft', sa.Integer(), nullable=True),
        sa.Column('beds', sa.Float(), nullable=True),
        sa.Column('baths', sa.Float(), nullable=True),
        sa.Column('assessed_value', sa.Integer(), nullable=True),
        sa.Column('mortgagor', sa.String(), nullable=True),
        sa.Column('mortgagee', sa.String(), nullable=True),
        sa.Column('trustee', sa.String(), nullable=True),
        sa.Column('loan_type', sa.String(), nullable=True),
        sa.Column('interest_rate', sa.Float(), nullable=True),
        sa.Column('orig_loan_amount', sa.Integer(), nullable=True),
        sa.Column('est_balance', sa.Integer(), nullable=True),
        sa.Column('auction_date', sa.DateTime(timezone=False), nullable=True),
        sa.Column('auction_time', sa.String(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id')
    )
    op.create_index(op.f('ix_properties_external_id'), 'properties', ['external_id'], unique=True)

    op.create_table(
        'ai_scores',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('case_id', sa.UUID(), nullable=False),
        sa.Column('equity', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('strategy', sa.String(), nullable=False),
        sa.Column('confidence', sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.add_column('cases', sa.Column('property_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_cases_property_id', 'cases', 'properties', ['property_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_cases_property_id', 'cases', type_='foreignkey')
    op.drop_column('cases', 'property_id')
    op.drop_table('ai_scores')
    op.drop_index(op.f('ix_properties_external_id'), table_name='properties')
    op.drop_table('properties')
