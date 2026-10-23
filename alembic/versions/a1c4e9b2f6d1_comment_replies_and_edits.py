"""comment replies (parent_id) and edit timestamp

Revision ID: a1c4e9b2f6d1
Revises: d7d8e3f5e43a
Create Date: 2026-10-23 23:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1c4e9b2f6d1"
down_revision: Union[str, Sequence[str], None] = "d7d8e3f5e43a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("comments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("parent_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index(batch_op.f("ix_comments_parent_id"), ["parent_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_comments_parent_id_comments", "comments", ["parent_id"], ["id"], ondelete="CASCADE"
        )


def downgrade() -> None:
    with op.batch_alter_table("comments", schema=None) as batch_op:
        batch_op.drop_constraint("fk_comments_parent_id_comments", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_comments_parent_id"))
        batch_op.drop_column("updated_at")
        batch_op.drop_column("parent_id")
