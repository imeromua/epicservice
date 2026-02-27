"""add phone field to users table

Revision ID: f3e4d5c6b7a8
Revises: d1a2b3c4d5e6
Create Date: 2026-02-27 09:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3e4d5c6b7a8"
down_revision: Union[str, None] = "d1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Додаємо поле phone для автентифікації за номером телефону (Android-додаток)
    op.add_column(
        "users",
        sa.Column("phone", sa.String(length=20), nullable=True),
    )
    op.create_index(op.f("ix_users_phone"), "users", ["phone"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_phone"), table_name="users")
    op.drop_column("users", "phone")
