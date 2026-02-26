"""add standalone auth fields (login, password_hash)

Revision ID: d1a2b3c4d5e6
Revises: c4b1c8f2b5e9
Create Date: 2026-02-26 02:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d1a2b3c4d5e6"
down_revision: Union[str, None] = "c4b1c8f2b5e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Додаємо поля для автентифікації автономного додатку
    op.add_column(
        "users",
        sa.Column("login", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=255), nullable=True),
    )

    # Унікальний індекс для login
    op.create_index(op.f("ix_users_login"), "users", ["login"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_login"), table_name="users")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "login")
