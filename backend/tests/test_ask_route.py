import io

from services.llm.errors import (
    ProviderNetworkError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)


def _auth_headers(client, email: str = "ask-user@example.com") -> dict:
    client.post(
        "/users", json={"email": email, "name": "Ask User", "password": "secret123"}
    )
    response = client.post("/auth/login", json={"email": email, "password": "secret123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _upload_document(client, headers: dict, filename: str = "notes.txt") -> str:
    upload = client.post(
        "/documents",
        headers=headers,
        files={
            "file": (
                filename,
                io.BytesIO(b"OpsMind helps teams find operational bottlenecks."),
                "text/plain",
            )
        },
    )
    # TestClient runs BackgroundTasks synchronously, so ingestion has
    # already completed by the time this returns.
    return upload.json()["id"]


def test_ask_without_auth_returns_401(client):
    response = client.post("/chat/ask", json={"question": "What is OpsMind?"})
    assert response.status_code == 401


def test_ask_with_empty_question_returns_400(client):
    headers = _auth_headers(client)
    response = client.post("/chat/ask", headers=headers, json={"question": "   "})
    assert response.status_code == 400


def test_ask_returns_answer_with_citations_confidence_and_latency(client):
    headers = _auth_headers(client)
    _upload_document(client, headers, filename="bottlenecks.txt")

    response = client.post(
        "/chat/ask", headers=headers, json={"question": "What does OpsMind do?"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "This is a fake answer for testing."
    assert len(body["citations"]) > 0
    assert body["citations"][0]["filename"] == "bottlenecks.txt"
    assert body["citations"][0]["page_number"] is None  # .txt has no pages
    assert body["confidence"] > 0.0
    assert body["latency_ms"] >= 0.0


def test_ask_response_never_includes_a_conversation_id(client):
    # The whole point of this endpoint (see AskService's own docstring):
    # genuinely stateless, no Conversation/Message row created anywhere.
    headers = _auth_headers(client)
    _upload_document(client, headers)

    response = client.post("/chat/ask", headers=headers, json={"question": "anything"})

    assert "conversation_id" not in response.json()


def test_ask_does_not_create_a_conversation(client):
    headers = _auth_headers(client)
    _upload_document(client, headers)

    client.post("/chat/ask", headers=headers, json={"question": "anything"})

    conversations = client.get("/conversations", headers=headers).json()
    assert conversations == []


def test_ask_with_no_documents_returns_zero_confidence_and_no_citations(client):
    headers = _auth_headers(client, email="ask-no-docs@example.com")

    response = client.post("/chat/ask", headers=headers, json={"question": "What is SOC2?"})

    assert response.status_code == 200
    body = response.json()
    assert body["citations"] == []
    assert body["confidence"] == 0.0


# --- typed provider errors map to distinct HTTP statuses, same mapping
# POST /chat already uses (see test_chat_error_handling.py) ---


def _raise(error: Exception):
    async def _generate(prompt: str):
        raise error

    return _generate


def test_provider_rate_limit_returns_429(client):
    headers = _auth_headers(client, email="ask-errors-429@example.com")
    client.fake_llm.generate = _raise(ProviderRateLimitError("rate limited"))

    response = client.post("/chat/ask", headers=headers, json={"question": "anything"})

    assert response.status_code == 429


def test_provider_timeout_returns_504(client):
    headers = _auth_headers(client, email="ask-errors-504@example.com")
    client.fake_llm.generate = _raise(ProviderTimeoutError("timed out"))

    response = client.post("/chat/ask", headers=headers, json={"question": "anything"})

    assert response.status_code == 504


def test_provider_network_error_returns_502(client):
    headers = _auth_headers(client, email="ask-errors-502@example.com")
    client.fake_llm.generate = _raise(ProviderNetworkError("connection failed"))

    response = client.post("/chat/ask", headers=headers, json={"question": "anything"})

    assert response.status_code == 502


def test_provider_unavailable_returns_503(client):
    headers = _auth_headers(client, email="ask-errors-503@example.com")
    client.fake_llm.generate = _raise(ProviderUnavailableError("provider down"))

    response = client.post("/chat/ask", headers=headers, json={"question": "anything"})

    assert response.status_code == 503


# --- permission isolation ---


def test_ask_does_not_leak_another_owners_documents(client):
    owner_a_headers = _auth_headers(client, email="ask-owner-a@example.com")
    owner_b_headers = _auth_headers(client, email="ask-owner-b@example.com")
    _upload_document(client, owner_a_headers, filename="owner-a-secret.txt")

    response = client.post(
        "/chat/ask", headers=owner_b_headers, json={"question": "What does OpsMind do?"}
    )

    assert response.status_code == 200
    filenames = [c["filename"] for c in response.json()["citations"]]
    assert "owner-a-secret.txt" not in filenames
