"""add unique constraint on documents owner_id filename

Revision ID: d6fede6f8731
Revises: 9d2c7e4f1a83
Create Date: 2026-07-28 14:54:11.806181

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6fede6f8731'
down_revision: Union[str, None] = '9d2c7e4f1a83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Enforces "no two documents with the same filename for the same owner"
# at the database level, not just in application code — an app-level
# check-then-create has a race: two concurrent uploads of the same
# filename can both pass a SELECT-based check before either commits.
# A unique constraint is atomic and can't be beaten by concurrency; the
# service layer catches the resulting IntegrityError and turns it into a
# clean 409 (see services/document_service.py). No new column — this is
# a constraint on two columns that already exist.
def upgrade() -> None:
    op.create_unique_constraint(
        "uq_documents_owner_id_filename",
        "documents",
        ["owner_id", "filename"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_documents_owner_id_filename", "documents", type_="unique"
    )
