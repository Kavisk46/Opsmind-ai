import asyncio
import time
from typing import AsyncIterator

from core.logging import logger
from services.llm.protocol import LLMResponse


class LocalTransformersProvider:
    """A local, instruction-tuned HuggingFace model, loaded lazily — the
    same trade-off as SentenceTransformerEmbeddingModel: constructing this
    object is cheap (it just remembers the model name); the real weights
    (a genuine download the first time this model name is used on a
    machine, and a real, CPU-bound load into memory) only happen on the
    first call to generate(). This keeps app startup fast and keeps the
    test suite network-free — tests use a fake provider instead (see
    tests/conftest.py), never this class.

    The default provider for this project (see core/config.py's
    llm_provider) — free, no API key, no external network dependency
    once the model is downloaded once. Generation on CPU is measurably
    slower than embedding a chunk; a real, accepted trade-off of choosing
    a free, local, no-API-key model over a hosted one.
    """

    def __init__(self, model_name: str, max_new_tokens: int = 256):
        self._model_name = model_name
        self._max_new_tokens = max_new_tokens
        self._pipeline = None

    @property
    def is_loaded(self) -> bool:
        return self._pipeline is not None

    async def generate(self, prompt: str) -> LLMResponse:
        start_time = time.perf_counter()
        try:
            # transformers' pipeline() call is synchronous, CPU-bound
            # work — running it directly inside an async function would
            # block the entire event loop for the whole generation, the
            # exact class of bug already caught once this project
            # (the background-jobs phase's nested-event-loop test bug).
            # asyncio.to_thread offloads it to a worker thread, letting
            # other requests keep being served concurrently while this
            # one generates.
            text = await asyncio.to_thread(self._generate_sync, prompt)
        except Exception:
            duration_seconds = time.perf_counter() - start_time
            logger.error(
                "LLM request failed",
                extra={
                    "llm_provider": "local",
                    "llm_model": self._model_name,
                    "llm_duration_ms": round(duration_seconds * 1000, 2),
                    "llm_success": False,
                },
            )
            raise

        duration_seconds = time.perf_counter() - start_time
        logger.info(
            "LLM request succeeded",
            extra={
                "llm_provider": "local",
                "llm_model": self._model_name,
                "llm_duration_ms": round(duration_seconds * 1000, 2),
                "llm_success": True,
                # No token counts: the transformers pipeline doesn't
                # surface billed-token accounting the way a hosted API
                # does — None here is honest ("not available"), not a
                # claim that zero tokens were used.
            },
        )
        return LLMResponse(text=text)

    async def generate_stream(self, prompt: str) -> AsyncIterator[str]:
        """Pseudo-streaming: yields the ENTIRE generated response as a
        single chunk, rather than true token-by-token streaming.

        Real incremental streaming for a local transformers pipeline is
        achievable (transformers.TextIteratorStreamer, run alongside
        generation in a background thread, consumed as tokens arrive)
        but adds real thread-bridging complexity this project's scope
        doesn't justify — Step 3 explicitly asks for real streaming from
        the OpenAI provider specifically. This fallback exists so
        POST /chat/stream genuinely works end-to-end for this project's
        DEFAULT provider too, instead of being broken (a 501 or
        NotImplementedError) for the common case. Logging happens inside
        the delegated generate() call — no need to duplicate it here.
        """
        response = await self.generate(prompt)
        yield response.text

    def _generate_sync(self, prompt: str) -> str:
        if self._pipeline is None:
            from transformers import pipeline

            self._pipeline = pipeline("text-generation", model=self._model_name)

        messages = [{"role": "user", "content": prompt}]
        result = self._pipeline(
            messages, max_new_tokens=self._max_new_tokens, do_sample=False
        )
        # A chat-style pipeline's generated_text is the FULL conversation
        # (the input messages plus the model's reply appended) — the
        # actual answer is the last turn, not the whole list.
        return result[0]["generated_text"][-1]["content"]
