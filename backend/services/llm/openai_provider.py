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
    # generate()/generate_stream() below, so this module never actually
    # imports the openai SDK unless a real call is made (see this
    # class's own docstring on why). TYPE_CHECKING is always False at
    # runtime, so this branch never executes.
    from openai import AsyncOpenAI


class MissingAPIKeyError(ProviderUnavailableError):
    """Raised when generate() is called with no API key configured — a
    clear, actionable error instead of letting the OpenAI SDK's own
    (less obvious, deeply-nested) authentication error surface directly
    to whatever called this.

    Subclasses ProviderUnavailableError (not bare Exception) specifically
    so api/routes/chat.py's existing `except ProviderUnavailableError`
    handler catches this too, mapping it to 503 — a misconfigured
    provider IS a form of "provider unavailable" from the caller's point
    of view. This is what lets chat.py stay ignorant of both provider
    modules' exception types entirely, matching the containment rule
    this module's own docstring states for imports.
    """


def _map_sdk_error(error: Exception) -> Exception:
    """Translates an openai SDK exception into one of this project's own
    typed provider errors (services/llm/errors.py), so nothing outside
    this file ever needs to import/catch the openai SDK's own exception
    types — the same containment principle this module's docstring
    already states for imports. Order matters: openai.APITimeoutError
    is itself a SUBCLASS of openai.APIConnectionError (verified directly
    against the installed SDK), so the timeout check must come first, or
    every timeout would be misclassified as a generic network error.
    Anything not recognized here is returned UNCHANGED — callers still
    see the original exception (existing behavior, unaffected).
    """
    import openai

    if isinstance(error, openai.RateLimitError):
        return ProviderRateLimitError(str(error))
    if isinstance(error, openai.APITimeoutError):
        return ProviderTimeoutError(str(error))
    if isinstance(error, openai.APIConnectionError):
        return ProviderNetworkError(str(error))
    if isinstance(error, openai.APIStatusError):
        return ProviderUnavailableError(str(error))
    return error


class OpenAIProvider:
    """Wraps the OpenAI SDK — the ONLY file in this entire project
    allowed to import it (this phase's explicit rule: no OpenAI SDK
    calls anywhere else). Every provider-specific detail — client
    construction, request/response shapes, the SDK's own exception
    types — stays contained here; AIOrchestrator and everything above it
    only ever sees the LLMProvider protocol, never this class directly.

    Genuinely async, unlike LocalTransformersProvider's
    asyncio.to_thread workaround: openai.AsyncOpenAI performs real,
    non-blocking network I/O, so there's no CPU-bound work to offload to
    a thread — the async/await here is doing real work, not faking it.

    NOTE: no OPENAI_API_KEY exists anywhere in this project's environment
    — this class is built and structurally correct, but a real, live
    OpenAI call has not been executed. Verified instead via a mocked SDK
    client in tests (see tests/test_llm_providers.py), the same honest
    distinction this project has drawn before for anything blocked by an
    unavailable environment dependency (Docker Desktop, HuggingFace Hub
    downloads, etc.) — built and reasoned about carefully, not glossed
    over as "done."
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
        self._client: AsyncOpenAI | None = None

    @property
    def is_loaded(self) -> bool:
        # An API-based provider has no local weights to "load" — it's
        # always structurally ready to attempt a call the moment it's
        # constructed. Whether a call actually SUCCEEDS depends on a
        # valid API key, a separate concern from "is this object ready."
        return True

    @property
    def model_name(self) -> str:
        return self._model

    def health(self) -> ProviderHealth:
        # A local, cheap check — never a live call to OpenAI (see
        # ProviderHealth's own docstring). Whether the key is actually
        # VALID is only ever discovered by a real generate() call.
        if not self._api_key:
            return ProviderHealth(is_healthy=False, detail="No API key configured.")
        return ProviderHealth(is_healthy=True)

    async def generate(self, prompt: str) -> LLMResponse:
        if not self._api_key:
            raise MissingAPIKeyError(
                "No OpenAI API key configured (settings.llm_api_key) — "
                "set one before selecting llm_provider=openai."
            )

        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                api_key=self._api_key, timeout=self._timeout_seconds
            )

        start_time = time.perf_counter()
        try:
            response = await self._client.chat.completions.create(
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
                    "llm_provider": "openai",
                    "llm_model": self._model,
                    "llm_duration_ms": round(duration_seconds * 1000, 2),
                    "llm_success": False,
                },
            )
            raise _map_sdk_error(error) from error

        duration_seconds = time.perf_counter() - start_time
        usage = response.usage
        prompt_tokens = usage.prompt_tokens if usage else None
        completion_tokens = usage.completion_tokens if usage else None

        logger.info(
            "LLM request succeeded",
            extra={
                "llm_provider": "openai",
                "llm_model": self._model,
                "llm_duration_ms": round(duration_seconds * 1000, 2),
                "llm_success": True,
                "llm_prompt_tokens": prompt_tokens,
                "llm_completion_tokens": completion_tokens,
            },
        )
        return LLMResponse(
            text=response.choices[0].message.content or "",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    async def generate_stream(self, prompt: str) -> AsyncIterator[str]:
        """Real, incremental token streaming — stream=True on the same
        SDK call generate() makes, yielding each delta as OpenAI sends
        it rather than waiting for the full response. Genuinely async,
        same reasoning as generate(): no CPU-bound work to offload, the
        network I/O itself is what async/await is doing here.
        """
        if not self._api_key:
            raise MissingAPIKeyError(
                "No OpenAI API key configured (settings.llm_api_key) — "
                "set one before selecting llm_provider=openai."
            )

        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                api_key=self._api_key, timeout=self._timeout_seconds
            )

        start_time = time.perf_counter()
        # Three possible outcomes, distinguished for logging: "success"
        # (the loop below finishes naturally), "failed" (an exception
        # propagates), or "cancelled" (this generator is closed early —
        # e.g. the client disconnected — via GeneratorExit, which skips
        # both the natural-completion line AND the `except Exception`
        # block below, since GeneratorExit is a BaseException, not an
        # Exception). finally always runs, so the outcome is always
        # logged regardless of which of the three actually happened.
        status_label = "cancelled"
        try:
            stream = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self._temperature,
                top_p=self._top_p,
                max_tokens=self._max_output_tokens,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
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
                    "llm_provider": "openai",
                    "llm_model": self._model,
                    "llm_duration_ms": round(duration_seconds * 1000, 2),
                    "llm_success": status_label == "success",
                },
            )
