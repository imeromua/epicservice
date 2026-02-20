"""add archives table

Revision ID: b3f2c9d84a21
Revises: aeb5ab07a371
Create Date: 2026-02-21 01:38:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3f2c9d84a21'
down_revision: Union[str, None] = 'aeb5ab07a371'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Створення таблиці archives
    op.create_table(
        'archives',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('main_list_path', sa.String(length=255), nullable=True),
        sa.Column('surplus_list_path', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    )
    
    # Створення індексу для швидкого пошуку за user_id
    op.create_index(op.f('ix_archives_user_id'), 'archives', ['user_id'], unique=False)


def downgrade() -> None:
    # Видалення індексу
    op.drop_index(op.f('ix_archives_user_id'), table_name='archives')
    
    # Видалення таблиці
    op.drop_table('archives')
