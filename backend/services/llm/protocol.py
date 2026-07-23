from dataclasses import dataclass
from typing import AsyncIterator, Protocol


@dataclass
class LLMResponse:
    """Structured output, not a bare string — this is what Step 7's
    "log token usage if available" is actually asking for: without a
    structured return value, a provider would have no way to hand token
    counts back to whatever calls generate() at all. prompt_tokens/
    completion_tokens are None for providers that genuinely can't report
    them (the local provider has no concept of "tokens billed" the way a
    hosted API does) — None, not 0, since 0 would falsely claim "zero
    tokens were used."
    """

    text: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class LLMProvider(Protocol):
    """The contract every LLM backend must satisfy — this is the whole
    point of this package existing. AIOrchestrator, ChatService, and
    everything else in this codebase depend on THIS, never on a concrete
    provider class. Swapping local/OpenAI/Anthropic/Ollama is a
    configuration change (services/llm/factory.py), never a change to
    any file that calls generate().

    This is the Dependency Inversion Principle applied directly: high-
    level code (the orchestrator) doesn't depend on low-level details
    (the OpenAI SDK, the transformers library) — both depend on this
    shared abstraction instead.
    """

    async def generate(self, prompt: str) -> LLMResponse: ...

    # A plain `def`, not `async def` — calling generate_stream(prompt)
    # returns an async generator immediately (no work happens yet); the
    # caller drives it with `async for chunk in llm.generate_stream(...)`.
    # This mirrors how Python's own async generator functions are called:
    # `await` applies to each step of iteration, never to the call itself.
    def generate_stream(self, prompt: str) -> AsyncIterator[str]: ...

    @property
    def is_loaded(self) -> bool: ...
