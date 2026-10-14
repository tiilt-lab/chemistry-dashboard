"""student.group_name / team_name; first and last name optional

The sign-up form asks for a username plus the student's group and team
instead of a first and last name, so the name columns become optional
(records from the old form keep theirs) and the two labels are added. Guarded on the inspector so the migration
is a no-op wherever it already applied.

Revision ID: 9a1b2c3d4e5f
Revises: 809102132435
Create Date: 2026-10-14
"""
from alembic import op
import sqlalchemy as sa


revision = '9a1b2c3d4e5f'
down_revision = '809102132435'
branch_labels = None
depends_on = None

LABELS = ('group_name', 'team_name')
NAMES = ('firstname', 'lastname')


def _has_column(table, column):
    insp = sa.inspect(op.get_bind())
    return any(c['name'] == column for c in insp.get_columns(table))


def upgrade():
    for col in LABELS:
        if not _has_column('student', col):
            op.add_column('student', sa.Column(col, sa.String(length=64), nullable=True))
    # batch mode so the NOT NULL change also works on SQLite (tests).
    with op.batch_alter_table('student') as batch:
        for col in NAMES:
            batch.alter_column(col, existing_type=sa.String(length=50), nullable=True)


def downgrade():
    for col in LABELS:
        if _has_column('student', col):
            op.drop_column('student', col)
    # The names were required before: blank the missing ones rather than
    # fail on NULLs.
    for col in NAMES:
        op.execute("UPDATE student SET %s = '' WHERE %s IS NULL" % (col, col))
    with op.batch_alter_table('student') as batch:
        for col in NAMES:
            batch.alter_column(col, existing_type=sa.String(length=50), nullable=False)
