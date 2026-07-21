import io


def _register_and_login(client, email: str = "doc-user@example.com") -> str:
    client.post(
        "/users", json={"email": email, "name": "Doc User", "password": "secret123"}
    )
    response = client.post("/auth/login", json={"email": email, "password": "secret123"})
    return response.json()["access_token"]


def _auth_headers(client, email: str = "doc-user@example.com") -> dict:
    token = _register_and_login(client, email)
    return {"Authorization": f"Bearer {token}"}


def test_upload_document_returns_201(client):
    headers = _auth_headers(client)
    response = client.post(
        "/documents",
        headers=headers,
        files={"file": ("notes.txt", io.BytesIO(b"hello world"), "text/plain")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "notes.txt"
    assert body["status"] == "uploaded"
    assert body["size_bytes"] == len(b"hello world")


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
