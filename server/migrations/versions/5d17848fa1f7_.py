"""empty message

Revision ID: 5d17848fa1f7
Revises: 8fbd8ec138f6
Create Date: 2023-11-07 14:21:07.729881

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5d17848fa1f7'
down_revision = '8fbd8ec138f6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('session', sa.Column('topic_model_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'session', 'topic_model', ['topic_model_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'session', type_='foreignkey')
    op.drop_column('session', 'topic_model_id')
    # ### end Alembic commands ###