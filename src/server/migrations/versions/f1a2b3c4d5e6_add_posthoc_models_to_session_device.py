"""add posthoc_models to session_device

Adds session_device.posthoc_models (nullable Text) to persist per-run model
provenance for post-hoc analyses.

down_revision is 42a3c6485423, the revision this deployment's alembic_version
actually records. NOTE: the repo has three divergent heads (42a3c6485423,
85aa1f4d787b, a13d95eb7da7); this migration extends only the first. The other
two branches' schema is already present in existing databases even though
alembic_version does not record them (schema-ahead-of-version drift), so a
force-merge across all three would fail with duplicate-object errors. Converging
the heads cleanly is a separate exercise (stamp the applied branches, then add
an empty merge revision) and is intentionally NOT done here. Apply this one with
a targeted upgrade: `flask --app app db upgrade f1a2b3c4d5e6`.

Revision ID: f1a2b3c4d5e6
Revises: 42a3c6485423
Create Date: 2026-07-04

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = '42a3c6485423'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('session_device',
                  sa.Column('posthoc_models', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('session_device', 'posthoc_models')
