import io
import uuid


def _auth_headers(client, email: str = "chat-user@example.com") -> dict:
    client.post(
        "/users", json={"email": email, "name": "Chat User", "password": "secret123"}
    )
    response = client.post(
        "/auth/login", json={"email": email, "password": "secret123"}
    )
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


def test_chat_without_auth_returns_401(client):
    response = client.post("/chat", json={"question": "What is OpsMind?"})
    assert response.status_code == 401


def test_chat_returns_answer_with_citations(client):
    headers = _auth_headers(client)
    _upload_document(client, headers, filename="bottlenecks.txt")

    response = client.post(
        "/chat", headers=headers, json={"question": "What does OpsMind do?"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "This is a fake answer for testing."
    assert body["conversation_id"]
    assert body["tool_used"] == "rag_retrieval"
    assert len(body["citations"]) > 0
    assert body["citations"][0]["document_name"] == "bottlenecks.txt"
    assert body["citations"][0]["page_number"] is None  # .txt has no pages


def test_chat_routes_document_count_question_to_metadata_tool(client):
    headers = _auth_headers(client, email="chat-metadata@example.com")
    _upload_document(client, headers, filename="a.txt")
    _upload_document(client, headers, filename="b.txt")

    response = client.post(
        "/chat",
        headers=headers,
        json={"question": "How many documents have I uploaded?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["tool_used"] == "document_metadata"
    # The metadata tool never produces chunk-level citations — there's no
    # chunk involved in answering a count/list question.
    assert body["citations"] == []
    # Real proof routing worked, not just that the API accepted the
    # question: the assembled prompt contains the actual document count
    # and filenames read from Postgres, not semantically-retrieved chunk
    # text — exactly what RAG could NOT have produced for this question.
    assert "2 document(s)" in client.fake_llm.last_prompt
    assert "a.txt" in client.fake_llm.last_prompt
    assert "b.txt" in client.fake_llm.last_prompt


def test_chat_starts_new_conversation_when_none_given(client):
    headers = _auth_headers(client, email="chat-user2@example.com")
    _upload_document(client, headers)

    first = client.post("/chat", headers=headers, json={"question": "First question"})
    second = client.post("/chat", headers=headers, json={"question": "Second question"})

    assert first.json()["conversation_id"] != second.json()["conversation_id"]


def test_chat_continues_existing_conversation_with_history(client):
    headers = _auth_headers(client, email="chat-user3@example.com")
    _upload_document(client, headers)

    first = client.post(
        "/chat", headers=headers, json={"question": "My name is Ada."}
    )
    conversation_id = first.json()["conversation_id"]

    second = client.post(
        "/chat",
        headers=headers,
        json={"question": "What is my name?", "conversation_id": conversation_id},
    )
    assert second.status_code == 200
    assert second.json()["conversation_id"] == conversation_id

    # Real proof conversation memory works: the assembled prompt for the
    # second turn actually contains the first turn's exchange, not just
    # that the API accepted the same conversation_id.
    assert "My name is Ada." in client.fake_llm.last_prompt
    assert "This is a fake answer for testing." in client.fake_llm.last_prompt


def test_chat_with_nonexistent_conversation_returns_404(client):
    headers = _auth_headers(client, email="chat-user4@example.com")
    response = client.post(
        "/chat",
        headers=headers,
        json={"question": "hello", "conversation_id": str(uuid.uuid4())},
    )
    assert response.status_code == 404


def test_chat_with_another_users_conversation_returns_404(client):
    headers_a = _auth_headers(client, email="chat-owner-a@example.com")
    first = client.post("/chat", headers=headers_a, json={"question": "hello"})
    conversation_id = first.json()["conversation_id"]

    headers_b = _auth_headers(client, email="chat-owner-b@example.com")
    response = client.post(
        "/chat",
        headers=headers_b,
        json={"question": "hello", "conversation_id": conversation_id},
    )
    assert response.status_code == 404


def test_chat_empty_question_returns_400(client):
    headers = _auth_headers(client, email="chat-user5@example.com")
    response = client.post("/chat", headers=headers, json={"question": "   "})
    assert response.status_code == 400


# /chat/stream is now a real, working endpoint (this phase's streaming
# work) — its tests live in tests/test_chat_streaming.py, not here. The
# old "returns 501" placeholder test is gone; that was correct behavior
# for the honest stub it used to be, not a regression to preserve.
