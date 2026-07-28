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
    # with the same 25MB max_size_bytes as production (core/config.py) —
    # one byte over that limit is what actually exercises the
    # FileTooLargeError -> 413 mapping, never proven anywhere else in
    # this suite before this test.
    headers = _auth_headers(client, email="doc-toolarge@example.com")
    oversized = b"a" * (25 * 1024 * 1024 + 1)
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
    # storage_key is namespaced "{owner_id}/{uuid}{ext}" (see
    # DocumentService.upload_document), so the saved file is one level
    # deeper than client.storage_dir itself — walk instead of assuming a
    # flat top-level listing.
    saved_files = [
        os.path.join(root, name)
        for root, _dirs, names in os.walk(client.storage_dir)
        for name in names
    ]
    assert len(saved_files) == 1
    file_path = saved_files[0]
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


def test_uploading_a_duplicate_filename_returns_409(client):
    headers = _auth_headers(client, email="doc-dup@example.com")
    client.post(
        "/documents",
        headers=headers,
        files={"file": ("report.txt", io.BytesIO(b"first"), "text/plain")},
    )

    response = client.post(
        "/documents",
        headers=headers,
        files={"file": ("report.txt", io.BytesIO(b"second"), "text/plain")},
    )

    assert response.status_code == 409


def test_same_filename_allowed_for_different_users(client):
    headers_a = _auth_headers(client, email="doc-shared-a@example.com")
    client.post(
        "/documents",
        headers=headers_a,
        files={"file": ("shared.txt", io.BytesIO(b"from a"), "text/plain")},
    )

    headers_b = _auth_headers(client, email="doc-shared-b@example.com")
    response = client.post(
        "/documents",
        headers=headers_b,
        files={"file": ("shared.txt", io.BytesIO(b"from b"), "text/plain")},
    )

    assert response.status_code == 202


def test_upload_rejects_a_genuinely_unsupported_type(client):
    headers = _auth_headers(client, email="doc-unsupported@example.com")
    response = client.post(
        "/documents",
        headers=headers,
        files={"file": ("archive.zip", io.BytesIO(b"PK\x03\x04"), "application/zip")},
    )
    assert response.status_code == 415


def test_uploaded_filename_is_sanitized(client):
    headers = _auth_headers(client, email="doc-sanitize@example.com")
    response = client.post(
        "/documents",
        headers=headers,
        files={
            "file": (
                "../../etc/passwd.txt",
                io.BytesIO(b"hello"),
                "text/plain",
            )
        },
    )
    assert response.status_code == 202
    assert response.json()["filename"] == "passwd.txt"


def test_search_without_auth_returns_401(client):
    response = client.get("/documents/search")
    assert response.status_code == 401


def test_search_matches_filename_substring(client):
    headers = _auth_headers(client, email="doc-search@example.com")
    client.post(
        "/documents", headers=headers,
        files={"file": ("Quarterly Report.txt", io.BytesIO(b"a"), "text/plain")},
    )
    client.post(
        "/documents", headers=headers,
        files={"file": ("notes.txt", io.BytesIO(b"b"), "text/plain")},
    )

    response = client.get("/documents/search", headers=headers, params={"q": "report"})

    assert response.status_code == 200
    assert [d["filename"] for d in response.json()] == ["Quarterly Report.txt"]


def test_search_only_returns_the_current_users_documents(client):
    headers_a = _auth_headers(client, email="doc-search-a@example.com")
    client.post(
        "/documents", headers=headers_a,
        files={"file": ("mine.txt", io.BytesIO(b"a"), "text/plain")},
    )
    headers_b = _auth_headers(client, email="doc-search-b@example.com")

    response = client.get("/documents/search", headers=headers_b)

    assert response.status_code == 200
    assert response.json() == []


def test_search_sort_largest_orders_by_size_descending(client):
    headers = _auth_headers(client, email="doc-search-sort@example.com")
    client.post(
        "/documents", headers=headers,
        files={"file": ("small.txt", io.BytesIO(b"a"), "text/plain")},
    )
    client.post(
        "/documents", headers=headers,
        files={"file": ("big.txt", io.BytesIO(b"a" * 1000), "text/plain")},
    )

    response = client.get(
        "/documents/search", headers=headers, params={"sort": "largest"}
    )

    assert [d["filename"] for d in response.json()] == ["big.txt", "small.txt"]


def test_search_with_invalid_sort_value_returns_422(client):
    headers = _auth_headers(client, email="doc-search-bad-sort@example.com")
    response = client.get(
        "/documents/search", headers=headers, params={"sort": "not-a-real-option"}
    )
    assert response.status_code == 422


def test_stats_without_auth_returns_401(client):
    response = client.get("/documents/stats")
    assert response.status_code == 401


def test_stats_for_a_new_user_are_all_zero(client):
    headers = _auth_headers(client, email="doc-stats-empty@example.com")

    response = client.get("/documents/stats", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total_documents"] == 0
    assert body["total_storage_bytes"] == 0
    assert body["documents_by_type"] == {}
    assert body["recent_uploads"] == []


def test_stats_reflect_uploaded_documents(client):
    headers = _auth_headers(client, email="doc-stats@example.com")
    client.post(
        "/documents", headers=headers,
        files={"file": ("a.txt", io.BytesIO(b"12345"), "text/plain")},
    )
    client.post(
        "/documents", headers=headers,
        files={"file": ("b.pdf", io.BytesIO(b"1234567890"), "application/pdf")},
    )

    response = client.get("/documents/stats", headers=headers)

    body = response.json()
    assert body["total_documents"] == 2
    assert body["total_storage_bytes"] == 15
    assert body["documents_by_type"] == {"text/plain": 1, "application/pdf": 1}
    assert len(body["recent_uploads"]) == 2


def test_download_without_auth_returns_401(client):
    response = client.get(f"/documents/download/{uuid.uuid4()}")
    assert response.status_code == 401


def test_download_nonexistent_document_returns_404(client):
    headers = _auth_headers(client, email="doc-download-404@example.com")
    response = client.get(f"/documents/download/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404


def test_download_another_users_document_returns_404(client):
    headers_a = _auth_headers(client, email="doc-download-a@example.com")
    upload = client.post(
        "/documents", headers=headers_a,
        files={"file": ("secret.txt", io.BytesIO(b"private"), "text/plain")},
    )
    document_id = upload.json()["id"]

    headers_b = _auth_headers(client, email="doc-download-b@example.com")
    response = client.get(f"/documents/download/{document_id}", headers=headers_b)

    assert response.status_code == 404


def test_download_returns_the_original_bytes_and_filename(client):
    headers = _auth_headers(client, email="doc-download@example.com")
    upload = client.post(
        "/documents", headers=headers,
        files={"file": ("report.txt", io.BytesIO(b"the exact original bytes"), "text/plain")},
    )
    document_id = upload.json()["id"]

    response = client.get(f"/documents/download/{document_id}", headers=headers)

    assert response.status_code == 200
    assert response.content == b"the exact original bytes"
    # Starlette's Response appends "; charset=utf-8" to text/* media
    # types automatically — startswith, not equality, is the correct
    # check here.
    assert response.headers["content-type"].startswith("text/plain")
    assert 'filename="report.txt"' in response.headers["content-disposition"]


def test_uploading_a_png_is_accepted_and_ends_up_ready_not_failed(client):
    # PNG has no text-extraction path (core/text_extraction.py) but IS a
    # legitimate upload (services/document_service.py's
    # ACCEPTED_UPLOAD_CONTENT_TYPES) — this proves the full path end to
    # end: accepted at upload, then the background ingestion task (which
    # TestClient runs synchronously before returning any later response)
    # must mark it READY, never FAILED, for a type it simply can't index.
    headers = _auth_headers(client, email="doc-png@example.com")
    upload = client.post(
        "/documents",
        headers=headers,
        files={"file": ("diagram.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")},
    )
    assert upload.status_code == 202
    document_id = upload.json()["id"]

    response = client.get(f"/documents/{document_id}", headers=headers)

    assert response.json()["status"] == "ready"
