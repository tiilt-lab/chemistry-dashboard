"""fix_cascade_delete_for_llm_metrics_and_transcript

Revision ID: a41421e7eae0
Revises: 69ee83de6b05
Create Date: 2025-11-17 19:24:45.523340

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a41421e7eae0'
down_revision = '69ee83de6b05'
branch_labels = None
depends_on = None


def upgrade():
    """Add CASCADE DELETE to foreign keys for llm_metrics and transcript tables"""

    # Fix llm_metrics foreign key to have CASCADE DELETE
    # First drop the existing constraint
    op.drop_constraint('llm_metrics_ibfk_1', 'llm_metrics', type_='foreignkey')
    # Then recreate it with CASCADE DELETE
    op.create_foreign_key('llm_metrics_ibfk_1', 'llm_metrics', 'session_device',
                         ['session_device_id'], ['id'], ondelete='CASCADE')

    # Fix transcript foreign key to have CASCADE DELETE
    # First drop the existing constraint
    op.drop_constraint('transcript_ibfk_1', 'transcript', type_='foreignkey')
    # Then recreate it with CASCADE DELETE
    op.create_foreign_key('transcript_ibfk_1', 'transcript', 'session_device',
                         ['session_device_id'], ['id'], ondelete='CASCADE')


def downgrade():
    """Remove CASCADE DELETE from foreign keys (revert to default RESTRICT)"""

    # Revert llm_metrics foreign key back to default (RESTRICT)
    op.drop_constraint('llm_metrics_ibfk_1', 'llm_metrics', type_='foreignkey')
    op.create_foreign_key('llm_metrics_ibfk_1', 'llm_metrics', 'session_device',
                         ['session_device_id'], ['id'])

    # Revert transcript foreign key back to default (RESTRICT)
    op.drop_constraint('transcript_ibfk_1', 'transcript', type_='foreignkey')
    op.create_foreign_key('transcript_ibfk_1', 'transcript', 'session_device',
                         ['session_device_id'], ['id'])
