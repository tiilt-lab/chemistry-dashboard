"""coding schemes: instructor-made schemes, the session's choice, generic codes

* coding_scheme: an instructor's scheme (coding_schemes.py, editor shape as
  JSON), cascading from its owner.
* session.coding_scheme: "builtin:<key>" | "scheme:<id>" | NULL, which
  scheme codes the session (negotiation_coding stays as the on/off flag).
* negotiation_code.codes: the utterance's codes as JSON {dimension: value},
  so a scheme may have any dimensions; the four Viking columns stay for
  rows written before this and are no longer read when codes is set.

Guarded on the inspector so the migration is a no-op wherever it already
applied.

Revision ID: 7f8091021324
Revises: 6e7f80910213
Create Date: 2026-10-14
"""
from alembic import op
import sqlalchemy as sa


revision = '7f8091021324'
down_revision = '6e7f80910213'
branch_labels = None
depends_on = None


def _has_column(table, column):
    insp = sa.inspect(op.get_bind())
    return any(c['name'] == column for c in insp.get_columns(table))


def _has_table(table):
    return sa.inspect(op.get_bind()).has_table(table)


def upgrade():
    if not _has_table('coding_scheme'):
        op.create_table(
            'coding_scheme',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('owner_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=64), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('scheme', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['owner_id'], ['user.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_coding_scheme_owner_id', 'coding_scheme', ['owner_id'])
    if not _has_column('session', 'coding_scheme'):
        op.add_column('session', sa.Column('coding_scheme', sa.String(length=64), nullable=True))
    if not _has_column('negotiation_code', 'codes'):
        op.add_column('negotiation_code', sa.Column('codes', sa.Text(), nullable=True))


def downgrade():
    if _has_column('negotiation_code', 'codes'):
        op.drop_column('negotiation_code', 'codes')
    if _has_column('session', 'coding_scheme'):
        op.drop_column('session', 'coding_scheme')
    if _has_table('coding_scheme'):
        op.drop_table('coding_scheme')
