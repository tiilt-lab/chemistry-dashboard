"""negotiation pairs: one device per team

A negotiation class can run with two devices per breakout group, one on
each side of the table, so that every utterance, face and gesture a device
captures belongs to that side's team (negotiation_coding.py, "paired" runs).

* session.negotiation_paired (nullable boolean): NULL/FALSE = one device per
  group, speakers assigned to teams by name afterwards (the historic
  behaviour); TRUE = two devices per group, teams fixed by device.
* session_device.negotiation_group / negotiation_side: which breakout group
  ("Table 3") the device belongs to and which side it records ("Pat" or
  "Sandy"). NULL on every other session.
* negotiation_coding_run.partner_device_id: the second device of a paired
  run (the run row hangs off the first; SET NULL if the partner is removed).

Every step is guarded on the inspector so the migration is a no-op wherever
it already applied.

Revision ID: 5d6e7f809102
Revises: 4c5d6e7f8091
Create Date: 2026-10-13
"""
from alembic import op
import sqlalchemy as sa


revision = '5d6e7f809102'
down_revision = '4c5d6e7f8091'
branch_labels = None
depends_on = None


def _has_column(table, column):
    insp = sa.inspect(op.get_bind())
    return any(c['name'] == column for c in insp.get_columns(table))


def _has_fk(table, name):
    insp = sa.inspect(op.get_bind())
    return any(fk.get('name') == name for fk in insp.get_foreign_keys(table))


def upgrade():
    if not _has_column('session', 'negotiation_paired'):
        op.add_column('session', sa.Column('negotiation_paired', sa.Boolean(), nullable=True))
    if not _has_column('session_device', 'negotiation_group'):
        op.add_column('session_device', sa.Column('negotiation_group', sa.String(length=32), nullable=True))
    if not _has_column('session_device', 'negotiation_side'):
        op.add_column('session_device', sa.Column('negotiation_side', sa.String(length=16), nullable=True))
    if not _has_column('negotiation_coding_run', 'partner_device_id'):
        op.add_column('negotiation_coding_run', sa.Column('partner_device_id', sa.Integer(), nullable=True))
    if not _has_fk('negotiation_coding_run', 'fk_negotiation_coding_run_partner'):
        op.create_foreign_key('fk_negotiation_coding_run_partner', 'negotiation_coding_run',
                              'session_device', ['partner_device_id'], ['id'], ondelete='SET NULL')


def downgrade():
    if _has_fk('negotiation_coding_run', 'fk_negotiation_coding_run_partner'):
        op.drop_constraint('fk_negotiation_coding_run_partner', 'negotiation_coding_run', type_='foreignkey')
    if _has_column('negotiation_coding_run', 'partner_device_id'):
        op.drop_column('negotiation_coding_run', 'partner_device_id')
    if _has_column('session_device', 'negotiation_side'):
        op.drop_column('session_device', 'negotiation_side')
    if _has_column('session_device', 'negotiation_group'):
        op.drop_column('session_device', 'negotiation_group')
    if _has_column('session', 'negotiation_paired'):
        op.drop_column('session', 'negotiation_paired')
