"""add metadata to messages

Revision ID: f9b2e6a1c754
Revises: e1a4c9b7d203
Create Date: 2026-07-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9b2e6a1c754'
down_revision: Union[str, None] = 'e1a4c9b7d203'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Nullable JSON column — a user message never populates it (nothing to
# record); an assistant message gets provider/model/tool_used/token
# counts (see ConversationService.append_message / ChatService.ask()).
# Matches models/message.py's Message.extra_metadata, which maps to this
# same physical column name via mapped_column("metadata", ...) — the
# Python attribute can't be named `metadata` directly (see that model's
# own comment for why).
def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("metadata", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("messages", "metadata")
