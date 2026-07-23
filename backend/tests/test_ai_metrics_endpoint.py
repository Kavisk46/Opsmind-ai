import asyncio
import io

from core.security import hash_password
from models.user import User


def _auth_headers(client, email: str = "aimetrics-user@example.com") -> dict:
    client.post(
        "/users", json={"email": email, "name": "AI Metrics User", "password": "secret123"}
    )
    response = client.post(
        "/auth/login", json={"email": email, "password": "secret123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_admin_and_login(client, email: str = "aimetrics-admin@example.com") -> str:
    # Same reasoning as tests/test_users_rbac.py's identical helper: no
    # public endpoint can create an admin, so the test inserts one
    # directly against the test database, matching how a real deployment
    # would only ever grant admin via a trusted, out-of-band path.
    async def _create() -> None:
        async with client.session_factory() as session:
            user = User(
                email=email,
                name="AI Metrics Admin",
                password_hash=hash_password("secret123"),
                role="admin",
            )
            session.add(user)
            await session.commit()

    asyncio.run(_create())
    response = client.post(
        "/auth/login", json={"email": email, "password": "secret123"}
    )
    return response.json()["access_token"]


def _upload_document(client, headers: dict) -> str:
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
    return upload.json()["id"]


def test_ai_metrics_without_auth_returns_401(client):
    response = client.get("/internal/ai-metrics")
    assert response.status_code == 401


def test_ai_metrics_as_member_returns_403(client):
    headers = _auth_headers(client)
    response = client.get("/internal/ai-metrics", headers=headers)
    assert response.status_code == 403


def test_ai_metrics_as_admin_returns_empty_summary_before_any_chat(client):
    token = _create_admin_and_login(client)
    response = client.get(
        "/internal/ai-metrics", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["llm"] == {"total_requests": 0}
    assert body["retrieval"] == {"total_requests": 0}
    assert body["generation_eval"] == {"total_answers": 0}


def test_ai_metrics_reflects_a_real_chat_request(client):
    headers = _auth_headers(client, email="aimetrics-chat-user@example.com")
    _upload_document(client, headers)
    client.post("/chat", headers=headers, json={"question": "What does OpsMind do?"})

    admin_token = _create_admin_and_login(client, email="aimetrics-admin2@example.com")
    response = client.get(
        "/internal/ai-metrics", headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert response.status_code == 200
    body = response.json()

    # The fake LLM (tests/conftest.py's FakeLLM) reports no token counts,
    # matching the local provider's real honest behavior — but the call
    # itself, and the eager retrieval it triggered, both genuinely
    # happened and must be reflected here.
    assert body["llm"]["total_requests"] == 1
    assert body["llm"]["success_count"] == 1
    assert body["retrieval"]["total_requests"] == 1
    assert body["retrieval"]["avg_chunk_count"] > 0
    assert body["generation_eval"]["total_answers"] == 1


def test_ai_metrics_service_directly_reflects_chat_request(client):
    # White-box check using the fixture-exposed service (see
    # tests/conftest.py) rather than only going through the HTTP layer —
    # proves AIOrchestrator's instrumentation itself is what populated
    # this, not just that the endpoint returns SOME 200 response.
    headers = _auth_headers(client, email="aimetrics-direct-user@example.com")
    _upload_document(client, headers)
    client.post("/chat", headers=headers, json={"question": "What does OpsMind do?"})

    summary = client.ai_metrics_service.summary()
    assert summary["llm"]["total_requests"] == 1
    assert summary["retrieval"]["total_requests"] == 1
