"""add raw material usage table

Revision ID: a7b8c9d0e1f2
Revises: f2a90e431f49
Create Date: 2025-11-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7b8c9d0e1f2'
down_revision = 'f2a90e431f49'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'raw_material_usage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('raw_material_id', sa.Integer(), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('order_item_id', sa.Integer(), nullable=True),
        sa.Column('menu_item_id', sa.Integer(), nullable=True),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(length=32), nullable=False),
        sa.Column('note', sa.String(length=256), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['menu_item_id'], ['menu_item.id'], ),
        sa.ForeignKeyConstraint(['order_id'], ['order.id'], ),
        sa.ForeignKeyConstraint(['order_item_id'], ['order_item.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['raw_material_id'], ['raw_material.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('raw_material_usage')

