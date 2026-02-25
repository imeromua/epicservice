"""add product photos table

Revision ID: 8f3b2a1d9c72
Revises: c4b1c8f2b5e9
Create Date: 2026-02-26 00:41:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8f3b2a1d9c72"
down_revision: Union[str, None] = "c4b1c8f2b5e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_photos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("артикул", sa.String(length=20), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("original_size", sa.Integer(), nullable=False),
        sa.Column("photo_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uploaded_by", sa.BigInteger(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("moderated_by", sa.BigInteger(), nullable=True),
        sa.Column("moderated_at", sa.DateTime(), nullable=True),
        sa.Column("rejection_reason", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["артикул"], ["products.артикул"]),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["moderated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_product_photos_артикул"), "product_photos", ["артикул"], unique=False)
    op.create_index(op.f("ix_product_photos_status"), "product_photos", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_product_photos_status"), table_name="product_photos")
    op.drop_index(op.f("ix_product_photos_артикул"), table_name="product_photos")
    op.drop_table("product_photos")
