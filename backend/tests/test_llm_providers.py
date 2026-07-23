import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from core.config import Settings
from services.llm.anthropic_provider import AnthropicProvider
from services.llm.factory import get_llm_provider
from services.llm.local_provider import LocalTransformersProvider
from services.llm.ollama_provider import OllamaProvider
from services.llm.openai_provider import MissingAPIKeyError, OpenAIProvider


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


def test_factory_returns_anthropic_stub_when_configured():
    settings = Settings(llm_provider="anthropic")
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


# --- OpenAI provider ---
# No OPENAI_API_KEY exists anywhere in this project's environment — these
# tests verify the provider's OWN logic (the missing-key guard, and
# correctly mapping a response into LLMResponse) using a mocked SDK
# client, never a real network call. This is precisely what dependency
# injection buys here: OpenAIProvider depends on `openai.AsyncOpenAI`
# only at the point of use, so a test can substitute a fake one without
# needing a real API key, real network access, or real billing.


def test_openai_provider_raises_without_api_key():
    provider = OpenAIProvider(
        api_key=None,
        model="gpt-4o-mini",
        temperature=0.0,
        max_output_tokens=100,
        timeout_seconds=30.0,
    )
    with pytest.raises(MissingAPIKeyError):
        asyncio.run(provider.generate("hello"))


def test_openai_provider_maps_response_into_llm_response():
    provider = OpenAIProvider(
        api_key="sk-test",
        model="gpt-4o-mini",
        temperature=0.0,
        max_output_tokens=100,
        timeout_seconds=30.0,
    )

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
    provider = OpenAIProvider(
        api_key=None,
        model="gpt-4o-mini",
        temperature=0.0,
        max_output_tokens=100,
        timeout_seconds=30.0,
    )

    async def _collect():
        return [chunk async for chunk in provider.generate_stream("hello")]

    with pytest.raises(MissingAPIKeyError):
        asyncio.run(_collect())


def test_openai_provider_streams_incremental_deltas():
    provider = OpenAIProvider(
        api_key="sk-test",
        model="gpt-4o-mini",
        temperature=0.0,
        max_output_tokens=100,
        timeout_seconds=30.0,
    )

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


# --- Placeholder providers ---


def test_anthropic_provider_is_an_honest_placeholder():
    provider = AnthropicProvider(api_key=None, model="claude-3-5-haiku")
    assert provider.is_loaded is False
    with pytest.raises(NotImplementedError):
        asyncio.run(provider.generate("hello"))


def test_anthropic_provider_stream_is_an_honest_placeholder():
    provider = AnthropicProvider(api_key=None, model="claude-3-5-haiku")

    async def _collect():
        return [chunk async for chunk in provider.generate_stream("hello")]

    with pytest.raises(NotImplementedError):
        asyncio.run(_collect())


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
