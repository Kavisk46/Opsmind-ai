import asyncio
import uuid
from datetime import datetime, timezone


def _make_user(user_repository, email: str = "conv-owner@example.com"):
    return asyncio.run(
        user_repository.create(email=email, name="Conv Owner", password_hash="h")
    )


# --- create / get_by_id ---


def test_create_persists_a_new_conversation(conversation_repository, user_repository):
    owner = _make_user(user_repository)

    conversation = asyncio.run(
        conversation_repository.create(user_id=owner.id, title="My first chat")
    )

    assert conversation.id is not None
    assert conversation.title == "My first chat"
    assert conversation.user_id == owner.id


def test_get_by_id_returns_none_for_unknown_id(conversation_repository):
    assert asyncio.run(conversation_repository.get_by_id(uuid.uuid4())) is None


# --- query filters ---


def test_list_by_owner_returns_only_that_owners_conversations(
    conversation_repository, user_repository
):
    owner_a = _make_user(user_repository, email="conv-a@example.com")
    owner_b = _make_user(user_repository, email="conv-b@example.com")
    asyncio.run(conversation_repository.create(user_id=owner_a.id, title="A's chat"))
    asyncio.run(conversation_repository.create(user_id=owner_b.id, title="B's chat"))

    result = asyncio.run(conversation_repository.list_by_owner(owner_a.id))

    assert len(result) == 1
    assert result[0].title == "A's chat"


def test_list_by_owner_orders_most_recently_updated_first(
    conversation_repository, user_repository
):
    owner = _make_user(user_repository)
    first = asyncio.run(conversation_repository.create(user_id=owner.id, title="first"))
    asyncio.run(conversation_repository.create(user_id=owner.id, title="second"))

    # Touch `first` last — a real UPDATE, which is what should move it to
    # the front despite being created earlier, proving list_by_owner()
    # orders by actual activity (updated_at), not creation order.
    asyncio.run(
        conversation_repository.update(first, updated_at=datetime.now(timezone.utc))
    )

    result = asyncio.run(conversation_repository.list_by_owner(owner.id))

    assert [c.title for c in result] == ["first", "second"]


# --- update / delete ---


def test_update_changes_the_title(conversation_repository, user_repository):
    owner = _make_user(user_repository)
    conversation = asyncio.run(
        conversation_repository.create(user_id=owner.id, title="old title")
    )

    asyncio.run(conversation_repository.update(conversation, title="new title"))

    refetched = asyncio.run(conversation_repository.get_by_id(conversation.id))
    assert refetched.title == "new title"


def test_delete_removes_the_conversation(conversation_repository, user_repository):
    owner = _make_user(user_repository)
    conversation = asyncio.run(
        conversation_repository.create(user_id=owner.id, title="to delete")
    )

    asyncio.run(conversation_repository.delete(conversation))

    assert asyncio.run(conversation_repository.get_by_id(conversation.id)) is None
