"""add workspaces, workspace_members, and workspace scoping

Revision ID: a3d8f2c91b56
Revises: f9b2e6a1c754
Create Date: 2026-07-31 00:00:00.000000

"""
import uuid
from datetime import UTC, datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a3d8f2c91b56'
down_revision: Union[str, None] = 'f9b2e6a1c754'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Hand-written, matching the pattern established throughout this project —
# no live database available in this environment to autogenerate against.
#
# This migration does three things in sequence, all in one file (this
# project's established style is one hand-written migration per logical
# change, not a strict one-DDL-statement-per-file split — see e.g.
# a1c9e3d7f042's own precedent):
#   1. Schema: rename teams -> workspaces (the table predates any real
#      route using it — see models/workspace.py's docstring — so this is
#      a safe rename, not a breaking change to real data), create
#      workspace_members, add workspace_id (nullable) to documents/
#      conversations, add default_workspace_id (nullable) to users.
#   2. Backfill: create one "Personal" workspace + OWNER membership per
#      EXISTING user, then point their existing documents/conversations
#      at it. This is what makes workspace_id safe to tighten to NOT NULL
#      in the same migration — every existing row gets a real value, none
#      are left null.
#   3. Constraints: workspace_id -> NOT NULL on documents/conversations,
#      swap the duplicate-filename unique constraint from
#      (owner_id, filename) to (workspace_id, filename) — see
#      models/document.py's own comment on why that's the correct
#      evolution of "no duplicates" once documents are workspace-shared —
#      and drop the now-replaced users.team_id column.
#
# NOTE for a real zero-downtime deploy: steps 1-3 running as one
# transaction means a NOT NULL constraint lands in the same deploy as the
# column — acceptable for this project's scale (see this phase's own
# precedent of prioritizing schema clarity over deploy-safety
# infrastructure that doesn't exist here yet, e.g. Docker/Postgres
# unavailable in this dev environment), but a larger production table
# would normally split step 3 into its own follow-up migration after
# confirming the backfill actually completed cleanly.
def upgrade() -> None:
    # --- 1. Schema ---
    op.rename_table("teams", "workspaces")
    op.add_column(
        "workspaces",
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    # Team.name was made unique via a UNIQUE INDEX (ix_teams_name), not a
    # separate named constraint — see b7e2f4a9c6d1's own create_index call.
    # Workspace.name is NOT unique (see models/workspace.py's own comment
    # on why — every user gets their own "Personal" workspace below,
    # which would collide under a global unique constraint), so this
    # drops that unique index and replaces it with a plain, non-unique one.
    op.drop_index("ix_teams_name", table_name="workspaces")
    op.create_index(op.f("ix_workspaces_name"), "workspaces", ["name"], unique=False)
    op.create_index(
        op.f("ix_workspaces_created_by"), "workspaces", ["created_by"], unique=False
    )

    op.create_table(
        "workspace_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "workspace_id", "user_id", name="uq_workspace_members_workspace_id_user_id"
        ),
    )
    op.create_index(
        op.f("ix_workspace_members_workspace_id"), "workspace_members", ["workspace_id"]
    )
    op.create_index(
        op.f("ix_workspace_members_user_id"), "workspace_members", ["user_id"]
    )

    op.add_column(
        "documents", sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_index(
        op.f("ix_documents_workspace_id"), "documents", ["workspace_id"], unique=False
    )
    op.add_column(
        "conversations", sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_index(
        op.f("ix_conversations_workspace_id"), "conversations", ["workspace_id"], unique=False
    )
    op.add_column(
        "users",
        sa.Column("default_workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f("ix_users_default_workspace_id"), "users", ["default_workspace_id"], unique=False
    )

    # --- 2. Backfill: one Personal workspace + OWNER membership per
    # existing user, then re-point their documents/conversations at it ---
    bind = op.get_bind()
    # A real Python value, not sa.func.now() — a bound parameter passed to
    # sa.text() must be a literal value the DBAPI can send as-is; an SQL
    # expression construct like func.now() isn't one.
    now = datetime.now(UTC)

    user_rows = bind.execute(sa.text("SELECT id, name FROM users")).fetchall()
    for user_id, user_name in user_rows:
        workspace_id = uuid.uuid4()
        bind.execute(
            sa.text(
                "INSERT INTO workspaces (id, name, description, created_by, "
                "created_at, updated_at) "
                "VALUES (:id, :name, NULL, :created_by, :now, :now)"
            ),
            {
                "id": str(workspace_id),
                "name": f"{user_name}'s Workspace" if user_name else "Personal Workspace",
                "created_by": str(user_id),
                "now": now,
            },
        )
        bind.execute(
            sa.text(
                "INSERT INTO workspace_members (id, workspace_id, user_id, role, "
                "created_at, updated_at) "
                "VALUES (:id, :workspace_id, :user_id, 'owner', :now, :now)"
            ),
            {
                "id": str(uuid.uuid4()),
                "workspace_id": str(workspace_id),
                "user_id": str(user_id),
                "now": now,
            },
        )
        bind.execute(
            sa.text("UPDATE documents SET workspace_id = :workspace_id WHERE owner_id = :user_id"),
            {"workspace_id": str(workspace_id), "user_id": str(user_id)},
        )
        bind.execute(
            sa.text(
                "UPDATE conversations SET workspace_id = :workspace_id WHERE user_id = :user_id"
            ),
            {"workspace_id": str(workspace_id), "user_id": str(user_id)},
        )
        bind.execute(
            sa.text("UPDATE users SET default_workspace_id = :workspace_id WHERE id = :user_id"),
            {"workspace_id": str(workspace_id), "user_id": str(user_id)},
        )

    # Any PRE-EXISTING workspace row (renamed from a real teams row, if one
    # ever existed) still has created_by = NULL at this point — nothing
    # above touches rows already in the table before this migration ran.
    # Fall back to an arbitrary real user (any one at all) so the column
    # can still be tightened to NOT NULL below; a genuinely correct
    # "which user created this pre-existing team" answer doesn't exist in
    # the data, since Team never recorded one.
    bind.execute(
        sa.text(
            "UPDATE workspaces SET created_by = (SELECT id FROM users LIMIT 1) "
            "WHERE created_by IS NULL AND EXISTS (SELECT 1 FROM users)"
        )
    )

    # --- 3. Constraints ---
    op.alter_column("documents", "workspace_id", nullable=False)
    op.alter_column("conversations", "workspace_id", nullable=False)
    op.create_foreign_key(
        "documents_workspace_id_fkey", "documents", "workspaces",
        ["workspace_id"], ["id"], ondelete="CASCADE",
    )
    op.create_foreign_key(
        "conversations_workspace_id_fkey", "conversations", "workspaces",
        ["workspace_id"], ["id"], ondelete="CASCADE",
    )
    op.create_foreign_key(
        "users_default_workspace_id_fkey", "users", "workspaces",
        ["default_workspace_id"], ["id"], ondelete="SET NULL",
    )
    op.create_foreign_key(
        "workspaces_created_by_fkey", "workspaces", "users", ["created_by"], ["id"],
    )

    op.drop_constraint("uq_documents_owner_id_filename", "documents", type_="unique")
    op.create_unique_constraint(
        "uq_documents_workspace_id_filename", "documents", ["workspace_id", "filename"]
    )

    # Named "fk_users_team_id_teams" back in b7e2f4a9c6d1 (an explicit
    # name, not Postgres's auto-generated default) — renaming the target
    # table above doesn't rename this constraint.
    op.drop_constraint("fk_users_team_id_teams", "users", type_="foreignkey")
    op.drop_index("ix_users_team_id", table_name="users")
    op.drop_column("users", "team_id")


def downgrade() -> None:
    op.add_column(
        "users", sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_index(op.f("ix_users_team_id"), "users", ["team_id"], unique=False)
    op.create_foreign_key(
        "fk_users_team_id_teams", "users", "workspaces", ["team_id"], ["id"], ondelete="SET NULL"
    )

    op.drop_constraint("uq_documents_workspace_id_filename", "documents", type_="unique")
    op.create_unique_constraint(
        "uq_documents_owner_id_filename", "documents", ["owner_id", "filename"]
    )

    op.drop_constraint("workspaces_created_by_fkey", "workspaces", type_="foreignkey")
    op.drop_constraint("users_default_workspace_id_fkey", "users", type_="foreignkey")
    op.drop_constraint("conversations_workspace_id_fkey", "conversations", type_="foreignkey")
    op.drop_constraint("documents_workspace_id_fkey", "documents", type_="foreignkey")

    op.drop_index(op.f("ix_users_default_workspace_id"), table_name="users")
    op.drop_column("users", "default_workspace_id")
    op.drop_index(op.f("ix_conversations_workspace_id"), table_name="conversations")
    op.drop_column("conversations", "workspace_id")
    op.drop_index(op.f("ix_documents_workspace_id"), table_name="documents")
    op.drop_column("documents", "workspace_id")

    op.drop_index(op.f("ix_workspace_members_user_id"), table_name="workspace_members")
    op.drop_index(op.f("ix_workspace_members_workspace_id"), table_name="workspace_members")
    op.drop_table("workspace_members")

    op.drop_index(op.f("ix_workspaces_created_by"), table_name="workspaces")
    op.drop_index(op.f("ix_workspaces_name"), table_name="workspaces")
    op.drop_column("workspaces", "created_by")
    op.create_index(op.f("ix_teams_name"), "workspaces", ["name"], unique=True)
    op.rename_table("workspaces", "teams")
