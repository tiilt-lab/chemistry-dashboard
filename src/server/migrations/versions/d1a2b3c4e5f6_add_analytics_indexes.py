"""add indexes on the student-analytics hot-path columns

The anonymous, all-term-growing student endpoints (longitudinal, overview,
merge) filter/join on these columns with no index, so each becomes a full
scan as the tables grow (speaker_video_metrics is already ~257k rows). Index
names match SQLAlchemy's index=True default (ix_<table>_<column>) so model and
schema stay in sync and autogenerate won't want to re-add them.

Same caveat as the two prior migrations: this repo's history has divergent
heads and the live DB tracks the 42a3c6485423 -> c4d5e6f7a8b9 lineage. Apply
with a TARGETED upgrade, not a blanket one:

    flask --app app db upgrade d1a2b3c4e5f6

Revision ID: d1a2b3c4e5f6
Revises: c4d5e6f7a8b9
"""
from alembic import op

revision = 'd1a2b3c4e5f6'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ix_speaker_alias', 'speaker', ['alias'])
    op.create_index('ix_transcript_speaker_tag', 'transcript', ['speaker_tag'])
    op.create_index('ix_speaker_video_metrics_student_username',
                    'speaker_video_metrics', ['student_username'])


def downgrade():
    op.drop_index('ix_speaker_video_metrics_student_username',
                  table_name='speaker_video_metrics')
    op.drop_index('ix_transcript_speaker_tag', table_name='transcript')
    op.drop_index('ix_speaker_alias', table_name='speaker')
