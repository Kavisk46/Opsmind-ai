import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import ValidationError

from core.config import Settings
from services.llm.anthropic_provider import AnthropicProvider
from services.llm.anthropic_provider import MissingAPIKeyError as AnthropicMissingAPIKeyError
from services.llm.errors import (
    ProviderNetworkError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from services.llm.factory import get_llm_provider
from services.llm.local_provider import LocalTransformersProvider
from services.llm.ollama_provider import OllamaProvider
from services.llm.openai_provider import MissingAPIKeyError, OpenAIProvider
from services.llm.protocol import ProviderHealth

# --- Configuration-driven provider selection ---


def test_settings_rejects_unknown_llm_provider():
    # llm_provider is a Literal, not a plain str — Pydantic rejects an
    # invalid value at startup, before the factory is ever called.
    with pytest.raises(ValidationError):
        Settings(llm_provider="bogus")


def test_factory_returns_local_provider_by_default():
    settings = Settings()
    assert isinstance(get_llm_provider(settings), LocalTransformersProvider)


def test_factory_returns_openai_provider_when_configured():
    settings = Settings(llm_provider="openai", llm_api_key="sk-test")
    assert isinstance(get_llm_provider(settings), OpenAIProvider)


def test_factory_returns_real_anthropic_provider_when_configured():
    settings = Settings(llm_provider="anthropic", llm_api_key="sk-ant-test")
    assert isinstance(get_llm_provider(settings), AnthropicProvider)


def test_factory_returns_ollama_stub_when_configured():
    settings = Settings(llm_provider="ollama")
    assert isinstance(get_llm_provider(settings), OllamaProvider)


# --- Local provider ---


def test_local_provider_reports_not_loaded_before_first_use():
    # Cheap to construct, no real model touched — proves the lazy-loading
    # contract without needing to actually download/run a model in a test.
    provider = LocalTransformersProvider(model_name="not-a-real-model")
    assert provider.is_loaded is False


def test_local_provider_stream_yields_full_text_as_one_chunk():
    # Pseudo-streaming, not real token-by-token streaming (see
    # LocalTransformersProvider.generate_stream()'s docstring) —
    # _generate_sync is monkeypatched so this test never touches a real
    # model, same reasoning as every other local-provider test here.
    provider = LocalTransformersProvider(model_name="not-a-real-model")
    provider._generate_sync = lambda prompt: "a fake local answer"

    async def _collect():
        return [chunk async for chunk in provider.generate_stream("hello")]

    chunks = asyncio.run(_collect())
    assert chunks == ["a fake local answer"]


def test_local_provider_model_name_and_health():
    provider = LocalTransformersProvider(model_name="not-a-real-model")
    assert provider.model_name == "not-a-real-model"
    assert provider.health() == ProviderHealth(is_healthy=True)


# --- OpenAI provider ---
# No OPENAI_API_KEY exists anywhere in this project's environment — these
# tests verify the provider's OWN logic (the missing-key guard, and
# correctly mapping a response into LLMResponse) using a mocked SDK
# client, never a real network call. This is precisely what dependency
# injection buys here: OpenAIProvider depends on `openai.AsyncOpenAI`
# only at the point of use, so a test can substitute a fake one without
# needing a real API key, real network access, or real billing.


def _openai_provider(api_key: str | None = "sk-test") -> OpenAIProvider:
    return OpenAIProvider(
        api_key=api_key,
        model="gpt-4o-mini",
        temperature=0.0,
        top_p=1.0,
        max_output_tokens=100,
        timeout_seconds=30.0,
    )


def test_openai_provider_raises_without_api_key():
    provider = _openai_provider(api_key=None)
    with pytest.raises(MissingAPIKeyError):
        asyncio.run(provider.generate("hello"))


def test_openai_provider_model_name_and_health():
    assert _openai_provider().model_name == "gpt-4o-mini"
    assert _openai_provider().health() == ProviderHealth(is_healthy=True)
    assert _openai_provider(api_key=None).health() == ProviderHealth(
        is_healthy=False, detail="No API key configured."
    )


def test_openai_provider_maps_response_into_llm_response():
    provider = _openai_provider()

    fake_message = MagicMock(content="a real-looking answer")
    fake_choice = MagicMock(message=fake_message)
    fake_usage = MagicMock(prompt_tokens=42, completion_tokens=7)
    fake_response = MagicMock(choices=[fake_choice], usage=fake_usage)

    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_response)

    with patch("openai.AsyncOpenAI", return_value=fake_client):
        result = asyncio.run(provider.generate("What is OpsMind?"))

    assert result.text == "a real-looking answer"
    assert result.prompt_tokens == 42
    assert result.completion_tokens == 7


def test_openai_provider_stream_raises_without_api_key():
    provider = _openai_provider(api_key=None)

    async def _collect():
        return [chunk async for chunk in provider.generate_stream("hello")]

    with pytest.raises(MissingAPIKeyError):
        asyncio.run(_collect())


def test_openai_provider_streams_incremental_deltas():
    provider = _openai_provider()

    async def fake_sdk_stream():
        for text in ["Hello", ", ", "world!"]:
            chunk = MagicMock()
            chunk.choices = [MagicMock(delta=MagicMock(content=text))]
            yield chunk

    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=fake_sdk_stream())

    async def _collect():
        with patch("openai.AsyncOpenAI", return_value=fake_client):
            return [chunk async for chunk in provider.generate_stream("hi")]

    chunks = asyncio.run(_collect())
    assert chunks == ["Hello", ", ", "world!"]


# --- OpenAI provider: typed error mapping ---
# Each SDK error is a REAL instance of the SDK's own exception class (not
# a bare RuntimeError standing in for it) — this is what actually proves
# _map_sdk_error's isinstance() checks work against the real exception
# hierarchy, not just against a shape this test file made up.

_FAKE_REQUEST = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
_FAKE_RESPONSE = httpx.Response(429, request=_FAKE_REQUEST)


def _openai_rate_limit_error():
    import openai

    return openai.RateLimitError("rate limited", response=_FAKE_RESPONSE, body=None)


def _openai_timeout_error():
    import openai

    return openai.APITimeoutError(request=_FAKE_REQUEST)


def _openai_connection_error():
    import openai

    return openai.APIConnectionError(request=_FAKE_REQUEST)


def _openai_status_error():
    import openai

    return openai.AuthenticationError(
        "bad key", response=httpx.Response(401, request=_FAKE_REQUEST), body=None
    )


@pytest.mark.parametrize(
    ("sdk_error_factory", "expected_type"),
    [
        (_openai_rate_limit_error, ProviderRateLimitError),
        (_openai_timeout_error, ProviderTimeoutError),
        (_openai_connection_error, ProviderNetworkError),
        (_openai_status_error, ProviderUnavailableError),
    ],
)
def test_openai_provider_maps_sdk_errors_to_typed_provider_errors(sdk_error_factory, expected_type):
    provider = _openai_provider()
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(side_effect=sdk_error_factory())

    with patch("openai.AsyncOpenAI", return_value=fake_client):
        with pytest.raises(expected_type):
            asyncio.run(provider.generate("hello"))


# --- Anthropic provider (real, mirroring OpenAIProvider's tests) ---
# Same "no real API key, verify via a mocked SDK client" reasoning as the
# OpenAI section above — see AnthropicProvider's own docstring.


def _anthropic_provider(api_key: str | None = "sk-ant-test") -> AnthropicProvider:
    return AnthropicProvider(
        api_key=api_key,
        model="claude-3-5-haiku-latest",
        temperature=0.0,
        top_p=1.0,
        max_output_tokens=100,
        timeout_seconds=30.0,
    )


def test_anthropic_provider_raises_without_api_key():
    provider = _anthropic_provider(api_key=None)
    with pytest.raises(AnthropicMissingAPIKeyError):
        asyncio.run(provider.generate("hello"))


def test_anthropic_provider_model_name_and_health():
    assert _anthropic_provider().model_name == "claude-3-5-haiku-latest"
    assert _anthropic_provider().health() == ProviderHealth(is_healthy=True)
    assert _anthropic_provider(api_key=None).health() == ProviderHealth(
        is_healthy=False, detail="No API key configured."
    )


def test_anthropic_provider_maps_response_into_llm_response():
    provider = _anthropic_provider()

    fake_block = MagicMock(type="text", text="a real-looking answer")
    fake_usage = MagicMock(input_tokens=42, output_tokens=7)
    fake_response = MagicMock(content=[fake_block], usage=fake_usage)

    fake_client = MagicMock()
    fake_client.messages.create = AsyncMock(return_value=fake_response)

    with patch("anthropic.AsyncAnthropic", return_value=fake_client):
        result = asyncio.run(provider.generate("What is OpsMind?"))

    assert result.text == "a real-looking answer"
    assert result.prompt_tokens == 42
    assert result.completion_tokens == 7


def test_anthropic_provider_stream_raises_without_api_key():
    provider = _anthropic_provider(api_key=None)

    async def _collect():
        return [chunk async for chunk in provider.generate_stream("hello")]

    with pytest.raises(AnthropicMissingAPIKeyError):
        asyncio.run(_collect())


def test_anthropic_provider_streams_incremental_text_deltas():
    provider = _anthropic_provider()

    async def fake_sdk_stream():
        for text in ["Hello", ", ", "world!"]:
            event = MagicMock(type="content_block_delta")
            event.delta = MagicMock(type="text_delta", text=text)
            yield event
        # A non-text event (e.g. message_stop) must be filtered out, not
        # yielded as if it were answer text.
        yield MagicMock(type="message_stop")

    fake_client = MagicMock()
    fake_client.messages.create = AsyncMock(return_value=fake_sdk_stream())

    async def _collect():
        with patch("anthropic.AsyncAnthropic", return_value=fake_client):
            return [chunk async for chunk in provider.generate_stream("hi")]

    chunks = asyncio.run(_collect())
    assert chunks == ["Hello", ", ", "world!"]


def _anthropic_rate_limit_error():
    import anthropic

    return anthropic.RateLimitError("rate limited", response=_FAKE_RESPONSE, body=None)


def _anthropic_timeout_error():
    import anthropic

    return anthropic.APITimeoutError(request=_FAKE_REQUEST)


def _anthropic_connection_error():
    import anthropic

    return anthropic.APIConnectionError(request=_FAKE_REQUEST)


def _anthropic_status_error():
    import anthropic

    return anthropic.AuthenticationError(
        "bad key", response=httpx.Response(401, request=_FAKE_REQUEST), body=None
    )


@pytest.mark.parametrize(
    ("sdk_error_factory", "expected_type"),
    [
        (_anthropic_rate_limit_error, ProviderRateLimitError),
        (_anthropic_timeout_error, ProviderTimeoutError),
        (_anthropic_connection_error, ProviderNetworkError),
        (_anthropic_status_error, ProviderUnavailableError),
    ],
)
def test_anthropic_provider_maps_sdk_errors_to_typed_provider_errors(sdk_error_factory, expected_type):
    provider = _anthropic_provider()
    fake_client = MagicMock()
    fake_client.messages.create = AsyncMock(side_effect=sdk_error_factory())

    with patch("anthropic.AsyncAnthropic", return_value=fake_client):
        with pytest.raises(expected_type):
            asyncio.run(provider.generate("hello"))


# --- Placeholder providers ---


def test_ollama_provider_is_an_honest_placeholder():
    provider = OllamaProvider(model="llama3")
    assert provider.is_loaded is False
    with pytest.raises(NotImplementedError):
        asyncio.run(provider.generate("hello"))


def test_ollama_provider_stream_is_an_honest_placeholder():
    provider = OllamaProvider(model="llama3")

    async def _collect():
        return [chunk async for chunk in provider.generate_stream("hello")]

    with pytest.raises(NotImplementedError):
        asyncio.run(_collect())


def test_ollama_provider_model_name_and_health():
    provider = OllamaProvider(model="llama3")
    assert provider.model_name == "llama3"
    health = provider.health()
    assert health.is_healthy is False
    assert health.detail
