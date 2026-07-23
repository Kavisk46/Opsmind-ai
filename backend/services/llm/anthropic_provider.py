from typing import AsyncIterator

from services.llm.protocol import LLMResponse


class AnthropicProvider:
    """A placeholder, not a working provider — but the SAME LLMProvider
    shape as every real one. That's the point: selecting
    llm_provider=anthropic fails loudly and immediately with a clear
    NotImplementedError, rather than the factory needing a special case
    for "this one isn't real yet," and nothing that calls an LLMProvider
    needs to know or care that this one is a stub versus a working
    implementation.

    Wiring in the real Anthropic SDK is a self-contained follow-up —
    mirror OpenAIProvider's structure (lazy client construction, a
    try/except around the real call with the same logging shape, mapping
    Anthropic's response/usage fields into LLMResponse) — never a
    redesign of anything else in this package.
    """

    def __init__(self, *, api_key: str | None, model: str):
        self._api_key = api_key
        self._model = model

    @property
    def is_loaded(self) -> bool:
        return False

    async def generate(self, prompt: str) -> LLMResponse:
        raise NotImplementedError(
            "AnthropicProvider is a placeholder and not yet implemented. "
            "Follow OpenAIProvider's structure to wire in the real Anthropic SDK."
        )

    async def generate_stream(self, prompt: str) -> AsyncIterator[str]:
        raise NotImplementedError(
            "AnthropicProvider is a placeholder and not yet implemented. "
            "Follow OpenAIProvider's generate_stream() to wire in real streaming."
        )
        # Unreachable — but the presence of a `yield` anywhere in this
        # function body is what makes Python treat it as an async
        # generator FUNCTION at all. Without it, calling generate_stream()
        # would return a plain coroutine, not something `async for` can
        # iterate, and the NotImplementedError would need to be awaited
        # directly instead of raised on first iteration like every real
        # provider's generate_stream() does.
        yield
