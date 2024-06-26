"""empty message

Revision ID: 8fbd8ec138f6
Revises: f6ac6dc39a09
Create Date: 2023-10-02 16:16:09.495717

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8fbd8ec138f6'
down_revision = 'f6ac6dc39a09'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('session_device', sa.Column('embeddings', sa.String(length=64), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('session_device', 'embeddings')
    # ### end Alembic commands ###
