import time
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from core.logging import logger
from services.llm.errors import (
    ProviderNetworkError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from services.llm.protocol import LLMResponse, ProviderHealth

if TYPE_CHECKING:
    # Only for type-checking — the real import stays lazy, inside
    # generate()/generate_stream() below, mirroring OpenAIProvider's own
    # reasoning exactly: this module shouldn't pay the anthropic SDK's
    # import cost unless a real call is actually made.
    from anthropic import AsyncAnthropic


class MissingAPIKeyError(ProviderUnavailableError):
    """Raised when generate() is called with no API key configured — same
    reasoning as openai_provider.py's identically-named exception,
    including subclassing ProviderUnavailableError so it's caught by
    api/routes/chat.py's existing 503 handler for free.
    """


def _map_sdk_error(error: Exception) -> Exception:
    """Translates an anthropic SDK exception into one of this project's
    own typed provider errors (services/llm/errors.py) — same reasoning,
    and the same subclass-ordering caveat, as openai_provider.py's
    _map_sdk_error: anthropic.APITimeoutError is itself a subclass of
    anthropic.APIConnectionError (verified directly against the
    installed SDK, which mirrors the openai SDK's exception hierarchy),
    so the timeout check must come first.
    """
    import anthropic

    if isinstance(error, anthropic.RateLimitError):
        return ProviderRateLimitError(str(error))
    if isinstance(error, anthropic.APITimeoutError):
        return ProviderTimeoutError(str(error))
    if isinstance(error, anthropic.APIConnectionError):
        return ProviderNetworkError(str(error))
    if isinstance(error, anthropic.APIStatusError):
        return ProviderUnavailableError(str(error))
    return error


class AnthropicProvider:
    """Wraps the Anthropic SDK — the ONLY file in this project allowed to
    import it, same containment rule OpenAIProvider's docstring states
    for the openai SDK. Structurally identical to OpenAIProvider: lazy
    client construction, the same try/except/logging shape, the same
    typed-error mapping — the two providers differ only in which SDK
    they call and how that SDK shapes its request/response.

    NOTE: no ANTHROPIC_API_KEY exists anywhere in this project's
    environment — built and structurally correct, verified via a mocked
    SDK client in tests (see tests/test_llm_providers.py), never a real,
    live Anthropic call. Same honest distinction OpenAIProvider's own
    docstring already draws.
    """

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        temperature: float,
        top_p: float,
        max_output_tokens: int,
        timeout_seconds: float,
    ):
        self._api_key = api_key
        self._model = model
        self._temperature = temperature
        self._top_p = top_p
        self._max_output_tokens = max_output_tokens
        self._timeout_seconds = timeout_seconds
        self._client: AsyncAnthropic | None = None

    @property
    def is_loaded(self) -> bool:
        # Same reasoning as OpenAIProvider.is_loaded — an API-based
        # provider has no local weights to load.
        return True

    @property
    def model_name(self) -> str:
        return self._model

    def health(self) -> ProviderHealth:
        if not self._api_key:
            return ProviderHealth(is_healthy=False, detail="No API key configured.")
        return ProviderHealth(is_healthy=True)

    def _ensure_client(self) -> "AsyncAnthropic":
        if not self._api_key:
            raise MissingAPIKeyError(
                "No Anthropic API key configured (settings.llm_api_key) — "
                "set one before selecting llm_provider=anthropic."
            )
        if self._client is None:
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(
                api_key=self._api_key, timeout=self._timeout_seconds
            )
        return self._client

    async def generate(self, prompt: str) -> LLMResponse:
        client = self._ensure_client()

        start_time = time.perf_counter()
        try:
            response = await client.messages.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self._temperature,
                top_p=self._top_p,
                max_tokens=self._max_output_tokens,
            )
        except Exception as error:
            duration_seconds = time.perf_counter() - start_time
            logger.error(
                "LLM request failed",
                extra={
                    "llm_provider": "anthropic",
                    "llm_model": self._model,
                    "llm_duration_ms": round(duration_seconds * 1000, 2),
                    "llm_success": False,
                },
            )
            raise _map_sdk_error(error) from error

        duration_seconds = time.perf_counter() - start_time
        usage = response.usage
        prompt_tokens = usage.input_tokens if usage else None
        completion_tokens = usage.output_tokens if usage else None
        # Anthropic's response content is a LIST of content blocks (text,
        # tool-use, etc.) — this provider only ever sends plain-text
        # prompts with no tools configured, so exactly one text block is
        # expected; joining is a defensive no-op in that case, not
        # evidence multiple blocks are actually anticipated here.
        text = "".join(
            block.text for block in response.content if block.type == "text"
        )

        logger.info(
            "LLM request succeeded",
            extra={
                "llm_provider": "anthropic",
                "llm_model": self._model,
                "llm_duration_ms": round(duration_seconds * 1000, 2),
                "llm_success": True,
                "llm_prompt_tokens": prompt_tokens,
                "llm_completion_tokens": completion_tokens,
            },
        )
        return LLMResponse(
            text=text, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
        )

    async def generate_stream(self, prompt: str) -> AsyncIterator[str]:
        """Real, incremental token streaming — same shape as
        OpenAIProvider.generate_stream(). Anthropic's raw stream yields
        several distinct EVENT types (message_start/content_block_start/
        content_block_delta/...); only content_block_delta events with a
        text_delta carry actual answer text, which is exactly what this
        filters for.
        """
        client = self._ensure_client()

        start_time = time.perf_counter()
        status_label = "cancelled"
        try:
            stream = await client.messages.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self._temperature,
                top_p=self._top_p,
                max_tokens=self._max_output_tokens,
                stream=True,
            )
            async for event in stream:
                if event.type == "content_block_delta" and event.delta.type == "text_delta":
                    yield event.delta.text
            status_label = "success"
        except Exception as error:
            status_label = "failed"
            raise _map_sdk_error(error) from error
        finally:
            duration_seconds = time.perf_counter() - start_time
            log_fn = logger.error if status_label == "failed" else logger.info
            log_fn(
                "LLM stream %s",
                status_label,
                extra={
                    "llm_provider": "anthropic",
                    "llm_model": self._model,
                    "llm_duration_ms": round(duration_seconds * 1000, 2),
                    "llm_success": status_label == "success",
                },
            )
