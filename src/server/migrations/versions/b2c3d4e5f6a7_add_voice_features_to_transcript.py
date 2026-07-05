"""add voice_features to transcript

Nullable JSON-text column holding per-utterance prosody (#6) + vocal emotion (#5).

Revision ID: b2c3d4e5f6a7
Revises: f1a2b3c4d5e6
Create Date: 2026-07-05

"""
from alembic import op
import sqlalchemy as sa


revision = 'b2c3d4e5f6a7'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('transcript',
                  sa.Column('voice_features', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('transcript', 'voice_features')
