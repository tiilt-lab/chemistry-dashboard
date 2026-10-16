"""session.join_mode: how the session's devices join by default

'audio' or 'video' (join_mode.py); NULL = audio, which is what the join
page opens on anyway. The session starter picks it on the create form so a
class that records video does not need every team to change the "Join
with" list by hand. Guarded on the inspector so the migration is a no-op
wherever it already applied.

Revision ID: c1d2e3f4a5b6
Revises: ba756b7c0126
Create Date: 2026-10-16
"""
from alembic import op
import sqlalchemy as sa


revision = 'c1d2e3f4a5b6'
down_revision = 'ba756b7c0126'
branch_labels = None
depends_on = None


def _has_column(table, column):
    insp = sa.inspect(op.get_bind())
    return any(c['name'] == column for c in insp.get_columns(table))


def upgrade():
    if not _has_column('session', 'join_mode'):
        op.add_column('session', sa.Column('join_mode', sa.String(length=8), nullable=True))


def downgrade():
    if _has_column('session', 'join_mode'):
        op.drop_column('session', 'join_mode')
