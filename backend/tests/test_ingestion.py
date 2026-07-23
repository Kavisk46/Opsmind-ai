import asyncio
import concurrent.futures
import io
import uuid

from core.storage import LocalStorage
from repositories.document_repository import DocumentRepository
from services.ingestion_service import IngestionService


def _auth_headers(client, email: str = "ingest-user@example.com") -> dict:
    client.post(
        "/users", json={"email": email, "name": "Ingest User", "password": "secret123"}
    )
    response = client.post(
        "/auth/login", json={"email": email, "password": "secret123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_upload_triggers_processing_and_document_becomes_ready(client):
    headers = _auth_headers(client)
    upload = client.post(
        "/documents",
        headers=headers,
        files={
            "file": (
                "notes.txt",
                io.BytesIO(b"OpsMind helps teams find operational bottlenecks."),
                "text/plain",
            )
        },
    )
    document_id = upload.json()["id"]

    # TestClient runs BackgroundTasks synchronously as part of the same
    # request/response cycle (no real worker process involved), so by the
    # time client.post() returns, ingestion has already run to completion
    # — no polling or waiting needed here, unlike a real deployment with a
    # genuinely separate task queue.
    response = client.get(f"/documents/{document_id}", headers=headers)
    assert response.json()["status"] == "ready"


def test_processed_document_chunks_are_indexed_in_vector_store(client):
    headers = _auth_headers(client, email="ingest-user2@example.com")
    before_count = client.vector_store.count()

    client.post(
        "/documents",
        headers=headers,
        files={
            "file": (
                "notes.txt",
                io.BytesIO(b"a" * 2500),  # long enough to produce multiple chunks
                "text/plain",
            )
        },
    )

    after_count = client.vector_store.count()
    assert after_count > before_count


def test_markdown_upload_is_extracted_and_becomes_ready(client):
    headers = _auth_headers(client, email="ingest-user-md@example.com")
    upload = client.post(
        "/documents",
        headers=headers,
        files={
            "file": (
                "notes.md",
                io.BytesIO(
                    b"# Bottleneck Report\n\n"
                    b"The **deployment pipeline** kept stalling last week.\n\n"
                    b"\n\n   \n\n"  # blank/whitespace-only lines clean_text() should collapse
                    b"See [the postmortem](https://example.com) for details."
                ),
                "text/markdown",
            )
        },
    )
    document_id = upload.json()["id"]

    response = client.get(f"/documents/{document_id}", headers=headers)
    assert response.json()["status"] == "ready"


def test_embedding_status_is_visible_while_embedding_runs(client):
    # TestClient runs BackgroundTasks synchronously, so by the time
    # client.post() returns, the document has ALREADY passed through
    # every status including "embedding" — there's no way to catch it
    # mid-flight through the HTTP layer alone. To prove EMBEDDING is a
    # real, observable transition (not just a label that's set and
    # immediately overwritten), this re-runs ingestion directly, using a
    # fake embedding model that checks the document's status FROM THE
    # DATABASE at the exact moment embed() is called — before any
    # embedding work happens, but after _set_status(EMBEDDING) committed.
    headers = _auth_headers(client, email="ingest-embed-status@example.com")
    upload = client.post(
        "/documents",
        headers=headers,
        files={"file": ("notes.txt", io.BytesIO(b"some content"), "text/plain")},
    )
    document_id = uuid.UUID(upload.json()["id"])

    status_seen_during_embed = []

    class StatusCheckingEmbeddingModel:
        def embed(self, texts):
            async def _check_status() -> str:
                async with client.session_factory() as session:
                    document = await DocumentRepository(session).get_by_id(document_id)
                    return document.status

            # embed() is called synchronously from INSIDE process_document's
            # already-running event loop (driven by asyncio.run() below) —
            # calling asyncio.run() again here directly would raise
            # "cannot be called from a running event loop." Running it in
            # a separate thread gives it a fresh loop of its own; the
            # session_factory's connect_args={"check_same_thread": False}
            # (set up in conftest.py from the start) is exactly what makes
            # sharing that SQLite connection across threads safe.
            with concurrent.futures.ThreadPoolExecutor() as executor:
                status = executor.submit(asyncio.run, _check_status()).result()
            status_seen_during_embed.append(status)
            return [[1.0] * 8 for _ in texts]

    service = IngestionService(
        session_factory=client.session_factory,
        storage=LocalStorage(client.storage_dir),
        embedding_model=StatusCheckingEmbeddingModel(),
        vector_store=client.vector_store,
        chunk_size=1000,
        chunk_overlap=200,
    )
    asyncio.run(service.process_document(document_id))

    assert status_seen_during_embed == ["embedding"]

    final = client.get(f"/documents/{document_id}/status", headers=headers)
    assert final.json()["status"] == "ready"


def test_document_status_endpoint_returns_error_message_on_failure(client):
    headers = _auth_headers(client, email="ingest-user-failmsg@example.com")
    upload = client.post(
        "/documents",
        headers=headers,
        files={
            "file": (
                "image.png",
                io.BytesIO(b"not a real image"),
                "image/png",
            )
        },
    )
    document_id = upload.json()["id"]

    response = client.get(f"/documents/{document_id}/status", headers=headers)
    body = response.json()
    assert body["status"] == "failed"
    assert body["error_message"]  # non-empty — the actual exception text


def test_unsupported_content_type_marks_document_failed(client):
    headers = _auth_headers(client, email="ingest-user3@example.com")
    upload = client.post(
        "/documents",
        headers=headers,
        files={
            "file": (
                "image.png",
                io.BytesIO(b"not really a png, but content_type is unsupported"),
                "image/png",
            )
        },
    )
    document_id = upload.json()["id"]

    response = client.get(f"/documents/{document_id}", headers=headers)
    assert response.json()["status"] == "failed"


def test_deleting_document_removes_its_vectors(client):
    headers = _auth_headers(client, email="ingest-user4@example.com")
    upload = client.post(
        "/documents",
        headers=headers,
        files={"file": ("notes.txt", io.BytesIO(b"a" * 2500), "text/plain")},
    )
    document_id = upload.json()["id"]

    count_after_upload = client.vector_store.count()
    assert count_after_upload > 0

    client.delete(f"/documents/{document_id}", headers=headers)

    count_after_delete = client.vector_store.count()
    assert count_after_delete == 0
