import io
import os
import uuid


def _register_and_login(client, email: str = "doc-user@example.com") -> str:
    client.post(
        "/users", json={"email": email, "name": "Doc User", "password": "secret123"}
    )
    response = client.post("/auth/login", json={"email": email, "password": "secret123"})
    return response.json()["access_token"]


def _auth_headers(client, email: str = "doc-user@example.com") -> dict:
    token = _register_and_login(client, email)
    return {"Authorization": f"Bearer {token}"}


def test_upload_document_returns_202(client):
    # 202, not 201: the row is created, but ingestion is still pending —
    # see api/routes/documents.py's upload_document for the full reasoning.
    headers = _auth_headers(client)
    response = client.post(
        "/documents",
        headers=headers,
        files={"file": ("notes.txt", io.BytesIO(b"hello world"), "text/plain")},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["filename"] == "notes.txt"
    assert body["size_bytes"] == len(b"hello world")
    # response_model serialization happens before BackgroundTasks run (per
    # FastAPI/Starlette's execution order), so this reliably reflects the
    # row's state at creation time, not whatever ingestion later does to it.
    assert body["status"] == "uploaded"


def test_upload_without_auth_returns_401(client):
    response = client.post(
        "/documents",
        files={"file": ("notes.txt", io.BytesIO(b"hello world"), "text/plain")},
    )
    assert response.status_code == 401


def test_upload_empty_file_returns_400(client):
    headers = _auth_headers(client)
    response = client.post(
        "/documents",
        headers=headers,
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
    )
    assert response.status_code == 400


def test_upload_file_exceeding_max_size_returns_413(client):
    # conftest.py's override_get_document_service builds DocumentService
    # with the same 20MB max_size_bytes as production (core/config.py) —
    # one byte over that limit is what actually exercises the
    # FileTooLargeError -> 413 mapping, never proven anywhere else in
    # this suite before this test.
    headers = _auth_headers(client, email="doc-toolarge@example.com")
    oversized = b"a" * (20 * 1024 * 1024 + 1)
    response = client.post(
        "/documents",
        headers=headers,
        files={"file": ("big.txt", io.BytesIO(oversized), "text/plain")},
    )
    assert response.status_code == 413


def test_list_documents_without_auth_returns_401(client):
    response = client.get("/documents")
    assert response.status_code == 401


def test_get_document_without_auth_returns_401(client):
    response = client.get(f"/documents/{uuid.uuid4()}")
    assert response.status_code == 401


def test_list_documents_only_returns_own(client):
    headers_a = _auth_headers(client, email="owner-a@example.com")
    client.post(
        "/documents",
        headers=headers_a,
        files={"file": ("a.txt", io.BytesIO(b"from a"), "text/plain")},
    )

    headers_b = _auth_headers(client, email="owner-b@example.com")
    response = client.get("/documents", headers=headers_b)

    assert response.status_code == 200
    assert response.json() == []


def test_get_document_owned_by_another_user_returns_404(client):
    headers_a = _auth_headers(client, email="owner-a2@example.com")
    upload = client.post(
        "/documents",
        headers=headers_a,
        files={"file": ("a.txt", io.BytesIO(b"from a"), "text/plain")},
    )
    document_id = upload.json()["id"]

    headers_b = _auth_headers(client, email="owner-b2@example.com")
    response = client.get(f"/documents/{document_id}", headers=headers_b)

    assert response.status_code == 404


def test_delete_document_returns_204_and_removes_file_from_disk(client):
    headers = _auth_headers(client, email="deleter@example.com")
    upload = client.post(
        "/documents",
        headers=headers,
        files={"file": ("a.txt", io.BytesIO(b"delete me"), "text/plain")},
    )
    document_id = upload.json()["id"]
    storage_key = os.listdir(client.storage_dir)[0]
    file_path = os.path.join(client.storage_dir, storage_key)
    assert os.path.exists(file_path)

    response = client.delete(f"/documents/{document_id}", headers=headers)

    assert response.status_code == 204
    assert not os.path.exists(file_path)

    # gone from the DB too, not just the disk
    get_response = client.get(f"/documents/{document_id}", headers=headers)
    assert get_response.status_code == 404


def test_delete_document_owned_by_another_user_returns_404(client):
    headers_a = _auth_headers(client, email="owner-a3@example.com")
    upload = client.post(
        "/documents",
        headers=headers_a,
        files={"file": ("a.txt", io.BytesIO(b"from a"), "text/plain")},
    )
    document_id = upload.json()["id"]

    headers_b = _auth_headers(client, email="owner-b3@example.com")
    response = client.delete(f"/documents/{document_id}", headers=headers_b)

    assert response.status_code == 404


def test_delete_document_without_auth_returns_401(client):
    response = client.delete(f"/documents/{uuid.uuid4()}")
    assert response.status_code == 401
