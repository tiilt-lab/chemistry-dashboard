"""student.username: 20 characters

The Viking pilot's role codes (Sandy1G1S31) are 11 characters and the
sign-up form refused them at 10. Widen the column to match
speaker_video_metrics.student_username (20); the API and the forms raise
their limit to the same number. Guarded on the inspector so the migration
is a no-op wherever it already applied.

Revision ID: ba756b7c0126
Revises: 9a1b2c3d4e5f
Create Date: 2026-10-15
"""
from alembic import op
import sqlalchemy as sa


revision = 'ba756b7c0126'
down_revision = '9a1b2c3d4e5f'
branch_labels = None
depends_on = None

NEW = 20
OLD = 10


def _username_length():
    insp = sa.inspect(op.get_bind())
    for c in insp.get_columns('student'):
        if c['name'] == 'username':
            return getattr(c['type'], 'length', None)
    return None


def upgrade():
    if _username_length() == NEW:
        return
    # batch mode so the change also works on SQLite (tests).
    with op.batch_alter_table('student') as batch:
        batch.alter_column('username', existing_type=sa.String(length=OLD),
                           type_=sa.String(length=NEW), existing_nullable=False)


def downgrade():
    # Only safe when no stored username is longer than the old limit.
    with op.batch_alter_table('student') as batch:
        batch.alter_column('username', existing_type=sa.String(length=NEW),
                           type_=sa.String(length=OLD), existing_nullable=False)
