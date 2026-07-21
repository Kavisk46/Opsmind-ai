"""add password_hash to users

Revision ID: f380b5307d28
Revises: 53630647baca
Create Date: 2026-07-18 00:47:36.085314

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f380b5307d28'
down_revision: Union[str, None] = '53630647baca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Hand-written, matching the pattern established in 53630647baca — no live
# database available in this environment to autogenerate against. Uses a
# plain `nullable=False` (no server_default backfill needed) because this
# table has no real rows yet in this project's history.
def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "password_hash")
