"""add product photos table

Revision ID: add_product_photos
Revises: 
Create Date: 2026-02-21 03:30:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_product_photos'
down_revision = None  # Update this with your latest migration ID
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create product_photos table
    op.create_table(
        'product_photos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('артикул', sa.String(length=20), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('original_size', sa.Integer(), nullable=False),
        sa.Column('photo_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('uploaded_by', sa.BigInteger(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('moderated_by', sa.BigInteger(), nullable=True),
        sa.Column('moderated_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['moderated_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['артикул'], ['products.артикул'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(
        op.f('ix_product_photos_артикул'),
        'product_photos',
        ['артикул'],
        unique=False
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_product_photos_артикул'), table_name='product_photos')
    
    # Drop table
    op.drop_table('product_photos')
