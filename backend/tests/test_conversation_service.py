import asyncio
import uuid
from datetime import UTC, datetime

import pytest

from services.conversation_service import (
    ConversationNotFoundError,
    ConversationService,
    EmptyTitleError,
    estimate_tokens,
)

# A single fixed workspace_id reused across every test in this file —
# ConversationService.get_or_create_conversation only stamps workspace_id
# onto a new Conversation for organizational/audit purposes (see
# models/conversation.py's own docstring); visibility/ownership scoping
# stays owner_id-based, so no test here actually needs a REAL, distinct
# workspace per case the way the repository/route-level tests do.
_WORKSPACE_ID = uuid.uuid4()


class _FakeConversation:
    def __init__(self, id, user_id, workspace_id, title):
        self.id = id
        self.user_id = user_id
        self.workspace_id = workspace_id
        self.title = title
        self.updated_at = datetime.now(UTC)


class _FakeMessage:
    def __init__(self, id, conversation_id, role, content, extra_metadata=None):
        self.id = id
        self.conversation_id = conversation_id
        self.role = role
        self.content = content
        self.extra_metadata = extra_metadata


class FakeConversationStore:
    """A plain in-memory stand-in satisfying the ConversationStore Protocol
    — no SQLAlchemy, no event loop juggling, exactly what Step 8 of this
    phase asks tests to demonstrate.
    """

    def __init__(self):
        self.conversations: dict[uuid.UUID, _FakeConversation] = {}

    async def create(self, *, user_id, workspace_id, title):
        conversation = _FakeConversation(uuid.uuid4(), user_id, workspace_id, title)
        self.conversations[conversation.id] = conversation
        return conversation

    async def get_by_id(self, id):
        return self.conversations.get(id)

    async def list_by_owner(self, owner_id):
        return sorted(
            (c for c in self.conversations.values() if c.user_id == owner_id),
            key=lambda c: c.updated_at,
            reverse=True,
        )

    async def update(self, instance, **fields):
        for key, value in fields.items():
            setattr(instance, key, value)
        return instance

    async def delete(self, instance):
        self.conversations.pop(instance.id, None)


class FakeMessageStore:
    def __init__(self):
        self.messages: list[_FakeMessage] = []

    async def create(self, *, conversation_id, role, content, extra_metadata=None):
        message = _FakeMessage(uuid.uuid4(), conversation_id, role, content, extra_metadata)
        self.messages.append(message)
        return message

    async def list_by_conversation(self, conversation_id):
        return [m for m in self.messages if m.conversation_id == conversation_id]


def _make_service(max_history_tokens: int = 2000) -> ConversationService:
    return ConversationService(
        FakeConversationStore(), FakeMessageStore(), max_history_tokens=max_history_tokens
    )


# --- estimate_tokens() ---


def test_estimate_tokens_is_roughly_one_token_per_four_chars():
    assert estimate_tokens("a" * 40) == 10


def test_estimate_tokens_never_returns_zero_for_nonempty_text():
    assert estimate_tokens("hi") == 1


# --- get_or_create_conversation() ---


def test_get_or_create_conversation_creates_new_when_no_id_given():
    service = _make_service()
    owner_id = uuid.uuid4()

    conversation = asyncio.run(
        service.get_or_create_conversation(
            owner_id=owner_id,
            workspace_id=_WORKSPACE_ID,
            conversation_id=None,
            title_hint="First question",
        )
    )

    assert conversation.user_id == owner_id
    assert conversation.workspace_id == _WORKSPACE_ID
    assert conversation.title == "First question"


def test_get_or_create_conversation_returns_existing_when_id_given():
    service = _make_service()
    owner_id = uuid.uuid4()
    created = asyncio.run(
        service.get_or_create_conversation(
            owner_id=owner_id,
            workspace_id=_WORKSPACE_ID,
            conversation_id=None,
            title_hint="hello",
        )
    )

    fetched = asyncio.run(
        service.get_or_create_conversation(
            owner_id=owner_id,
            workspace_id=_WORKSPACE_ID,
            conversation_id=created.id,
            title_hint="ignored",
        )
    )

    assert fetched.id == created.id


def test_get_or_create_conversation_raises_for_other_owners_conversation():
    service = _make_service()
    owner_a = uuid.uuid4()
    owner_b = uuid.uuid4()
    created = asyncio.run(
        service.get_or_create_conversation(
            owner_id=owner_a,
            workspace_id=_WORKSPACE_ID,
            conversation_id=None,
            title_hint="hello",
        )
    )

    with pytest.raises(ConversationNotFoundError):
        asyncio.run(
            service.get_or_create_conversation(
                owner_id=owner_b,
                workspace_id=_WORKSPACE_ID,
                conversation_id=created.id,
                title_hint="ignored",
            )
        )


# --- append_message() bumps updated_at ---


def test_append_message_bumps_conversation_updated_at():
    service = _make_service()
    owner_id = uuid.uuid4()
    conversation = asyncio.run(
        service.get_or_create_conversation(
            owner_id=owner_id,
            workspace_id=_WORKSPACE_ID,
            conversation_id=None,
            title_hint="hello",
        )
    )
    original_updated_at = conversation.updated_at

    async def _append_later():
        await asyncio.sleep(0)
        return await service.append_message(
            conversation_id=conversation.id, role="user", content="hi"
        )

    asyncio.run(_append_later())

    refreshed = asyncio.run(service.conversation_repository.get_by_id(conversation.id))
    assert refreshed.updated_at >= original_updated_at


# --- list_conversations() ordering ---


def test_list_conversations_orders_most_recently_updated_first():
    service = _make_service()
    owner_id = uuid.uuid4()
    first = asyncio.run(
        service.get_or_create_conversation(
            owner_id=owner_id,
            workspace_id=_WORKSPACE_ID,
            conversation_id=None,
            title_hint="first",
        )
    )
    second = asyncio.run(
        service.get_or_create_conversation(
            owner_id=owner_id,
            workspace_id=_WORKSPACE_ID,
            conversation_id=None,
            title_hint="second",
        )
    )
    # Touch the FIRST conversation last, so it should now sort ahead of
    # the second one despite being created earlier.
    asyncio.run(
        service.conversation_repository.update(
            first, updated_at=datetime.now(UTC)
        )
    )

    ordered = asyncio.run(service.list_conversations(owner_id=owner_id))
    assert [c.id for c in ordered] == [first.id, second.id]


# --- delete_conversation() ---


def test_delete_conversation_removes_it():
    service = _make_service()
    owner_id = uuid.uuid4()
    conversation = asyncio.run(
        service.get_or_create_conversation(
            owner_id=owner_id,
            workspace_id=_WORKSPACE_ID,
            conversation_id=None,
            title_hint="hello",
        )
    )

    asyncio.run(
        service.delete_conversation(owner_id=owner_id, conversation_id=conversation.id)
    )

    assert asyncio.run(service.conversation_repository.get_by_id(conversation.id)) is None


def test_delete_conversation_raises_for_other_owners_conversation():
    service = _make_service()
    owner_a = uuid.uuid4()
    owner_b = uuid.uuid4()
    conversation = asyncio.run(
        service.get_or_create_conversation(
            owner_id=owner_a,
            workspace_id=_WORKSPACE_ID,
            conversation_id=None,
            title_hint="hello",
        )
    )

    with pytest.raises(ConversationNotFoundError):
        asyncio.run(
            service.delete_conversation(owner_id=owner_b, conversation_id=conversation.id)
        )


# --- rename_conversation() ---


def test_rename_conversation_updates_the_title():
    service = _make_service()
    owner_id = uuid.uuid4()
    conversation = asyncio.run(
        service.get_or_create_conversation(
            owner_id=owner_id,
            workspace_id=_WORKSPACE_ID,
            conversation_id=None,
            title_hint="original",
        )
    )

    renamed = asyncio.run(
        service.rename_conversation(
            owner_id=owner_id, conversation_id=conversation.id, title="new title"
        )
    )

    assert renamed.title == "new title"
    refetched = asyncio.run(service.conversation_repository.get_by_id(conversation.id))
    assert refetched.title == "new title"


def test_rename_conversation_strips_whitespace():
    service = _make_service()
    owner_id = uuid.uuid4()
    conversation = asyncio.run(
        service.get_or_create_conversation(
            owner_id=owner_id,
            workspace_id=_WORKSPACE_ID,
            conversation_id=None,
            title_hint="original",
        )
    )

    renamed = asyncio.run(
        service.rename_conversation(
            owner_id=owner_id, conversation_id=conversation.id, title="  padded title  "
        )
    )

    assert renamed.title == "padded title"


def test_rename_conversation_rejects_empty_title():
    service = _make_service()
    owner_id = uuid.uuid4()
    conversation = asyncio.run(
        service.get_or_create_conversation(
            owner_id=owner_id,
            workspace_id=_WORKSPACE_ID,
            conversation_id=None,
            title_hint="original",
        )
    )

    with pytest.raises(EmptyTitleError):
        asyncio.run(
            service.rename_conversation(
                owner_id=owner_id, conversation_id=conversation.id, title="   "
            )
        )


def test_rename_conversation_raises_for_other_owners_conversation():
    service = _make_service()
    owner_a = uuid.uuid4()
    owner_b = uuid.uuid4()
    conversation = asyncio.run(
        service.get_or_create_conversation(
            owner_id=owner_a,
            workspace_id=_WORKSPACE_ID,
            conversation_id=None,
            title_hint="original",
        )
    )

    with pytest.raises(ConversationNotFoundError):
        asyncio.run(
            service.rename_conversation(
                owner_id=owner_b, conversation_id=conversation.id, title="hijacked"
            )
        )


def test_rename_conversation_raises_for_unknown_conversation():
    service = _make_service()
    with pytest.raises(ConversationNotFoundError):
        asyncio.run(
            service.rename_conversation(
                owner_id=uuid.uuid4(), conversation_id=uuid.uuid4(), title="anything"
            )
        )


# --- append_message() metadata ---


def test_append_message_persists_metadata():
    service = _make_service()
    owner_id = uuid.uuid4()
    conversation = asyncio.run(
        service.get_or_create_conversation(
            owner_id=owner_id,
            workspace_id=_WORKSPACE_ID,
            conversation_id=None,
            title_hint="hello",
        )
    )

    message = asyncio.run(
        service.append_message(
            conversation_id=conversation.id,
            role="assistant",
            content="an answer",
            metadata={"tool_used": "rag_retrieval", "provider": "local", "model": "test-model"},
        )
    )

    assert message.extra_metadata == {
        "tool_used": "rag_retrieval", "provider": "local", "model": "test-model"
    }


def test_append_message_defaults_metadata_to_none():
    service = _make_service()
    owner_id = uuid.uuid4()
    conversation = asyncio.run(
        service.get_or_create_conversation(
            owner_id=owner_id,
            workspace_id=_WORKSPACE_ID,
            conversation_id=None,
            title_hint="hello",
        )
    )

    message = asyncio.run(
        service.append_message(
            conversation_id=conversation.id, role="user", content="a question"
        )
    )

    assert message.extra_metadata is None


# --- prepare_history_for_prompt() token budgeting ---


def test_prepare_history_for_prompt_includes_everything_within_budget():
    service = _make_service(max_history_tokens=2000)
    conversation_id = uuid.uuid4()
    asyncio.run(
        service.message_repository.create(
            conversation_id=conversation_id, role="user", content="short message one"
        )
    )
    asyncio.run(
        service.message_repository.create(
            conversation_id=conversation_id, role="assistant", content="short reply one"
        )
    )

    history = asyncio.run(service.prepare_history_for_prompt(conversation_id=conversation_id))

    assert history == [
        ("user", "short message one"),
        ("assistant", "short reply one"),
    ]


def test_prepare_history_for_prompt_drops_oldest_messages_over_budget():
    # Budget of 5 tokens ~ 20 chars — only the newest message (20 chars,
    # 5 tokens) fits; the older one must be dropped.
    service = _make_service(max_history_tokens=5)
    conversation_id = uuid.uuid4()
    asyncio.run(
        service.message_repository.create(
            conversation_id=conversation_id, role="user", content="a" * 100
        )
    )
    asyncio.run(
        service.message_repository.create(
            conversation_id=conversation_id, role="assistant", content="b" * 20
        )
    )

    history = asyncio.run(service.prepare_history_for_prompt(conversation_id=conversation_id))

    assert history == [("assistant", "b" * 20)]


def test_prepare_history_for_prompt_always_includes_at_least_one_message():
    # A single message that alone vastly exceeds the budget must still be
    # returned — an empty history would be strictly worse than one
    # over-budget message.
    service = _make_service(max_history_tokens=1)
    conversation_id = uuid.uuid4()
    asyncio.run(
        service.message_repository.create(
            conversation_id=conversation_id, role="user", content="a" * 1000
        )
    )

    history = asyncio.run(service.prepare_history_for_prompt(conversation_id=conversation_id))

    assert history == [("user", "a" * 1000)]


def test_prepare_history_for_prompt_returns_chronological_order():
    service = _make_service(max_history_tokens=2000)
    conversation_id = uuid.uuid4()
    for i in range(4):
        asyncio.run(
            service.message_repository.create(
                conversation_id=conversation_id, role="user", content=f"message {i}"
            )
        )

    history = asyncio.run(service.prepare_history_for_prompt(conversation_id=conversation_id))

    assert [content for _, content in history] == [
        "message 0",
        "message 1",
        "message 2",
        "message 3",
    ]
