import asyncio
import uuid
from datetime import UTC, datetime

from models.workspace import Workspace


def _make_user(user_repository, email: str = "conv-owner@example.com"):
    return asyncio.run(
        user_repository.create(email=email, name="Conv Owner", password_hash="h")
    )


def _make_workspace(db_session, created_by: uuid.UUID) -> Workspace:
    async def _create():
        workspace = Workspace(name="Test Workspace", created_by=created_by)
        db_session.add(workspace)
        await db_session.flush()
        return workspace

    return asyncio.run(_create())


# --- create / get_by_id ---


def test_create_persists_a_new_conversation(conversation_repository, user_repository):
    owner = _make_user(user_repository)
    workspace = _make_workspace(conversation_repository.db, owner.id)

    conversation = asyncio.run(
        conversation_repository.create(
            user_id=owner.id, workspace_id=workspace.id, title="My first chat"
        )
    )

    assert conversation.id is not None
    assert conversation.title == "My first chat"
    assert conversation.user_id == owner.id
    assert conversation.workspace_id == workspace.id


def test_get_by_id_returns_none_for_unknown_id(conversation_repository):
    assert asyncio.run(conversation_repository.get_by_id(uuid.uuid4())) is None


# --- query filters ---


def test_list_by_owner_returns_only_that_owners_conversations(
    conversation_repository, user_repository
):
    owner_a = _make_user(user_repository, email="conv-a@example.com")
    owner_b = _make_user(user_repository, email="conv-b@example.com")
    workspace_a = _make_workspace(conversation_repository.db, owner_a.id)
    workspace_b = _make_workspace(conversation_repository.db, owner_b.id)
    asyncio.run(
        conversation_repository.create(
            user_id=owner_a.id, workspace_id=workspace_a.id, title="A's chat"
        )
    )
    asyncio.run(
        conversation_repository.create(
            user_id=owner_b.id, workspace_id=workspace_b.id, title="B's chat"
        )
    )

    result = asyncio.run(conversation_repository.list_by_owner(owner_a.id))

    assert len(result) == 1
    assert result[0].title == "A's chat"


def test_list_by_owner_orders_most_recently_updated_first(
    conversation_repository, user_repository
):
    owner = _make_user(user_repository)
    workspace = _make_workspace(conversation_repository.db, owner.id)
    first = asyncio.run(
        conversation_repository.create(
            user_id=owner.id, workspace_id=workspace.id, title="first"
        )
    )
    asyncio.run(
        conversation_repository.create(
            user_id=owner.id, workspace_id=workspace.id, title="second"
        )
    )

    # Touch `first` last — a real UPDATE, which is what should move it to
    # the front despite being created earlier, proving list_by_owner()
    # orders by actual activity (updated_at), not creation order.
    asyncio.run(
        conversation_repository.update(first, updated_at=datetime.now(UTC))
    )

    result = asyncio.run(conversation_repository.list_by_owner(owner.id))

    assert [c.title for c in result] == ["first", "second"]


# --- update / delete ---


def test_update_changes_the_title(conversation_repository, user_repository):
    owner = _make_user(user_repository)
    workspace = _make_workspace(conversation_repository.db, owner.id)
    conversation = asyncio.run(
        conversation_repository.create(
            user_id=owner.id, workspace_id=workspace.id, title="old title"
        )
    )

    asyncio.run(conversation_repository.update(conversation, title="new title"))

    refetched = asyncio.run(conversation_repository.get_by_id(conversation.id))
    assert refetched.title == "new title"


def test_delete_removes_the_conversation(conversation_repository, user_repository):
    owner = _make_user(user_repository)
    workspace = _make_workspace(conversation_repository.db, owner.id)
    conversation = asyncio.run(
        conversation_repository.create(
            user_id=owner.id, workspace_id=workspace.id, title="to delete"
        )
    )

    asyncio.run(conversation_repository.delete(conversation))

    assert asyncio.run(conversation_repository.get_by_id(conversation.id)) is None
