import time
from typing import AsyncIterator

from core.logging import logger
from services.llm.protocol import LLMResponse


class MissingAPIKeyError(Exception):
    """Raised when generate() is called with no API key configured — a
    clear, actionable error instead of letting the OpenAI SDK's own
    (less obvious, deeply-nested) authentication error surface directly
    to whatever called this.
    """


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
        max_output_tokens: int,
        timeout_seconds: float,
    ):
        self._api_key = api_key
        self._model = model
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens
        self._timeout_seconds = timeout_seconds
        self._client = None

    @property
    def is_loaded(self) -> bool:
        # An API-based provider has no local weights to "load" — it's
        # always structurally ready to attempt a call the moment it's
        # constructed. Whether a call actually SUCCEEDS depends on a
        # valid API key, a separate concern from "is this object ready."
        return True

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
                max_tokens=self._max_output_tokens,
            )
        except Exception:
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
            raise

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
                max_tokens=self._max_output_tokens,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
            status_label = "success"
        except Exception:
            status_label = "failed"
            raise
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
