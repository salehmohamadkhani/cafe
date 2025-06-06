"""add is_active to Category

Revision ID: f2a90e431f49
Revises: c4d22e6a754b
Create Date: 2025-05-14 15:39:00.769214

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f2a90e431f49'
down_revision = 'c4d22e6a754b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('category', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('category', schema=None) as batch_op:
        batch_op.drop_column('is_active')

    # ### end Alembic commands ###
