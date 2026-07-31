import pytest

from api.routes.chat import _sse_error_message
from core.config import settings
from services.llm.errors import (
    ProviderNetworkError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)


def _auth_headers(client, email: str = "chat-errors@example.com") -> dict:
    client.post(
        "/users", json={"email": email, "name": "Chat Errors User", "password": "secret123"}
    )
    response = client.post(
        "/auth/login", json={"email": email, "password": "secret123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _raise(error: Exception):
    async def _generate(prompt: str):
        raise error

    return _generate


# --- POST /chat: typed provider errors map to distinct HTTP statuses ---
# client.fake_llm's generate() is monkeypatched directly on the FIXTURE's
# instance (not the class) for exactly one test each — this is what lets
# each test simulate a different real-world provider failure without a
# real OpenAI/Anthropic account, reusing the exact same fake every other
# chat test in this suite already depends on.


def test_provider_rate_limit_returns_429(client):
    headers = _auth_headers(client, email="chat-errors-429@example.com")
    client.fake_llm.generate = _raise(ProviderRateLimitError("rate limited"))

    response = client.post("/chat", headers=headers, json={"question": "anything"})

    assert response.status_code == 429


def test_provider_timeout_returns_504(client):
    headers = _auth_headers(client, email="chat-errors-504@example.com")
    client.fake_llm.generate = _raise(ProviderTimeoutError("timed out"))

    response = client.post("/chat", headers=headers, json={"question": "anything"})

    assert response.status_code == 504


def test_provider_network_error_returns_502(client):
    headers = _auth_headers(client, email="chat-errors-502@example.com")
    client.fake_llm.generate = _raise(ProviderNetworkError("connection failed"))

    response = client.post("/chat", headers=headers, json={"question": "anything"})

    assert response.status_code == 502


def test_provider_unavailable_returns_503(client):
    headers = _auth_headers(client, email="chat-errors-503@example.com")
    client.fake_llm.generate = _raise(ProviderUnavailableError("provider down"))

    response = client.post("/chat", headers=headers, json={"question": "anything"})

    assert response.status_code == 503


# --- _sse_error_message(): the per-error-type message shown in the SSE
# error frame ---
# Tested as a plain function, not through the HTTP layer — verified
# directly (see the route-level test below) that TestClient's default
# raise_server_exceptions=True re-raises an exception that occurs mid-
# stream rather than letting it surface as observable response bytes, so
# there is no way to read the SSE `{"error": ...}` frame's actual message
# text back out through client.post() for this specific failure mode.
# This is a real, discovered limitation of testing a mid-stream failure
# through Starlette's TestClient — not a reason to leave the per-type
# message logic untested; it's a pure function, so it's tested directly.


@pytest.mark.parametrize(
    ("error", "expected_substring"),
    [
        (ProviderRateLimitError("x"), "rate-limiting"),
        (ProviderTimeoutError("x"), "took too long"),
        (ProviderNetworkError("x"), "Could not reach"),
        (ProviderUnavailableError("x"), "unavailable"),
        (RuntimeError("something else entirely"), "could not be completed"),
    ],
)
def test_sse_error_message_distinguishes_provider_failure_types(error, expected_substring):
    assert expected_substring in _sse_error_message(error)


# --- POST /chat/stream: a mid-stream provider failure is not silently
# swallowed ---


def _generate_stream_raising(error: Exception):
    async def _stream(prompt: str):
        raise error
        yield  # pragma: no cover - unreachable, makes this an async generator

    return _stream


def test_stream_provider_failure_is_not_silently_swallowed(client):
    # TestClient's default raise_server_exceptions=True re-raises an
    # exception that occurs while the streaming response body is being
    # consumed (verified directly — see this file's own note above),
    # rather than delivering a truncated/partial response the way a real
    # deployed server would. That re-raise IS the observable signal this
    # test locks in: the failure propagates all the way through, it is
    # never caught and discarded somewhere in the streaming pipeline.
    headers = _auth_headers(client, email="chat-errors-stream-swallow@example.com")
    client.fake_llm.generate_stream = _generate_stream_raising(
        ProviderRateLimitError("rate limited")
    )

    with pytest.raises(ProviderRateLimitError):
        client.post("/chat/stream", headers=headers, json={"question": "anything"})


# --- STREAMING_ENABLED config toggle ---


def test_stream_returns_503_when_streaming_disabled(client, monkeypatch):
    headers = _auth_headers(client, email="chat-errors-disabled@example.com")
    monkeypatch.setattr(settings, "streaming_enabled", False)

    response = client.post(
        "/chat/stream", headers=headers, json={"question": "anything"}
    )

    assert response.status_code == 503


def test_stream_works_normally_when_streaming_enabled(client):
    headers = _auth_headers(client, email="chat-errors-enabled@example.com")

    response = client.post(
        "/chat/stream", headers=headers, json={"question": "What is OpsMind?"}
    )

    assert response.status_code == 200
