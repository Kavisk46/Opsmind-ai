import shutil
import tempfile
import uuid

import pytest

from core.vector_store import VectorStore

# Real ChromaDB, not a fake — deliberately. VectorStore has no network
# dependency at all (chromadb.PersistentClient is embedded, writing to
# local disk, same relationship SQLite has to a full database server —
# see VectorStore's own docstring), so faking it here would hide exactly
# the translation logic (page_number's -1 sentinel, owner_id scoping,
# distance-to-similarity conversion) that only the REAL class actually
# performs. FakeVectorStore (tests/test_retrieval_service.py) exists to
# isolate RetrievalService FROM this class; this file tests the class
# itself.


@pytest.fixture()
def vector_store():
    persist_dir = tempfile.mkdtemp()
    store = VectorStore(persist_dir)
    yield store
    shutil.rmtree(persist_dir, ignore_errors=True)


def _vec(*values: float) -> list[float]:
    return list(values)


# --- add_chunks / query round trip ---


def test_query_returns_the_closest_chunk_by_embedding(vector_store):
    document_id = str(uuid.uuid4())
    owner_id = str(uuid.uuid4())
    vector_store.add_chunks(
        document_id=document_id,
        owner_id=owner_id,
        chunks=["about deploys", "about billing"],
        embeddings=[_vec(1.0, 0.0), _vec(0.0, 1.0)],
    )

    results = vector_store.query(query_embedding=_vec(1.0, 0.0), owner_id=owner_id, top_k=1)

    assert len(results) == 1
    assert results[0]["text"] == "about deploys"
    assert results[0]["document_id"] == document_id
    assert results[0]["chunk_index"] == 0
    # Identical vector to the stored one -> cosine similarity of 1.0
    # (this collection is configured hnsw:space="cosine" — see
    # VectorStore's _COLLECTION_METADATA).
    assert results[0]["similarity_score"] == pytest.approx(1.0, abs=1e-6)


def test_query_respects_top_k(vector_store):
    owner_id = str(uuid.uuid4())
    vector_store.add_chunks(
        document_id=str(uuid.uuid4()),
        owner_id=owner_id,
        chunks=["a", "b", "c"],
        embeddings=[_vec(1.0, 0.0), _vec(0.9, 0.1), _vec(0.0, 1.0)],
    )

    results = vector_store.query(query_embedding=_vec(1.0, 0.0), owner_id=owner_id, top_k=2)

    assert len(results) == 2


# --- owner_id scoping ---


def test_query_only_returns_chunks_belonging_to_the_given_owner(vector_store):
    owner_a = str(uuid.uuid4())
    owner_b = str(uuid.uuid4())
    vector_store.add_chunks(
        document_id=str(uuid.uuid4()), owner_id=owner_a,
        chunks=["owner a's chunk"], embeddings=[_vec(1.0, 0.0)],
    )
    vector_store.add_chunks(
        document_id=str(uuid.uuid4()), owner_id=owner_b,
        chunks=["owner b's chunk"], embeddings=[_vec(1.0, 0.0)],
    )

    results = vector_store.query(query_embedding=_vec(1.0, 0.0), owner_id=owner_a, top_k=5)

    assert len(results) == 1
    assert results[0]["text"] == "owner a's chunk"


# --- page_number sentinel translation ---


def test_page_number_none_survives_the_round_trip(vector_store):
    # Plain text/Markdown documents have no page concept — VectorStore
    # stores this as an internal -1 sentinel (ChromaDB metadata can't
    # hold None), translated back to None on the way out. This test
    # exists specifically to prove that translation happens in BOTH
    # directions and no caller outside core/ ever sees -1 leak through.
    owner_id = str(uuid.uuid4())
    vector_store.add_chunks(
        document_id=str(uuid.uuid4()), owner_id=owner_id,
        chunks=["no page here"], embeddings=[_vec(1.0, 0.0)], page_numbers=[None],
    )

    results = vector_store.query(query_embedding=_vec(1.0, 0.0), owner_id=owner_id, top_k=1)

    assert results[0]["page_number"] is None


def test_page_number_int_survives_the_round_trip(vector_store):
    owner_id = str(uuid.uuid4())
    vector_store.add_chunks(
        document_id=str(uuid.uuid4()), owner_id=owner_id,
        chunks=["from page 3"], embeddings=[_vec(1.0, 0.0)], page_numbers=[3],
    )

    results = vector_store.query(query_embedding=_vec(1.0, 0.0), owner_id=owner_id, top_k=1)

    assert results[0]["page_number"] == 3


# --- delete_by_document / count ---


def test_delete_by_document_removes_only_that_documents_chunks(vector_store):
    owner_id = str(uuid.uuid4())
    keep_id = str(uuid.uuid4())
    remove_id = str(uuid.uuid4())
    vector_store.add_chunks(
        document_id=keep_id, owner_id=owner_id,
        chunks=["keep me"], embeddings=[_vec(1.0, 0.0)],
    )
    vector_store.add_chunks(
        document_id=remove_id, owner_id=owner_id,
        chunks=["remove me"], embeddings=[_vec(0.0, 1.0)],
    )

    vector_store.delete_by_document(document_id=remove_id)

    results = vector_store.query(query_embedding=_vec(0.5, 0.5), owner_id=owner_id, top_k=5)
    assert [r["text"] for r in results] == ["keep me"]


def test_count_reflects_additions(vector_store):
    assert vector_store.count() == 0

    vector_store.add_chunks(
        document_id=str(uuid.uuid4()), owner_id=str(uuid.uuid4()),
        chunks=["a", "b"], embeddings=[_vec(1.0, 0.0), _vec(0.0, 1.0)],
    )

    assert vector_store.count() == 2


def test_readding_the_same_document_id_upserts_rather_than_duplicates(vector_store):
    # ids are "<document_id>:<index>" (see add_chunks' docstring) —
    # re-processing the same document should overwrite its old chunks,
    # not accumulate duplicates alongside them.
    document_id = str(uuid.uuid4())
    owner_id = str(uuid.uuid4())
    vector_store.add_chunks(
        document_id=document_id, owner_id=owner_id,
        chunks=["first version"], embeddings=[_vec(1.0, 0.0)],
    )

    vector_store.add_chunks(
        document_id=document_id, owner_id=owner_id,
        chunks=["second version"], embeddings=[_vec(1.0, 0.0)],
    )

    assert vector_store.count() == 1
    results = vector_store.query(query_embedding=_vec(1.0, 0.0), owner_id=owner_id, top_k=5)
    assert [r["text"] for r in results] == ["second version"]
