"""negotiation_coding_run.summary: MEDIUMTEXT

A paired coding run over a MOSS transcript (session 434, Group 7, 862
merged lines, 585 fold records in cross_talk.detail) writes a summary of
about 90 KB; MySQL TEXT holds 64 KB, so the final update failed ("Data too
long for column 'summary'") after the codes were saved and the run stayed
"running". MEDIUMTEXT holds 16 MB.

Revision ID: d4e5f6a7b8c9
Revises: c1d2e3f4a5b6
Create Date: 2026-10-19 00:35:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = 'd4e5f6a7b8c9'
down_revision = 'c1d2e3f4a5b6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('negotiation_coding_run') as batch:
        batch.alter_column('summary', existing_type=sa.Text(), type_=mysql.MEDIUMTEXT(), existing_nullable=True)


def downgrade():
    with op.batch_alter_table('negotiation_coding_run') as batch:
        batch.alter_column('summary', existing_type=mysql.MEDIUMTEXT(), type_=sa.Text(), existing_nullable=True)
