"""session.live_video_analyses: which video analyses run during class

"attention" (gaze, attention level, object of focus) and/or "emotion"
(facial emotion), comma-separated; NULL = both, the historic behaviour.
An empty string means none run live (session.live_video_analytics False).
Guarded on the inspector so the migration is a no-op wherever it already
applied.

Revision ID: 809102132435
Revises: 7f8091021324
Create Date: 2026-10-14
"""
from alembic import op
import sqlalchemy as sa


revision = '809102132435'
down_revision = '7f8091021324'
branch_labels = None
depends_on = None


def _has_column(table, column):
    insp = sa.inspect(op.get_bind())
    return any(c['name'] == column for c in insp.get_columns(table))


def upgrade():
    if not _has_column('session', 'live_video_analyses'):
        op.add_column('session', sa.Column('live_video_analyses', sa.String(length=32), nullable=True))


def downgrade():
    if _has_column('session', 'live_video_analyses'):
        op.drop_column('session', 'live_video_analyses')
