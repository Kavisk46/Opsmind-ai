import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models.document import Document


def _make_user(user_repository, email: str = "doc-owner@example.com"):
    return asyncio.run(
        user_repository.create(email=email, name="Doc Owner", password_hash="h")
    )


# --- create / get_by_id ---


def test_create_persists_a_new_document(document_repository, user_repository):
    owner = _make_user(user_repository)

    document = asyncio.run(
        document_repository.create(
            owner_id=owner.id,
            filename="notes.txt",
            content_type="text/plain",
            size_bytes=11,
            storage_key="abc123.txt",
        )
    )

    assert document.id is not None
    assert document.filename == "notes.txt"
    # Model-declared default (models/document.py) — proving it's applied.
    assert document.status == "uploaded"


def test_get_by_id_returns_the_created_document(document_repository, user_repository):
    owner = _make_user(user_repository)
    created = asyncio.run(
        document_repository.create(
            owner_id=owner.id,
            filename="a.txt",
            content_type="text/plain",
            size_bytes=1,
            storage_key="a.txt",
        )
    )

    fetched = asyncio.run(document_repository.get_by_id(created.id))

    assert fetched is not None
    assert fetched.filename == "a.txt"


def test_get_by_id_returns_none_for_unknown_id(document_repository):
    assert asyncio.run(document_repository.get_by_id(uuid.uuid4())) is None


# --- query filters ---


def test_list_by_owner_returns_only_that_owners_documents(document_repository, user_repository):
    owner_a = _make_user(user_repository, email="owner-a@example.com")
    owner_b = _make_user(user_repository, email="owner-b@example.com")
    asyncio.run(
        document_repository.create(
            owner_id=owner_a.id, filename="a.txt", content_type="text/plain",
            size_bytes=1, storage_key="a.txt",
        )
    )
    asyncio.run(
        document_repository.create(
            owner_id=owner_b.id, filename="b.txt", content_type="text/plain",
            size_bytes=1, storage_key="b.txt",
        )
    )

    result = asyncio.run(document_repository.list_by_owner(owner_a.id))

    assert len(result) == 1
    assert result[0].filename == "a.txt"


def test_list_by_status_filters_correctly(document_repository, user_repository):
    owner = _make_user(user_repository)
    ready_doc = asyncio.run(
        document_repository.create(
            owner_id=owner.id, filename="ready.txt", content_type="text/plain",
            size_bytes=1, storage_key="ready.txt",
        )
    )
    asyncio.run(document_repository.update(ready_doc, status="ready"))
    asyncio.run(
        document_repository.create(
            owner_id=owner.id, filename="uploaded.txt", content_type="text/plain",
            size_bytes=1, storage_key="uploaded.txt",
        )
    )

    result = asyncio.run(document_repository.list_by_status("ready"))

    assert [d.filename for d in result] == ["ready.txt"]


# --- relationship loading ---


def test_document_owner_relationship_loads_the_real_user(document_repository, user_repository):
    owner = _make_user(user_repository, email="relationship@example.com")
    document = asyncio.run(
        document_repository.create(
            owner_id=owner.id, filename="a.txt", content_type="text/plain",
            size_bytes=1, storage_key="a.txt",
        )
    )

    # DocumentRepository.get_by_id() doesn't eager-load `owner` (nothing
    # in this codebase currently traverses Document.owner — every caller
    # that needs the owner looks it up separately via UserRepository), so
    # this test queries directly with selectinload() to prove the
    # RELATIONSHIP ITSELF is correctly wired at the ORM level, independent
    # of whether any current repository method happens to use it yet.
    loaded_document = asyncio.run(_load_with_owner(document_repository.db, document.id))

    assert loaded_document.owner.id == owner.id
    assert loaded_document.owner.email == "relationship@example.com"


async def _load_with_owner(session, document_id):
    result = await session.execute(
        select(Document).options(selectinload(Document.owner)).where(Document.id == document_id)
    )
    return result.scalar_one()


# --- update / delete ---


def test_update_changes_status(document_repository, user_repository):
    owner = _make_user(user_repository)
    document = asyncio.run(
        document_repository.create(
            owner_id=owner.id, filename="a.txt", content_type="text/plain",
            size_bytes=1, storage_key="a.txt",
        )
    )

    asyncio.run(document_repository.update(document, status="failed", error_message="boom"))

    refetched = asyncio.run(document_repository.get_by_id(document.id))
    assert refetched.status == "failed"
    assert refetched.error_message == "boom"


def test_delete_removes_the_document(document_repository, user_repository):
    owner = _make_user(user_repository)
    document = asyncio.run(
        document_repository.create(
            owner_id=owner.id, filename="a.txt", content_type="text/plain",
            size_bytes=1, storage_key="a.txt",
        )
    )

    asyncio.run(document_repository.delete(document))

    assert asyncio.run(document_repository.get_by_id(document.id)) is None
