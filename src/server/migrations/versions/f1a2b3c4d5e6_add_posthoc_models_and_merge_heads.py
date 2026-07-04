"""add posthoc_models to session_device (merges 3 divergent heads)

Adds session_device.posthoc_models (nullable Text) to persist per-run model
provenance for post-hoc analyses. Also merges the three pre-existing Alembic
heads (42a3c6485423, 85aa1f4d787b, a13d95eb7da7) into a single head so
`alembic upgrade head` is unambiguous again.

Revision ID: f1a2b3c4d5e6
Revises: 42a3c6485423, 85aa1f4d787b, a13d95eb7da7
Create Date: 2026-07-04

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = ('42a3c6485423', '85aa1f4d787b', 'a13d95eb7da7')
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('session_device',
                  sa.Column('posthoc_models', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('session_device', 'posthoc_models')
