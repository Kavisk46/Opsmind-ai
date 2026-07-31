import asyncio
import uuid

import pytest

from models.workspace import Workspace
from repositories.document_repository import DocumentRepository


def _make_user(user_repository, email: str = "chunk-owner@example.com"):
    return asyncio.run(
        user_repository.create(email=email, name="Chunk Owner", password_hash="h")
    )


def _make_workspace(db_session, created_by: uuid.UUID) -> Workspace:
    async def _create():
        workspace = Workspace(name="Test Workspace", created_by=created_by)
        db_session.add(workspace)
        await db_session.flush()
        return workspace

    return asyncio.run(_create())


def _make_document(db_session, owner_id, workspace_id, filename: str = "notes.txt"):
    return asyncio.run(
        DocumentRepository(db_session).create(
            owner_id=owner_id,
            workspace_id=workspace_id,
            filename=filename,
            content_type="text/plain",
            size_bytes=100,
            storage_key=f"{filename}.key",
        )
    )


def _chunk_dicts(*texts: str, embedding_model: str = "test-model") -> list[dict]:
    return [
        {
            "chunk_index": index,
            "text": text,
            "token_count": len(text.split()),
            "embedding_model": embedding_model,
        }
        for index, text in enumerate(texts)
    ]


# --- replace_for_document ---


def test_replace_for_document_creates_chunks_in_order(
    chunk_repository, document_repository, user_repository, db_session
):
    owner = _make_user(user_repository)
    workspace = _make_workspace(db_session, owner.id)
    document = _make_document(db_session, owner.id, workspace.id)

    created = asyncio.run(
        chunk_repository.replace_for_document(
            document_id=document.id,
            owner_id=owner.id,
            chunks=_chunk_dicts("first chunk", "second chunk", "third chunk"),
        )
    )

    assert [c.chunk_index for c in created] == [0, 1, 2]
    assert [c.text for c in created] == ["first chunk", "second chunk", "third chunk"]
    assert all(c.embedding_model == "test-model" for c in created)
    assert all(c.owner_id == owner.id for c in created)
    assert all(c.document_id == document.id for c in created)


def test_replace_for_document_stores_the_given_token_count(
    chunk_repository, document_repository, user_repository, db_session
):
    owner = _make_user(user_repository)
    workspace = _make_workspace(db_session, owner.id)
    document = _make_document(db_session, owner.id, workspace.id)

    created = asyncio.run(
        chunk_repository.replace_for_document(
            document_id=document.id,
            owner_id=owner.id,
            chunks=_chunk_dicts("four words here total"),
        )
    )

    assert created[0].token_count == 4


def test_replace_for_document_is_idempotent_on_reprocessing(
    chunk_repository, document_repository, user_repository, db_session
):
    # Simulates re-ingesting the same document (a retry, a manual
    # re-upload-trigger) — the whole point of replace_for_document over a
    # plain insert: the second call's chunk set should fully REPLACE the
    # first's, never leave both sets coexisting.
    owner = _make_user(user_repository)
    workspace = _make_workspace(db_session, owner.id)
    document = _make_document(db_session, owner.id, workspace.id)

    asyncio.run(
        chunk_repository.replace_for_document(
            document_id=document.id,
            owner_id=owner.id,
            chunks=_chunk_dicts("old chunk one", "old chunk two", "old chunk three"),
        )
    )
    asyncio.run(
        chunk_repository.replace_for_document(
            document_id=document.id,
            owner_id=owner.id,
            chunks=_chunk_dicts("new chunk one"),
        )
    )

    result = asyncio.run(chunk_repository.list_by_document(document.id))

    assert len(result) == 1
    assert result[0].text == "new chunk one"


def test_replace_for_document_only_touches_that_documents_chunks(
    chunk_repository, document_repository, user_repository, db_session
):
    owner = _make_user(user_repository)
    workspace = _make_workspace(db_session, owner.id)
    document_a = _make_document(db_session, owner.id, workspace.id, filename="a.txt")
    document_b = _make_document(db_session, owner.id, workspace.id, filename="b.txt")

    asyncio.run(
        chunk_repository.replace_for_document(
            document_id=document_a.id,
            owner_id=owner.id,
            chunks=_chunk_dicts("a chunk"),
        )
    )
    asyncio.run(
        chunk_repository.replace_for_document(
            document_id=document_b.id,
            owner_id=owner.id,
            chunks=_chunk_dicts("b chunk one", "b chunk two"),
        )
    )
    # Reprocess document_a only.
    asyncio.run(
        chunk_repository.replace_for_document(
            document_id=document_a.id,
            owner_id=owner.id,
            chunks=_chunk_dicts("a chunk replaced"),
        )
    )

    result_a = asyncio.run(chunk_repository.list_by_document(document_a.id))
    result_b = asyncio.run(chunk_repository.list_by_document(document_b.id))

    assert [c.text for c in result_a] == ["a chunk replaced"]
    assert [c.text for c in result_b] == ["b chunk one", "b chunk two"]


# --- list_by_document ---


def test_list_by_document_orders_by_chunk_index(
    chunk_repository, document_repository, user_repository, db_session
):
    owner = _make_user(user_repository)
    workspace = _make_workspace(db_session, owner.id)
    document = _make_document(db_session, owner.id, workspace.id)
    asyncio.run(
        chunk_repository.replace_for_document(
            document_id=document.id,
            owner_id=owner.id,
            chunks=_chunk_dicts("zero", "one", "two", "three"),
        )
    )

    result = asyncio.run(chunk_repository.list_by_document(document.id))

    assert [c.chunk_index for c in result] == [0, 1, 2, 3]


def test_list_by_document_returns_empty_for_a_document_with_no_chunks(
    chunk_repository, document_repository, user_repository, db_session
):
    owner = _make_user(user_repository)
    workspace = _make_workspace(db_session, owner.id)
    document = _make_document(db_session, owner.id, workspace.id)

    assert asyncio.run(chunk_repository.list_by_document(document.id)) == []


# --- delete_by_document ---


def test_delete_by_document_removes_only_that_documents_chunks(
    chunk_repository, document_repository, user_repository, db_session
):
    owner = _make_user(user_repository)
    workspace = _make_workspace(db_session, owner.id)
    document_a = _make_document(db_session, owner.id, workspace.id, filename="a.txt")
    document_b = _make_document(db_session, owner.id, workspace.id, filename="b.txt")
    asyncio.run(
        chunk_repository.replace_for_document(
            document_id=document_a.id, owner_id=owner.id, chunks=_chunk_dicts("a")
        )
    )
    asyncio.run(
        chunk_repository.replace_for_document(
            document_id=document_b.id, owner_id=owner.id, chunks=_chunk_dicts("b")
        )
    )

    asyncio.run(chunk_repository.delete_by_document(document_a.id))

    assert asyncio.run(chunk_repository.list_by_document(document_a.id)) == []
    assert len(asyncio.run(chunk_repository.list_by_document(document_b.id))) == 1


def test_delete_by_document_is_safe_when_nothing_exists_yet(
    chunk_repository, document_repository, user_repository, db_session
):
    owner = _make_user(user_repository)
    workspace = _make_workspace(db_session, owner.id)
    document = _make_document(db_session, owner.id, workspace.id)

    # Should not raise even though no chunks were ever created.
    asyncio.run(chunk_repository.delete_by_document(document.id))


# --- search_by_text (keyword retrieval) ---


def test_search_by_text_matches_chunk_text(
    chunk_repository, document_repository, user_repository, db_session
):
    owner = _make_user(user_repository)
    workspace = _make_workspace(db_session, owner.id)
    document = _make_document(db_session, owner.id, workspace.id, filename="notes.txt")
    asyncio.run(
        chunk_repository.replace_for_document(
            document_id=document.id, owner_id=owner.id,
            chunks=_chunk_dicts("the deployment pipeline stalled overnight"),
        )
    )

    matches = asyncio.run(
        chunk_repository.search_by_text(
            owner_id=owner.id, terms=["pipeline"], mode="or", limit=10
        )
    )

    assert len(matches) == 1
    assert matches[0].document_id == document.id
    assert matches[0].filename == "notes.txt"
    assert matches[0].keyword_score == 1.0


def test_search_by_text_matches_filename_even_when_text_does_not_match(
    chunk_repository, document_repository, user_repository, db_session
):
    owner = _make_user(user_repository)
    workspace = _make_workspace(db_session, owner.id)
    document = _make_document(db_session, owner.id, workspace.id, filename="q3-budget-report.txt")
    asyncio.run(
        chunk_repository.replace_for_document(
            document_id=document.id, owner_id=owner.id,
            chunks=_chunk_dicts("completely unrelated content"),
        )
    )

    matches = asyncio.run(
        chunk_repository.search_by_text(
            owner_id=owner.id, terms=["budget"], mode="or", limit=10
        )
    )

    assert len(matches) == 1
    assert matches[0].document_id == document.id


def test_search_by_text_mode_and_requires_every_term_to_match(
    chunk_repository, document_repository, user_repository, db_session
):
    owner = _make_user(user_repository)
    workspace = _make_workspace(db_session, owner.id)
    both_terms = _make_document(db_session, owner.id, workspace.id, filename="a.txt")
    one_term = _make_document(db_session, owner.id, workspace.id, filename="b.txt")
    asyncio.run(
        chunk_repository.replace_for_document(
            document_id=both_terms.id, owner_id=owner.id,
            chunks=_chunk_dicts("quarterly budget review meeting"),
        )
    )
    asyncio.run(
        chunk_repository.replace_for_document(
            document_id=one_term.id, owner_id=owner.id,
            chunks=_chunk_dicts("quarterly sales numbers"),
        )
    )

    matches = asyncio.run(
        chunk_repository.search_by_text(
            owner_id=owner.id, terms=["quarterly", "budget"], mode="and", limit=10
        )
    )

    assert [m.document_id for m in matches] == [both_terms.id]


def test_search_by_text_mode_or_matches_any_term(
    chunk_repository, document_repository, user_repository, db_session
):
    owner = _make_user(user_repository)
    workspace = _make_workspace(db_session, owner.id)
    document_a = _make_document(db_session, owner.id, workspace.id, filename="a.txt")
    document_b = _make_document(db_session, owner.id, workspace.id, filename="b.txt")
    asyncio.run(
        chunk_repository.replace_for_document(
            document_id=document_a.id, owner_id=owner.id,
            chunks=_chunk_dicts("mentions budget only"),
        )
    )
    asyncio.run(
        chunk_repository.replace_for_document(
            document_id=document_b.id, owner_id=owner.id,
            chunks=_chunk_dicts("mentions payroll only"),
        )
    )

    matches = asyncio.run(
        chunk_repository.search_by_text(
            owner_id=owner.id, terms=["budget", "payroll"], mode="or", limit=10
        )
    )

    assert {m.document_id for m in matches} == {document_a.id, document_b.id}


def test_search_by_text_scores_more_matched_terms_higher(
    chunk_repository, document_repository, user_repository, db_session
):
    owner = _make_user(user_repository)
    workspace = _make_workspace(db_session, owner.id)
    strong_match = _make_document(db_session, owner.id, workspace.id, filename="a.txt")
    weak_match = _make_document(db_session, owner.id, workspace.id, filename="b.txt")
    asyncio.run(
        chunk_repository.replace_for_document(
            document_id=strong_match.id, owner_id=owner.id,
            chunks=_chunk_dicts("alpha beta gamma"),
        )
    )
    asyncio.run(
        chunk_repository.replace_for_document(
            document_id=weak_match.id, owner_id=owner.id,
            chunks=_chunk_dicts("alpha only"),
        )
    )

    matches = asyncio.run(
        chunk_repository.search_by_text(
            owner_id=owner.id, terms=["alpha", "beta", "gamma"], mode="or", limit=10
        )
    )

    assert matches[0].document_id == strong_match.id
    assert matches[0].keyword_score == 1.0
    assert matches[1].document_id == weak_match.id
    assert matches[1].keyword_score == pytest.approx(1 / 3)


def test_search_by_text_never_returns_another_owners_chunks(
    chunk_repository, document_repository, user_repository, db_session
):
    owner_a = _make_user(user_repository, email="owner-a@example.com")
    owner_b = _make_user(user_repository, email="owner-b@example.com")
    workspace_a = _make_workspace(db_session, owner_a.id)
    document = _make_document(db_session, owner_a.id, workspace_a.id, filename="secret.txt")
    asyncio.run(
        chunk_repository.replace_for_document(
            document_id=document.id, owner_id=owner_a.id,
            chunks=_chunk_dicts("confidential budget figures"),
        )
    )

    matches = asyncio.run(
        chunk_repository.search_by_text(
            owner_id=owner_b.id, terms=["budget"], mode="or", limit=10
        )
    )

    assert matches == []


def test_search_by_text_respects_the_limit(
    chunk_repository, document_repository, user_repository, db_session
):
    owner = _make_user(user_repository)
    workspace = _make_workspace(db_session, owner.id)
    for i in range(5):
        document = _make_document(db_session, owner.id, workspace.id, filename=f"doc-{i}.txt")
        asyncio.run(
            chunk_repository.replace_for_document(
                document_id=document.id, owner_id=owner.id,
                chunks=_chunk_dicts("shared keyword appears here"),
            )
        )

    matches = asyncio.run(
        chunk_repository.search_by_text(
            owner_id=owner.id, terms=["keyword"], mode="or", limit=2
        )
    )

    assert len(matches) == 2


def test_search_by_text_returns_empty_list_for_no_terms(
    chunk_repository, document_repository, user_repository, db_session
):
    owner = _make_user(user_repository)
    workspace = _make_workspace(db_session, owner.id)
    document = _make_document(db_session, owner.id, workspace.id)
    asyncio.run(
        chunk_repository.replace_for_document(
            document_id=document.id, owner_id=owner.id,
            chunks=_chunk_dicts("anything at all"),
        )
    )

    matches = asyncio.run(
        chunk_repository.search_by_text(owner_id=owner.id, terms=[], mode="or", limit=10)
    )

    assert matches == []


def test_search_by_text_returns_empty_list_when_nothing_matches(
    chunk_repository, document_repository, user_repository, db_session
):
    owner = _make_user(user_repository)
    workspace = _make_workspace(db_session, owner.id)
    document = _make_document(db_session, owner.id, workspace.id)
    asyncio.run(
        chunk_repository.replace_for_document(
            document_id=document.id, owner_id=owner.id,
            chunks=_chunk_dicts("nothing relevant here"),
        )
    )

    matches = asyncio.run(
        chunk_repository.search_by_text(
            owner_id=owner.id, terms=["zzz_no_match_zzz"], mode="or", limit=10
        )
    )

    assert matches == []
