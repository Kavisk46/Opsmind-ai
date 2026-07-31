import asyncio

from models.workspace_member import WorkspaceRole


def _make_user(user_repository, email: str = "workspace-owner@example.com"):
    return asyncio.run(
        user_repository.create(email=email, name="Workspace Owner", password_hash="h")
    )


# --- WorkspaceRepository.list_for_user ---


def test_list_for_user_returns_only_workspaces_the_user_is_a_member_of(
    workspace_repository, workspace_member_repository, user_repository
):
    member = _make_user(user_repository, email="member@example.com")
    outsider = _make_user(user_repository, email="outsider@example.com")

    async def _setup():
        their_workspace = await workspace_repository.create(
            name="Their Workspace", description=None, created_by=member.id
        )
        await workspace_member_repository.create(
            workspace_id=their_workspace.id, user_id=member.id, role=WorkspaceRole.OWNER.value
        )
        other_workspace = await workspace_repository.create(
            name="Someone Else's Workspace", description=None, created_by=outsider.id
        )
        await workspace_member_repository.create(
            workspace_id=other_workspace.id, user_id=outsider.id, role=WorkspaceRole.OWNER.value
        )
        return their_workspace

    their_workspace = asyncio.run(_setup())

    result = asyncio.run(workspace_repository.list_for_user(member.id))

    assert [w.id for w in result] == [their_workspace.id]


def test_list_for_user_orders_by_created_at(
    workspace_repository, workspace_member_repository, user_repository
):
    owner = _make_user(user_repository)

    async def _setup():
        first = await workspace_repository.create(
            name="First", description=None, created_by=owner.id
        )
        await workspace_member_repository.create(
            workspace_id=first.id, user_id=owner.id, role=WorkspaceRole.OWNER.value
        )
        second = await workspace_repository.create(
            name="Second", description=None, created_by=owner.id
        )
        await workspace_member_repository.create(
            workspace_id=second.id, user_id=owner.id, role=WorkspaceRole.OWNER.value
        )
        return first, second

    first, second = asyncio.run(_setup())

    result = asyncio.run(workspace_repository.list_for_user(owner.id))

    assert [w.id for w in result] == [first.id, second.id]


def test_list_for_user_returns_empty_list_for_a_user_with_no_workspaces(
    workspace_repository, user_repository
):
    lonely_user = _make_user(user_repository, email="lonely@example.com")

    assert asyncio.run(workspace_repository.list_for_user(lonely_user.id)) == []


# --- WorkspaceMemberRepository.get_membership ---


def test_get_membership_returns_the_matching_row(
    workspace_repository, workspace_member_repository, user_repository
):
    owner = _make_user(user_repository)

    async def _setup():
        workspace = await workspace_repository.create(
            name="Ops", description=None, created_by=owner.id
        )
        return await workspace_member_repository.create(
            workspace_id=workspace.id, user_id=owner.id, role=WorkspaceRole.OWNER.value
        )

    membership = asyncio.run(_setup())

    result = asyncio.run(
        workspace_member_repository.get_membership(
            workspace_id=membership.workspace_id, user_id=owner.id
        )
    )

    assert result is not None
    assert result.id == membership.id
    assert result.role == WorkspaceRole.OWNER.value


def test_get_membership_returns_none_when_not_a_member(
    workspace_repository, workspace_member_repository, user_repository
):
    owner = _make_user(user_repository)
    non_member = _make_user(user_repository, email="non-member@example.com")

    async def _setup():
        return await workspace_repository.create(
            name="Ops", description=None, created_by=owner.id
        )

    workspace = asyncio.run(_setup())

    result = asyncio.run(
        workspace_member_repository.get_membership(
            workspace_id=workspace.id, user_id=non_member.id
        )
    )

    assert result is None


# --- WorkspaceMemberRepository.list_by_workspace ---


def test_list_by_workspace_returns_only_that_workspaces_members(
    workspace_repository, workspace_member_repository, user_repository
):
    owner = _make_user(user_repository)
    other_owner = _make_user(user_repository, email="other-owner@example.com")

    async def _setup():
        workspace_a = await workspace_repository.create(
            name="A", description=None, created_by=owner.id
        )
        await workspace_member_repository.create(
            workspace_id=workspace_a.id, user_id=owner.id, role=WorkspaceRole.OWNER.value
        )
        workspace_b = await workspace_repository.create(
            name="B", description=None, created_by=other_owner.id
        )
        await workspace_member_repository.create(
            workspace_id=workspace_b.id, user_id=other_owner.id, role=WorkspaceRole.OWNER.value
        )
        return workspace_a

    workspace_a = asyncio.run(_setup())

    result = asyncio.run(workspace_member_repository.list_by_workspace(workspace_a.id))

    assert len(result) == 1
    assert result[0].user_id == owner.id


def test_list_by_workspace_orders_by_created_at(
    workspace_repository, workspace_member_repository, user_repository
):
    owner = _make_user(user_repository)
    second_member = _make_user(user_repository, email="second-member@example.com")

    async def _setup():
        workspace = await workspace_repository.create(
            name="Ops", description=None, created_by=owner.id
        )
        first = await workspace_member_repository.create(
            workspace_id=workspace.id, user_id=owner.id, role=WorkspaceRole.OWNER.value
        )
        second = await workspace_member_repository.create(
            workspace_id=workspace.id, user_id=second_member.id, role=WorkspaceRole.VIEWER.value
        )
        return workspace, first, second

    workspace, first, second = asyncio.run(_setup())

    result = asyncio.run(workspace_member_repository.list_by_workspace(workspace.id))

    assert [m.id for m in result] == [first.id, second.id]
