"""add error_message to documents

Revision ID: c3f8a1d5e9b2
Revises: b7e2f4a9c6d1
Create Date: 2026-07-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f8a1d5e9b2'
down_revision: Union[str, None] = 'b7e2f4a9c6d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Hand-written, matching every prior migration in this project — no live
# database available in this environment to autogenerate against.
# nullable=True, no server_default needed: existing rows simply have no
# recorded failure reason, which is the correct, honest value for a row
# that was never marked FAILED under the old schema.
def upgrade() -> None:
    op.add_column("documents", sa.Column("error_message", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "error_message")
