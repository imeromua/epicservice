"""float quantity for weighted products

Revision ID: a1b2c3d4e5f6
Revises: f3e4d5c6b7a8
Create Date: 2026-03-24 18:06:10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f3e4d5c6b7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "temp_lists", "quantity",
        existing_type=sa.Integer(),
        type_=sa.Float(),
        existing_nullable=False,
    )
    op.alter_column(
        "saved_list_items", "quantity",
        existing_type=sa.Integer(),
        type_=sa.Float(),
        existing_nullable=False,
    )
    op.alter_column(
        "products", "відкладено",
        existing_type=sa.Integer(),
        type_=sa.Float(),
        existing_nullable=False,
        existing_server_default="0",
    )


def downgrade() -> None:
    op.alter_column(
        "products", "відкладено",
        existing_type=sa.Float(),
        type_=sa.Integer(),
        existing_nullable=False,
        existing_server_default="0",
    )
    op.alter_column(
        "saved_list_items", "quantity",
        existing_type=sa.Float(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "temp_lists", "quantity",
        existing_type=sa.Float(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
