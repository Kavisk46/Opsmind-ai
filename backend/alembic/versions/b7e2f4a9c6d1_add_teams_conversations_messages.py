"""add teams, conversations, messages; extend users and documents

Revision ID: b7e2f4a9c6d1
Revises: a1c9e3d7f042
Create Date: 2026-07-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b7e2f4a9c6d1'
down_revision: Union[str, None] = 'a1c9e3d7f042'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Hand-written, matching every prior migration in this project — no live
# database available in this environment to autogenerate against (see the
# Phase 1/3 write-ups). Catches the schema up to models/base.py's new
# BaseModel (adds updated_at everywhere), models/team.py, models/user.py's
# new columns, models/document.py's new title column, and the new
# Conversation/Message tables. Notification is deliberately NOT included —
# deferred, per the earlier decision to defer it until something actually
# needs it.
#
# Table creation order matters here: teams must exist before users.team_id
# can reference it; users must exist before conversations.user_id can
# reference it; conversations must exist before messages.conversation_id
# can reference it. upgrade() follows that dependency order; downgrade()
# reverses it.
def upgrade() -> None:
    # --- teams (new table) ---
    op.create_table(
        "teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f("ix_teams_name"), "teams", ["name"], unique=True)

    # --- users (extend existing table) ---
    # NOT NULL columns added to a table that may already have rows need a
    # server_default so the backfill has a value — this is a DATABASE-side
    # default (applied by Postgres to existing rows during the ALTER, and
    # to any INSERT that doesn't specify the column), distinct from the
    # Python-side `default=` on the model, which only ever applies to
    # INSERTs issued through this app's own SQLAlchemy session.
    op.add_column("users", sa.Column("username", sa.String(), nullable=True))
    op.add_column(
        "users",
        sa.Column("role", sa.String(), nullable=False, server_default="member"),
    )
    op.add_column(
        "users",
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )
    op.add_column(
        "users",
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_index(op.f("ix_users_team_id"), "users", ["team_id"], unique=False)
    op.create_foreign_key(
        "fk_users_team_id_teams",
        "users",
        "teams",
        ["team_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # --- documents (extend existing table) ---
    op.add_column("documents", sa.Column("title", sa.String(), nullable=True))
    op.add_column(
        "documents",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    # documents.owner_id's FK was created without ON DELETE behavior back in
    # a1c9e3d7f042 (default: NO ACTION). models/document.py now declares
    # ondelete="CASCADE" — catching the real schema up to match the model
    # means dropping and recreating this constraint, since Postgres has no
    # "ALTER CONSTRAINT ... SET ON DELETE" — you drop and re-add. The name
    # below ("documents_owner_id_fkey") is Postgres's own default naming
    # convention for an unnamed FK created via SQLAlchemy's
    # ForeignKeyConstraint — if a live database's actual constraint name
    # ever differs, this line is exactly where that would surface as an
    # error, and exactly why "review before applying" (Step 1) matters even
    # for a migration as mechanical-looking as this one.
    op.drop_constraint("documents_owner_id_fkey", "documents", type_="foreignkey")
    op.create_foreign_key(
        "documents_owner_id_fkey",
        "documents",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # --- conversations (new table) ---
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        op.f("ix_conversations_user_id"), "conversations", ["user_id"], unique=False
    )

    # --- messages (new table) ---
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        op.f("ix_messages_conversation_id"), "messages", ["conversation_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_messages_conversation_id"), table_name="messages")
    op.drop_table("messages")

    op.drop_index(op.f("ix_conversations_user_id"), table_name="conversations")
    op.drop_table("conversations")

    op.drop_constraint("documents_owner_id_fkey", "documents", type_="foreignkey")
    op.create_foreign_key(
        "documents_owner_id_fkey", "documents", "users", ["owner_id"], ["id"]
    )
    op.drop_column("documents", "updated_at")
    op.drop_column("documents", "title")

    op.drop_constraint("fk_users_team_id_teams", "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_team_id"), table_name="users")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_column("users", "updated_at")
    op.drop_column("users", "team_id")
    op.drop_column("users", "is_active")
    op.drop_column("users", "role")
    op.drop_column("users", "username")

    op.drop_index(op.f("ix_teams_name"), table_name="teams")
    op.drop_table("teams")
