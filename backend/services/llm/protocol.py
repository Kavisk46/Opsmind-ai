from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol


@dataclass
class ProviderHealth:
    """health()'s return shape — richer than a bare bool so a caller (a
    future aggregate /health-style endpoint, or just a log line) can say
    WHY a provider isn't healthy, not just that it isn't. is_healthy is
    a cheap, LOCAL check (is a key configured, is this a real
    implementation) — never a live network call to the provider itself;
    that would make every health check as slow/expensive as a real
    generate() call, defeating the point of a lightweight readiness
    signal.
    """

    is_healthy: bool
    detail: str | None = None


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

    # model_name/health() are ADDITIVE to this Protocol, not a
    # replacement for is_loaded — is_loaded answers "are real weights in
    # memory right now" (only local/HuggingFace-style providers ever
    # meaningfully differ on this); model_name/health() answer "which
    # model is this" and "is this provider usable at all," which every
    # provider (API-based or local) can answer identically.
    @property
    def model_name(self) -> str: ...

    def health(self) -> ProviderHealth: ...
