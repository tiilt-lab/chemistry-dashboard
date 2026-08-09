"""referential integrity: FK + ON DELETE CASCADE

Integrity was enforced by app code every delete path had to remember (and
forgot): rater/rating/survey_response stored sessionid as a plain int with NO
foreign key, so deletes orphaned them (133 rating / 2 rater / 3 survey orphans
found live); speaker_video_metrics / speaker_hr_metrics had a FK but NO ON
DELETE rule, which is why delete_user crashed (FK 1451). This makes the
database enforce it.

Orphans are cleared first, or the new/altered FKs would fail (FK 1452/1451).

Same divergent-head caveat as the prior migrations — apply targeted:

    flask --app app db upgrade e2b3c4d5f6a7

Revision ID: e2b3c4d5f6a7
Revises: d1a2b3c4e5f6
"""
from alembic import op
import sqlalchemy as sa

revision = 'e2b3c4d5f6a7'
down_revision = 'd1a2b3c4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    # 1. Clear orphans pointing at deleted sessions (MySQL multi-table delete).
    for tbl in ('rating', 'rater', 'survey_response'):
        conn.execute(sa.text(
            "DELETE r FROM {0} r LEFT JOIN session s ON r.sessionid = s.id "
            "WHERE s.id IS NULL".format(tbl)))

    # 2. Metrics FKs already exist but with NO ACTION — recreate with CASCADE.
    op.drop_constraint('speaker_video_metrics_ibfk_1', 'speaker_video_metrics', type_='foreignkey')
    op.create_foreign_key('speaker_video_metrics_ibfk_1', 'speaker_video_metrics',
                          'session_device', ['session_device_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('speaker_hr_metrics_ibfk_1', 'speaker_hr_metrics', type_='foreignkey')
    op.create_foreign_key('speaker_hr_metrics_ibfk_1', 'speaker_hr_metrics',
                          'session_device', ['session_device_id'], ['id'], ondelete='CASCADE')

    # 3. Add the missing FKs on the peer-evaluation / survey tables.
    op.create_foreign_key('fk_rating_session', 'rating', 'session',
                          ['sessionid'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_rater_session', 'rater', 'session',
                          ['sessionid'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_survey_response_session', 'survey_response', 'session',
                          ['sessionid'], ['id'], ondelete='CASCADE')


def downgrade():
    op.drop_constraint('fk_survey_response_session', 'survey_response', type_='foreignkey')
    op.drop_constraint('fk_rater_session', 'rater', type_='foreignkey')
    op.drop_constraint('fk_rating_session', 'rating', type_='foreignkey')
    op.drop_constraint('speaker_hr_metrics_ibfk_1', 'speaker_hr_metrics', type_='foreignkey')
    op.create_foreign_key('speaker_hr_metrics_ibfk_1', 'speaker_hr_metrics',
                          'session_device', ['session_device_id'], ['id'])
    op.drop_constraint('speaker_video_metrics_ibfk_1', 'speaker_video_metrics', type_='foreignkey')
    op.create_foreign_key('speaker_video_metrics_ibfk_1', 'speaker_video_metrics',
                          'session_device', ['session_device_id'], ['id'])
