import asyncio

import pytest

from models.workspace_member import WorkspaceRole
from services.workspace_service import (
    EmptyWorkspaceNameError,
    InsufficientWorkspacePermissionError,
    LastOwnerError,
    NotAWorkspaceMemberError,
    WorkspaceNotFoundError,
    WorkspacePermission,
    has_permission,
)


def _make_user(user_repository, email: str = "svc-owner@example.com"):
    return asyncio.run(
        user_repository.create(email=email, name="Svc Owner", password_hash="h")
    )


# --- has_permission (the permission matrix itself) ---


@pytest.mark.parametrize(
    "role,permission,expected",
    [
        (WorkspaceRole.VIEWER, WorkspacePermission.CHAT, True),
        (WorkspaceRole.VIEWER, WorkspacePermission.UPLOAD, False),
        (WorkspaceRole.VIEWER, WorkspacePermission.DELETE, False),
        (WorkspaceRole.VIEWER, WorkspacePermission.MANAGE_SETTINGS, False),
        (WorkspaceRole.VIEWER, WorkspacePermission.MANAGE_MEMBERS, False),
        (WorkspaceRole.EDITOR, WorkspacePermission.CHAT, True),
        (WorkspaceRole.EDITOR, WorkspacePermission.UPLOAD, True),
        (WorkspaceRole.EDITOR, WorkspacePermission.DELETE, True),
        (WorkspaceRole.EDITOR, WorkspacePermission.MANAGE_SETTINGS, False),
        (WorkspaceRole.EDITOR, WorkspacePermission.MANAGE_MEMBERS, False),
        (WorkspaceRole.ADMIN, WorkspacePermission.MANAGE_SETTINGS, True),
        (WorkspaceRole.ADMIN, WorkspacePermission.MANAGE_MEMBERS, True),
        (WorkspaceRole.ADMIN, WorkspacePermission.VIEW_AUDIT_LOGS, True),
        (WorkspaceRole.OWNER, WorkspacePermission.MANAGE_SETTINGS, True),
        (WorkspaceRole.OWNER, WorkspacePermission.MANAGE_MEMBERS, True),
        (WorkspaceRole.OWNER, WorkspacePermission.UPLOAD, True),
        (WorkspaceRole.OWNER, WorkspacePermission.DELETE, True),
        (WorkspaceRole.OWNER, WorkspacePermission.CHAT, True),
    ],
)
def test_has_permission_matches_the_documented_matrix(role, permission, expected):
    assert has_permission(role, permission) is expected


# --- ensure_personal_workspace ---


def test_ensure_personal_workspace_creates_a_workspace_and_owner_membership(
    workspace_service, workspace_member_repository, user_repository
):
    user = _make_user(user_repository, email="fresh-signup@example.com")

    workspace = asyncio.run(workspace_service.ensure_personal_workspace(user.id, user.name))

    assert workspace.created_by == user.id
    membership = asyncio.run(
        workspace_member_repository.get_membership(workspace_id=workspace.id, user_id=user.id)
    )
    assert membership is not None
    assert membership.role == WorkspaceRole.OWNER.value


def test_ensure_personal_workspace_sets_the_users_default_workspace_id(
    workspace_service, user_repository
):
    user = _make_user(user_repository, email="fresh-signup-2@example.com")

    workspace = asyncio.run(workspace_service.ensure_personal_workspace(user.id, user.name))

    refetched = asyncio.run(user_repository.get_by_id(user.id))
    assert refetched.default_workspace_id == workspace.id


def test_ensure_personal_workspace_is_idempotent(workspace_service, user_repository):
    user = _make_user(user_repository, email="repeat-signup@example.com")

    first = asyncio.run(workspace_service.ensure_personal_workspace(user.id, user.name))
    second = asyncio.run(workspace_service.ensure_personal_workspace(user.id, user.name))

    assert first.id == second.id


# --- create_workspace ---


def test_create_workspace_makes_the_creator_an_owner(
    workspace_service, workspace_member_repository, user_repository
):
    user = _make_user(user_repository)

    workspace = asyncio.run(
        workspace_service.create_workspace(owner_id=user.id, name="Team Alpha")
    )

    membership = asyncio.run(
        workspace_member_repository.get_membership(workspace_id=workspace.id, user_id=user.id)
    )
    assert membership.role == WorkspaceRole.OWNER.value
    assert workspace.name == "Team Alpha"


def test_create_workspace_rejects_a_blank_name(workspace_service, user_repository):
    user = _make_user(user_repository)

    with pytest.raises(EmptyWorkspaceNameError):
        asyncio.run(workspace_service.create_workspace(owner_id=user.id, name="   "))


def test_create_workspace_strips_surrounding_whitespace_from_the_name(
    workspace_service, user_repository
):
    user = _make_user(user_repository)

    workspace = asyncio.run(
        workspace_service.create_workspace(owner_id=user.id, name="  Team Beta  ")
    )

    assert workspace.name == "Team Beta"


# --- get_workspace ---


def test_get_workspace_returns_the_workspace_for_a_member(workspace_service, user_repository):
    user = _make_user(user_repository)
    workspace = asyncio.run(workspace_service.create_workspace(owner_id=user.id, name="Ops"))

    result = asyncio.run(
        workspace_service.get_workspace(user_id=user.id, workspace_id=workspace.id)
    )

    assert result.id == workspace.id


def test_get_workspace_raises_not_found_for_a_non_member(workspace_service, user_repository):
    owner = _make_user(user_repository, email="owner-x@example.com")
    outsider = _make_user(user_repository, email="outsider-x@example.com")
    workspace = asyncio.run(workspace_service.create_workspace(owner_id=owner.id, name="Ops"))

    with pytest.raises(WorkspaceNotFoundError):
        asyncio.run(
            workspace_service.get_workspace(user_id=outsider.id, workspace_id=workspace.id)
        )


# --- rename_workspace ---


def test_rename_workspace_succeeds_for_an_owner(workspace_service, user_repository):
    user = _make_user(user_repository)
    workspace = asyncio.run(workspace_service.create_workspace(owner_id=user.id, name="Old Name"))

    renamed = asyncio.run(
        workspace_service.rename_workspace(
            user_id=user.id, workspace_id=workspace.id, name="New Name"
        )
    )

    assert renamed.name == "New Name"


def test_rename_workspace_rejects_a_blank_name(workspace_service, user_repository):
    user = _make_user(user_repository)
    workspace = asyncio.run(workspace_service.create_workspace(owner_id=user.id, name="Ops"))

    with pytest.raises(EmptyWorkspaceNameError):
        asyncio.run(
            workspace_service.rename_workspace(user_id=user.id, workspace_id=workspace.id, name="")
        )


def test_rename_workspace_denied_for_a_viewer(workspace_service, user_repository):
    owner = _make_user(user_repository, email="owner-y@example.com")
    viewer = _make_user(user_repository, email="viewer-y@example.com")
    workspace = asyncio.run(workspace_service.create_workspace(owner_id=owner.id, name="Ops"))
    asyncio.run(
        workspace_service.add_member(
            actor_user_id=owner.id,
            workspace_id=workspace.id,
            new_member_user_id=viewer.id,
            role=WorkspaceRole.VIEWER,
        )
    )

    with pytest.raises(InsufficientWorkspacePermissionError):
        asyncio.run(
            workspace_service.rename_workspace(
                user_id=viewer.id, workspace_id=workspace.id, name="Hijacked"
            )
        )


def test_rename_workspace_raises_not_found_for_a_non_member(workspace_service, user_repository):
    owner = _make_user(user_repository, email="owner-z@example.com")
    outsider = _make_user(user_repository, email="outsider-z@example.com")
    workspace = asyncio.run(workspace_service.create_workspace(owner_id=owner.id, name="Ops"))

    with pytest.raises(WorkspaceNotFoundError):
        asyncio.run(
            workspace_service.rename_workspace(
                user_id=outsider.id, workspace_id=workspace.id, name="Hijacked"
            )
        )


# --- delete_workspace ---


def test_delete_workspace_succeeds_for_the_owner(workspace_service, user_repository):
    user = _make_user(user_repository)
    workspace = asyncio.run(workspace_service.create_workspace(owner_id=user.id, name="Ops"))

    asyncio.run(workspace_service.delete_workspace(user_id=user.id, workspace_id=workspace.id))

    with pytest.raises(WorkspaceNotFoundError):
        asyncio.run(
            workspace_service.get_workspace(user_id=user.id, workspace_id=workspace.id)
        )


def test_delete_workspace_denied_for_an_admin(workspace_service, user_repository):
    # ADMIN has MANAGE_SETTINGS but delete_workspace is deliberately
    # OWNER-only (see WorkspaceService.delete_workspace's own docstring) —
    # this locks in that the extra restriction is enforced, not just the
    # ordinary permission table.
    owner = _make_user(user_repository, email="owner-admin-test@example.com")
    admin = _make_user(user_repository, email="admin-test@example.com")
    workspace = asyncio.run(workspace_service.create_workspace(owner_id=owner.id, name="Ops"))
    asyncio.run(
        workspace_service.add_member(
            actor_user_id=owner.id,
            workspace_id=workspace.id,
            new_member_user_id=admin.id,
            role=WorkspaceRole.ADMIN,
        )
    )

    with pytest.raises(InsufficientWorkspacePermissionError):
        asyncio.run(
            workspace_service.delete_workspace(user_id=admin.id, workspace_id=workspace.id)
        )


def test_delete_workspace_raises_not_found_for_a_non_member(workspace_service, user_repository):
    owner = _make_user(user_repository, email="owner-del@example.com")
    outsider = _make_user(user_repository, email="outsider-del@example.com")
    workspace = asyncio.run(workspace_service.create_workspace(owner_id=owner.id, name="Ops"))

    with pytest.raises(WorkspaceNotFoundError):
        asyncio.run(
            workspace_service.delete_workspace(user_id=outsider.id, workspace_id=workspace.id)
        )


# --- list_members ---


def test_list_members_includes_every_member(workspace_service, user_repository):
    owner = _make_user(user_repository, email="owner-list@example.com")
    viewer = _make_user(user_repository, email="viewer-list@example.com")
    workspace = asyncio.run(workspace_service.create_workspace(owner_id=owner.id, name="Ops"))
    asyncio.run(
        workspace_service.add_member(
            actor_user_id=owner.id,
            workspace_id=workspace.id,
            new_member_user_id=viewer.id,
            role=WorkspaceRole.VIEWER,
        )
    )

    members = asyncio.run(
        workspace_service.list_members(user_id=owner.id, workspace_id=workspace.id)
    )

    assert {m.user_id for m in members} == {owner.id, viewer.id}


def test_list_members_raises_not_found_for_a_non_member(workspace_service, user_repository):
    owner = _make_user(user_repository, email="owner-list2@example.com")
    outsider = _make_user(user_repository, email="outsider-list2@example.com")
    workspace = asyncio.run(workspace_service.create_workspace(owner_id=owner.id, name="Ops"))

    with pytest.raises(WorkspaceNotFoundError):
        asyncio.run(
            workspace_service.list_members(user_id=outsider.id, workspace_id=workspace.id)
        )


# --- add_member ---


def test_add_member_denied_for_a_non_manager(workspace_service, user_repository):
    owner = _make_user(user_repository, email="owner-add@example.com")
    editor = _make_user(user_repository, email="editor-add@example.com")
    new_member = _make_user(user_repository, email="new-member-add@example.com")
    workspace = asyncio.run(workspace_service.create_workspace(owner_id=owner.id, name="Ops"))
    asyncio.run(
        workspace_service.add_member(
            actor_user_id=owner.id,
            workspace_id=workspace.id,
            new_member_user_id=editor.id,
            role=WorkspaceRole.EDITOR,
        )
    )

    with pytest.raises(InsufficientWorkspacePermissionError):
        asyncio.run(
            workspace_service.add_member(
                actor_user_id=editor.id,
                workspace_id=workspace.id,
                new_member_user_id=new_member.id,
                role=WorkspaceRole.VIEWER,
            )
        )


def test_add_member_re_adding_an_existing_member_updates_their_role(
    workspace_service, user_repository
):
    owner = _make_user(user_repository, email="owner-readd@example.com")
    member = _make_user(user_repository, email="member-readd@example.com")
    workspace = asyncio.run(workspace_service.create_workspace(owner_id=owner.id, name="Ops"))
    asyncio.run(
        workspace_service.add_member(
            actor_user_id=owner.id,
            workspace_id=workspace.id,
            new_member_user_id=member.id,
            role=WorkspaceRole.VIEWER,
        )
    )

    updated = asyncio.run(
        workspace_service.add_member(
            actor_user_id=owner.id,
            workspace_id=workspace.id,
            new_member_user_id=member.id,
            role=WorkspaceRole.EDITOR,
        )
    )

    assert updated.role == WorkspaceRole.EDITOR.value


# --- change_member_role ---


def test_change_member_role_updates_the_role(workspace_service, user_repository):
    owner = _make_user(user_repository, email="owner-change@example.com")
    member = _make_user(user_repository, email="member-change@example.com")
    workspace = asyncio.run(workspace_service.create_workspace(owner_id=owner.id, name="Ops"))
    asyncio.run(
        workspace_service.add_member(
            actor_user_id=owner.id,
            workspace_id=workspace.id,
            new_member_user_id=member.id,
            role=WorkspaceRole.VIEWER,
        )
    )

    updated = asyncio.run(
        workspace_service.change_member_role(
            actor_user_id=owner.id,
            workspace_id=workspace.id,
            target_user_id=member.id,
            new_role=WorkspaceRole.ADMIN,
        )
    )

    assert updated.role == WorkspaceRole.ADMIN.value


def test_change_member_role_raises_not_a_member_for_an_unknown_target(
    workspace_service, user_repository
):
    owner = _make_user(user_repository, email="owner-unknown@example.com")
    stranger = _make_user(user_repository, email="stranger-unknown@example.com")
    workspace = asyncio.run(workspace_service.create_workspace(owner_id=owner.id, name="Ops"))

    with pytest.raises(NotAWorkspaceMemberError):
        asyncio.run(
            workspace_service.change_member_role(
                actor_user_id=owner.id,
                workspace_id=workspace.id,
                target_user_id=stranger.id,
                new_role=WorkspaceRole.ADMIN,
            )
        )


def test_change_member_role_prevents_demoting_the_last_owner(
    workspace_service, user_repository
):
    owner = _make_user(user_repository, email="last-owner-demote@example.com")
    workspace = asyncio.run(workspace_service.create_workspace(owner_id=owner.id, name="Ops"))

    with pytest.raises(LastOwnerError):
        asyncio.run(
            workspace_service.change_member_role(
                actor_user_id=owner.id,
                workspace_id=workspace.id,
                target_user_id=owner.id,
                new_role=WorkspaceRole.ADMIN,
            )
        )


def test_change_member_role_allows_demoting_an_owner_when_another_owner_remains(
    workspace_service, user_repository
):
    owner_a = _make_user(user_repository, email="owner-a-demote@example.com")
    owner_b = _make_user(user_repository, email="owner-b-demote@example.com")
    workspace = asyncio.run(workspace_service.create_workspace(owner_id=owner_a.id, name="Ops"))
    asyncio.run(
        workspace_service.add_member(
            actor_user_id=owner_a.id,
            workspace_id=workspace.id,
            new_member_user_id=owner_b.id,
            role=WorkspaceRole.OWNER,
        )
    )

    updated = asyncio.run(
        workspace_service.change_member_role(
            actor_user_id=owner_a.id,
            workspace_id=workspace.id,
            target_user_id=owner_a.id,
            new_role=WorkspaceRole.ADMIN,
        )
    )

    assert updated.role == WorkspaceRole.ADMIN.value


# --- remove_member ---


def test_remove_member_removes_a_non_owner(workspace_service, user_repository):
    owner = _make_user(user_repository, email="owner-remove@example.com")
    member = _make_user(user_repository, email="member-remove@example.com")
    workspace = asyncio.run(workspace_service.create_workspace(owner_id=owner.id, name="Ops"))
    asyncio.run(
        workspace_service.add_member(
            actor_user_id=owner.id,
            workspace_id=workspace.id,
            new_member_user_id=member.id,
            role=WorkspaceRole.VIEWER,
        )
    )

    asyncio.run(
        workspace_service.remove_member(
            actor_user_id=owner.id, workspace_id=workspace.id, target_user_id=member.id
        )
    )

    members = asyncio.run(
        workspace_service.list_members(user_id=owner.id, workspace_id=workspace.id)
    )
    assert member.id not in {m.user_id for m in members}


def test_remove_member_prevents_removing_the_last_owner(workspace_service, user_repository):
    owner = _make_user(user_repository, email="last-owner-remove@example.com")
    workspace = asyncio.run(workspace_service.create_workspace(owner_id=owner.id, name="Ops"))

    with pytest.raises(LastOwnerError):
        asyncio.run(
            workspace_service.remove_member(
                actor_user_id=owner.id, workspace_id=workspace.id, target_user_id=owner.id
            )
        )


def test_remove_member_raises_not_a_member_for_an_unknown_target(
    workspace_service, user_repository
):
    owner = _make_user(user_repository, email="owner-unknown-remove@example.com")
    stranger = _make_user(user_repository, email="stranger-unknown-remove@example.com")
    workspace = asyncio.run(workspace_service.create_workspace(owner_id=owner.id, name="Ops"))

    with pytest.raises(NotAWorkspaceMemberError):
        asyncio.run(
            workspace_service.remove_member(
                actor_user_id=owner.id, workspace_id=workspace.id, target_user_id=stranger.id
            )
        )


def test_remove_member_denied_for_a_non_manager(workspace_service, user_repository):
    owner = _make_user(user_repository, email="owner-remove-denied@example.com")
    editor = _make_user(user_repository, email="editor-remove-denied@example.com")
    victim = _make_user(user_repository, email="victim-remove-denied@example.com")
    workspace = asyncio.run(workspace_service.create_workspace(owner_id=owner.id, name="Ops"))
    asyncio.run(
        workspace_service.add_member(
            actor_user_id=owner.id,
            workspace_id=workspace.id,
            new_member_user_id=editor.id,
            role=WorkspaceRole.EDITOR,
        )
    )
    asyncio.run(
        workspace_service.add_member(
            actor_user_id=owner.id,
            workspace_id=workspace.id,
            new_member_user_id=victim.id,
            role=WorkspaceRole.VIEWER,
        )
    )

    with pytest.raises(InsufficientWorkspacePermissionError):
        asyncio.run(
            workspace_service.remove_member(
                actor_user_id=editor.id, workspace_id=workspace.id, target_user_id=victim.id
            )
        )
