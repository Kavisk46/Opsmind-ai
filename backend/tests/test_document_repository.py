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


# --- search ---


def _seed_search_fixture(document_repository, owner_id):
    async def _seed():
        await document_repository.create(
            owner_id=owner_id, filename="Quarterly Report.pdf",
            content_type="application/pdf", size_bytes=300, storage_key="1.pdf",
        )
        await document_repository.create(
            owner_id=owner_id, filename="notes.txt",
            content_type="text/plain", size_bytes=100, storage_key="2.txt",
        )
        await document_repository.create(
            owner_id=owner_id, filename="budget-report.csv",
            content_type="text/csv", size_bytes=200, storage_key="3.csv",
        )

    asyncio.run(_seed())


def test_search_with_no_filters_returns_everything_for_that_owner(
    document_repository, user_repository
):
    owner = _make_user(user_repository, email="search-all@example.com")
    _seed_search_fixture(document_repository, owner.id)

    results = asyncio.run(
        document_repository.search(
            owner_id=owner.id, query=None, content_type=None, sort="newest"
        )
    )

    assert len(results) == 3


def test_search_query_matches_filename_case_insensitively(
    document_repository, user_repository
):
    owner = _make_user(user_repository, email="search-query@example.com")
    _seed_search_fixture(document_repository, owner.id)

    results = asyncio.run(
        document_repository.search(
            owner_id=owner.id, query="REPORT", content_type=None, sort="newest"
        )
    )

    assert {d.filename for d in results} == {"Quarterly Report.pdf", "budget-report.csv"}


def test_search_filters_by_exact_content_type(document_repository, user_repository):
    owner = _make_user(user_repository, email="search-type@example.com")
    _seed_search_fixture(document_repository, owner.id)

    results = asyncio.run(
        document_repository.search(
            owner_id=owner.id, query=None, content_type="text/csv", sort="newest"
        )
    )

    assert [d.filename for d in results] == ["budget-report.csv"]


def test_search_sorts_by_largest_first(document_repository, user_repository):
    owner = _make_user(user_repository, email="search-sort@example.com")
    _seed_search_fixture(document_repository, owner.id)

    results = asyncio.run(
        document_repository.search(
            owner_id=owner.id, query=None, content_type=None, sort="largest"
        )
    )

    assert [d.size_bytes for d in results] == [300, 200, 100]


def test_search_sorts_by_smallest_first(document_repository, user_repository):
    owner = _make_user(user_repository, email="search-sort-2@example.com")
    _seed_search_fixture(document_repository, owner.id)

    results = asyncio.run(
        document_repository.search(
            owner_id=owner.id, query=None, content_type=None, sort="smallest"
        )
    )

    assert [d.size_bytes for d in results] == [100, 200, 300]


def test_search_never_returns_another_owners_documents(
    document_repository, user_repository
):
    owner_a = _make_user(user_repository, email="search-scope-a@example.com")
    owner_b = _make_user(user_repository, email="search-scope-b@example.com")
    _seed_search_fixture(document_repository, owner_a.id)

    results = asyncio.run(
        document_repository.search(
            owner_id=owner_b.id, query=None, content_type=None, sort="newest"
        )
    )

    assert results == []


# --- stats aggregates ---


def test_count_by_owner_counts_only_that_owners_documents(
    document_repository, user_repository
):
    owner = _make_user(user_repository, email="stats-count@example.com")
    _seed_search_fixture(document_repository, owner.id)

    assert asyncio.run(document_repository.count_by_owner(owner.id)) == 3


def test_count_by_owner_is_zero_for_an_owner_with_no_documents(
    document_repository, user_repository
):
    owner = _make_user(user_repository, email="stats-count-zero@example.com")

    assert asyncio.run(document_repository.count_by_owner(owner.id)) == 0


def test_total_size_bytes_sums_correctly(document_repository, user_repository):
    owner = _make_user(user_repository, email="stats-size@example.com")
    _seed_search_fixture(document_repository, owner.id)

    assert asyncio.run(document_repository.total_size_bytes_by_owner(owner.id)) == 600


def test_total_size_bytes_is_zero_not_null_with_no_documents(
    document_repository, user_repository
):
    owner = _make_user(user_repository, email="stats-size-zero@example.com")

    assert asyncio.run(document_repository.total_size_bytes_by_owner(owner.id)) == 0


def test_count_by_content_type_groups_correctly(document_repository, user_repository):
    owner = _make_user(user_repository, email="stats-types@example.com")
    _seed_search_fixture(document_repository, owner.id)

    result = asyncio.run(document_repository.count_by_content_type(owner.id))

    assert result == {"application/pdf": 1, "text/plain": 1, "text/csv": 1}


def test_list_recent_by_owner_respects_the_limit_and_newest_first(
    document_repository, user_repository
):
    owner = _make_user(user_repository, email="stats-recent@example.com")
    _seed_search_fixture(document_repository, owner.id)

    results = asyncio.run(document_repository.list_recent_by_owner(owner.id, limit=2))

    assert len(results) == 2
    # Newest first: the last-created document (budget-report.csv) leads.
    assert results[0].filename == "budget-report.csv"
