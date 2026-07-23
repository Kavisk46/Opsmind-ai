import uuid


def _auth_headers(client, email: str = "conv-user@example.com") -> dict:
    client.post(
        "/users", json={"email": email, "name": "Conv User", "password": "secret123"}
    )
    response = client.post(
        "/auth/login", json={"email": email, "password": "secret123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_conversations_without_auth_returns_401(client):
    response = client.get("/conversations")
    assert response.status_code == 401


# --- create ---


def test_create_conversation_returns_201(client):
    headers = _auth_headers(client)
    response = client.post("/conversations", headers=headers, json={"title": "My chat"})

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "My chat"
    assert body["id"]


def test_create_conversation_defaults_title_when_omitted(client):
    headers = _auth_headers(client, email="conv-user2@example.com")
    response = client.post("/conversations", headers=headers, json={})

    assert response.status_code == 201
    assert response.json()["title"] == "New conversation"


# --- list ---


def test_list_conversations_returns_only_the_callers_own(client):
    headers_a = _auth_headers(client, email="conv-owner-a@example.com")
    headers_b = _auth_headers(client, email="conv-owner-b@example.com")

    client.post("/conversations", headers=headers_a, json={"title": "A's chat"})
    client.post("/conversations", headers=headers_b, json={"title": "B's chat"})

    response = client.get("/conversations", headers=headers_a)

    assert response.status_code == 200
    titles = [c["title"] for c in response.json()]
    assert titles == ["A's chat"]


def test_list_conversations_orders_most_recently_active_first(client):
    headers = _auth_headers(client, email="conv-order@example.com")
    first = client.post(
        "/conversations", headers=headers, json={"title": "first"}
    ).json()
    client.post("/conversations", headers=headers, json={"title": "second"})

    # Sending a chat message against the FIRST conversation should bump
    # its updated_at past the second (untouched) conversation — real proof
    # that list ordering reflects actual message activity, not just
    # creation order.
    client.post(
        "/chat",
        headers=headers,
        json={"question": "hello", "conversation_id": first["id"]},
    )

    response = client.get("/conversations", headers=headers)
    titles = [c["title"] for c in response.json()]
    assert titles[0] == "first"


# --- get detail ---


def test_get_conversation_returns_messages(client):
    headers = _auth_headers(client, email="conv-detail@example.com")
    created = client.post(
        "/conversations", headers=headers, json={"title": "detail chat"}
    ).json()
    client.post(
        "/chat",
        headers=headers,
        json={"question": "What is OpsMind?", "conversation_id": created["id"]},
    )

    response = client.get(f"/conversations/{created['id']}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    roles = [m["role"] for m in body["messages"]]
    assert roles == ["user", "assistant"]
    assert body["messages"][0]["content"] == "What is OpsMind?"


def test_get_nonexistent_conversation_returns_404(client):
    headers = _auth_headers(client, email="conv-404@example.com")
    response = client.get(f"/conversations/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404


def test_get_another_users_conversation_returns_404(client):
    headers_a = _auth_headers(client, email="conv-owner-c@example.com")
    headers_b = _auth_headers(client, email="conv-owner-d@example.com")
    created = client.post(
        "/conversations", headers=headers_a, json={"title": "private"}
    ).json()

    response = client.get(f"/conversations/{created['id']}", headers=headers_b)
    assert response.status_code == 404


# --- delete ---


def test_delete_conversation_returns_204_and_removes_it(client):
    headers = _auth_headers(client, email="conv-delete@example.com")
    created = client.post(
        "/conversations", headers=headers, json={"title": "to delete"}
    ).json()

    delete_response = client.delete(f"/conversations/{created['id']}", headers=headers)
    assert delete_response.status_code == 204

    get_response = client.get(f"/conversations/{created['id']}", headers=headers)
    assert get_response.status_code == 404


def test_delete_nonexistent_conversation_returns_404(client):
    headers = _auth_headers(client, email="conv-delete-404@example.com")
    response = client.delete(f"/conversations/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404


def test_delete_another_users_conversation_returns_404(client):
    headers_a = _auth_headers(client, email="conv-owner-e@example.com")
    headers_b = _auth_headers(client, email="conv-owner-f@example.com")
    created = client.post(
        "/conversations", headers=headers_a, json={"title": "private"}
    ).json()

    response = client.delete(f"/conversations/{created['id']}", headers=headers_b)
    assert response.status_code == 404
