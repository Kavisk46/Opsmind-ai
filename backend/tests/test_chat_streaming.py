import asyncio
import json
import uuid

from repositories.message_repository import MessageRepository


def _auth_headers(client, email: str = "stream-user@example.com") -> dict:
    client.post(
        "/users", json={"email": email, "name": "Stream User", "password": "secret123"}
    )
    response = client.post(
        "/auth/login", json={"email": email, "password": "secret123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _parse_sse_events(text: str) -> list[dict]:
    events = []
    for block in text.split("\n\n"):
        block = block.strip()
        if block.startswith("data: "):
            events.append(json.loads(block[len("data: ") :]))
    return events


def test_chat_stream_without_auth_returns_401(client):
    response = client.post("/chat/stream", json={"question": "hi"})
    assert response.status_code == 401


def test_chat_stream_empty_question_returns_400(client):
    headers = _auth_headers(client, email="stream-empty@example.com")
    response = client.post("/chat/stream", headers=headers, json={"question": "   "})
    assert response.status_code == 400


def test_chat_stream_with_nonexistent_conversation_returns_404(client):
    headers = _auth_headers(client, email="stream-404@example.com")
    response = client.post(
        "/chat/stream",
        headers=headers,
        json={"question": "hello", "conversation_id": str(uuid.uuid4())},
    )
    assert response.status_code == 404


def test_chat_stream_returns_sse_events_with_incremental_deltas(client):
    headers = _auth_headers(client)
    response = client.post(
        "/chat/stream", headers=headers, json={"question": "What is OpsMind?"}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "X-Conversation-ID" in response.headers

    events = _parse_sse_events(response.text)
    delta_events = [e for e in events if "delta" in e]
    # FakeLLM (see conftest.py) yields 6 separate words — real proof this
    # arrived as multiple incremental chunks, not the whole answer in one
    # event the way the non-streaming /chat endpoint would return it.
    assert len(delta_events) == 6
    full_answer = "".join(e["delta"] for e in delta_events)
    assert full_answer == "This is a fake streamed answer."

    final = events[-1]
    assert final["done"] is True
    assert final["tool_used"] == "rag_retrieval"
    assert "citations" in final


def test_chat_stream_persists_assistant_message_after_completion(client):
    headers = _auth_headers(client, email="stream-persist@example.com")
    response = client.post(
        "/chat/stream", headers=headers, json={"question": "hello there"}
    )
    conversation_id = uuid.UUID(response.headers["X-Conversation-ID"])

    async def _fetch_messages():
        async with client.session_factory() as session:
            return await MessageRepository(session).list_by_conversation(conversation_id)

    messages = asyncio.run(_fetch_messages())
    roles = [m.role for m in messages]
    assert roles == ["user", "assistant"]
    assert messages[0].content == "hello there"
    assert messages[1].content == "This is a fake streamed answer."


def test_chat_stream_routes_metadata_question_correctly(client):
    headers = _auth_headers(client, email="stream-metadata@example.com")
    response = client.post(
        "/chat/stream",
        headers=headers,
        json={"question": "How many documents have I uploaded?"},
    )

    events = _parse_sse_events(response.text)
    final = events[-1]
    assert final["tool_used"] == "document_metadata"
    assert final["citations"] == []
