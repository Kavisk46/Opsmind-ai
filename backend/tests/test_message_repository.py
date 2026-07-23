import asyncio
import uuid


def _make_conversation(user_repository, conversation_repository, email: str = "msg-owner@example.com"):
    owner = asyncio.run(
        user_repository.create(email=email, name="Msg Owner", password_hash="h")
    )
    return asyncio.run(conversation_repository.create(user_id=owner.id, title="chat"))


# --- create ---


def test_create_persists_a_new_message(message_repository, user_repository, conversation_repository):
    conversation = _make_conversation(user_repository, conversation_repository)

    message = asyncio.run(
        message_repository.create(
            conversation_id=conversation.id, role="user", content="hello"
        )
    )

    assert message.id is not None
    assert message.role == "user"
    assert message.content == "hello"
    assert message.conversation_id == conversation.id


# --- query filters ---


def test_list_by_conversation_returns_only_that_conversations_messages(
    message_repository, user_repository, conversation_repository
):
    conversation_a = _make_conversation(user_repository, conversation_repository, email="a@example.com")
    conversation_b = _make_conversation(user_repository, conversation_repository, email="b@example.com")
    asyncio.run(
        message_repository.create(conversation_id=conversation_a.id, role="user", content="from A")
    )
    asyncio.run(
        message_repository.create(conversation_id=conversation_b.id, role="user", content="from B")
    )

    result = asyncio.run(message_repository.list_by_conversation(conversation_a.id))

    assert len(result) == 1
    assert result[0].content == "from A"


def test_list_by_conversation_orders_chronologically(
    message_repository, user_repository, conversation_repository
):
    conversation = _make_conversation(user_repository, conversation_repository)
    asyncio.run(
        message_repository.create(conversation_id=conversation.id, role="user", content="first")
    )
    asyncio.run(
        message_repository.create(conversation_id=conversation.id, role="assistant", content="second")
    )
    asyncio.run(
        message_repository.create(conversation_id=conversation.id, role="user", content="third")
    )

    result = asyncio.run(message_repository.list_by_conversation(conversation.id))

    assert [m.content for m in result] == ["first", "second", "third"]


def test_list_by_conversation_returns_empty_list_for_conversation_with_no_messages(
    message_repository,
):
    result = asyncio.run(message_repository.list_by_conversation(uuid.uuid4()))
    assert result == []
