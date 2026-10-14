"""session.pod_config: the session starter's pod setup

How a breakout group is composed (people, teams and their sizes), whether
each team or each group records from its own device, and the preset group
labels the join page offers (src/server/pod_config.py). JSON text, NULL for
sessions without a setup (the historic free-form join).

Guarded on the inspector so the migration is a no-op wherever it already
applied.

Revision ID: 6e7f80910213
Revises: 5d6e7f809102
Create Date: 2026-10-14
"""
from alembic import op
import sqlalchemy as sa


revision = '6e7f80910213'
down_revision = '5d6e7f809102'
branch_labels = None
depends_on = None


def _has_column(table, column):
    insp = sa.inspect(op.get_bind())
    return any(c['name'] == column for c in insp.get_columns(table))


def upgrade():
    if not _has_column('session', 'pod_config'):
        op.add_column('session', sa.Column('pod_config', sa.Text(), nullable=True))


def downgrade():
    if _has_column('session', 'pod_config'):
        op.drop_column('session', 'pod_config')
