"""add user status/role and audit fields

Revision ID: c4b1c8f2b5e9
Revises: add_product_photos
Create Date: 2026-02-26 01:08:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4b1c8f2b5e9"
down_revision: Union[str, None] = "add_product_photos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add RBAC fields
    op.add_column(
        "users",
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(length=20),
            nullable=False,
            server_default="user",
        ),
    )

    # Add audit fields for approval
    op.add_column("users", sa.Column("approved_by", sa.BigInteger(), nullable=True))
    op.add_column("users", sa.Column("approved_at", sa.DateTime(), nullable=True))

    # Add audit fields for blocking
    op.add_column("users", sa.Column("blocked_by", sa.BigInteger(), nullable=True))
    op.add_column("users", sa.Column("blocked_at", sa.DateTime(), nullable=True))
    op.add_column(
        "users",
        sa.Column("blocked_reason", sa.String(length=500), nullable=True),
    )

    # Add updated_at timestamp
    op.add_column(
        "users",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "updated_at")
    op.drop_column("users", "blocked_reason")
    op.drop_column("users", "blocked_at")
    op.drop_column("users", "blocked_by")
    op.drop_column("users", "approved_at")
    op.drop_column("users", "approved_by")
    op.drop_column("users", "role")
    op.drop_column("users", "status")
