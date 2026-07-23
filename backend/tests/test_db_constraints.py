import asyncio
import uuid

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from models.team import Team
from models.user import User


# --- unique constraint ---


def test_duplicate_email_raises_integrity_error_at_the_database_level(user_repository):
    # UserService (services/user_service.py) already checks for a
    # duplicate email BEFORE inserting, and that's what api/routes/users.py
    # turns into a 409 — but that's an APPLICATION-level check, one
    # specific code path choosing to look first. This test proves the
    # DATABASE ITSELF also refuses a duplicate email (models/user.py's
    # `unique=True` on the email column) — the real backstop that would
    # still protect data integrity even if some future code path ever
    # inserted a User directly, bypassing UserService entirely.
    asyncio.run(
        user_repository.create(email="dup@example.com", name="First", password_hash="h")
    )

    with pytest.raises(IntegrityError):
        asyncio.run(
            user_repository.create(email="dup@example.com", name="Second", password_hash="h")
        )


# --- foreign key constraint ---


def test_creating_document_with_nonexistent_owner_raises_integrity_error(document_repository):
    # owner_id points at a user that was never created — models/document.py
    # declares this column as ForeignKey("users.id"), so the database
    # should refuse this insert outright. This only proves anything
    # because the db_session fixture (tests/conftest.py) explicitly turns
    # on PRAGMA foreign_keys — SQLite ignores foreign keys by default,
    # unlike Postgres, which always enforces them (see this phase's
    # write-up for why that default would otherwise make this test lie).
    nonexistent_owner_id = uuid.uuid4()

    with pytest.raises(IntegrityError):
        asyncio.run(
            document_repository.create(
                owner_id=nonexistent_owner_id,
                filename="orphan.txt",
                content_type="text/plain",
                size_bytes=1,
                storage_key="orphan.txt",
            )
        )


# --- cascade delete: proving the DATABASE constraint, not the ORM's own cascade ---
#
# User.documents/.conversations both also declare cascade="all,
# delete-orphan" at the ORM level (models/user.py) — session.delete(user)
# would clean up related rows through EITHER mechanism, which means a
# test using the repository's normal delete() wouldn't tell you which one
# actually did the work. Every test below deletes via a raw bulk
# `delete(...)` statement instead — bulk DELETE bypasses the ORM's
# relationship-cascade logic entirely (SQLAlchemy never even loads the
# related rows into the session for a bulk statement), so if the child
# rows still disappear, it can only be because the DATABASE'S
# ondelete="CASCADE" did it.


def test_deleting_user_cascades_to_their_documents_at_the_database_level(
    document_repository, user_repository
):
    owner = asyncio.run(
        user_repository.create(email="cascade-doc@example.com", name="Owner", password_hash="h")
    )
    document = asyncio.run(
        document_repository.create(
            owner_id=owner.id, filename="a.txt", content_type="text/plain",
            size_bytes=1, storage_key="a.txt",
        )
    )

    async def _bulk_delete_user_and_flush():
        await user_repository.db.execute(delete(User).where(User.id == owner.id))
        await user_repository.db.flush()

    asyncio.run(_bulk_delete_user_and_flush())

    assert asyncio.run(document_repository.get_by_id(document.id)) is None


def test_deleting_user_cascades_to_conversations_and_their_messages(
    conversation_repository, message_repository, user_repository
):
    owner = asyncio.run(
        user_repository.create(email="cascade-conv@example.com", name="Owner", password_hash="h")
    )
    conversation = asyncio.run(
        conversation_repository.create(user_id=owner.id, title="doomed chat")
    )
    message = asyncio.run(
        message_repository.create(
            conversation_id=conversation.id, role="user", content="hello"
        )
    )

    async def _bulk_delete_user_and_flush():
        await user_repository.db.execute(delete(User).where(User.id == owner.id))
        await user_repository.db.flush()

    asyncio.run(_bulk_delete_user_and_flush())

    # Two levels of cascade in one delete: user -> conversation ->
    # message, neither of which was deleted directly.
    assert asyncio.run(conversation_repository.get_by_id(conversation.id)) is None
    remaining_messages = asyncio.run(
        message_repository.list_by_conversation(conversation.id)
    )
    assert remaining_messages == []
    assert message.id is not None  # sanity: the message genuinely existed beforehand


def test_deleting_team_sets_users_team_id_to_null(user_repository):
    # models/user.py: team_id's FK declares ondelete="SET NULL" —
    # deliberately different from documents/conversations' CASCADE, since
    # losing your team shouldn't delete YOU, just un-assign you from it.
    #
    # Run as ONE coroutine via a single asyncio.run(), unlike most other
    # tests in this file — chaining several independent asyncio.run()
    # calls against the same real AsyncSession works fine for plain
    # column reads/writes (see test_user_repository.py), but this test
    # sets team_id on a column that also backs a relationship()
    # (User.team). That combination triggered a real
    # `MissingGreenlet: greenlet_spawn has not been called` error under
    # the multi-call pattern here: something about the object's state
    # after crossing an asyncio.run() boundary made a later plain
    # attribute access (`user.team_id`, outside of any event loop at
    # all) attempt an implicit lazy load, which SQLAlchemy's async
    # engine cannot do outside an active async context. Keeping the
    # whole sequence in one coroutine sidesteps it entirely — a concrete
    # example of why "async code across event-loop boundaries" is worth
    # being suspicious of, not just a style preference.
    async def _run():
        team = Team(name="Ops Team")
        user_repository.db.add(team)
        await user_repository.db.flush()

        user = await user_repository.create(
            email="team-member@example.com", name="Member", password_hash="h"
        )
        await user_repository.update(user, team_id=team.id)
        assert user.team_id == team.id

        await user_repository.db.execute(delete(Team).where(Team.id == team.id))
        await user_repository.db.flush()
        # The bulk DELETE ran entirely in the database — SQLAlchemy's
        # session has no way to know the ON DELETE SET NULL cascade also
        # just changed `user.team_id` underneath it, so its identity map
        # still holds the OLD in-memory value. expire() forces the next
        # access to re-SELECT it from the database instead of trusting
        # the (now-stale) cached attribute.
        #
        # Scoped to JUST team_id via attribute_names — expire(user) with
        # no argument marks EVERY attribute stale, including `id`, and
        # `user.id` is read two lines below (as get_by_id's argument) —
        # a real, verified failure mode: accessing an expired attribute
        # outside an explicit await triggers SQLAlchemy's async ORM to
        # attempt an implicit lazy load, which raises `MissingGreenlet:
        # greenlet_spawn has not been called` because implicit lazy
        # loading isn't allowed under asyncio, awaited coroutine or not.
        user_repository.db.expire(user, attribute_names=["team_id"])

        return await user_repository.get_by_id(user.id)

    refetched = asyncio.run(_run())

    # The user itself survives — only the dangling reference is cleared.
    assert refetched is not None
    assert refetched.team_id is None
