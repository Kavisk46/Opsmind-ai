from typing import AsyncIterator

from services.llm.protocol import LLMResponse


class OllamaProvider:
    """A placeholder, not a working provider. Ollama specifically was
    already considered and set aside once already in this project (the
    RAG phase's LLM-backend decision), for the same reason every
    Docker-based service has been unreliable throughout this environment:
    it requires a separately running server process, not just a Python
    package — the same category of dependency as Postgres/ChromaDB-as-
    a-server, which this project has consistently avoided in favor of
    embedded/in-process alternatives wherever possible.

    This stub exists so the shape is ready: a real implementation just
    needs an HTTP client pointed at a running Ollama server's API
    (typically http://localhost:11434), following OpenAIProvider's
    structure for the logging/error-handling shape.
    """

    def __init__(self, *, model: str):
        self._model = model

    @property
    def is_loaded(self) -> bool:
        return False

    async def generate(self, prompt: str) -> LLMResponse:
        raise NotImplementedError(
            "OllamaProvider is a placeholder and not yet implemented. "
            "Requires a running Ollama server — see this class's docstring."
        )

    async def generate_stream(self, prompt: str) -> AsyncIterator[str]:
        raise NotImplementedError(
            "OllamaProvider is a placeholder and not yet implemented. "
            "Requires a running Ollama server — see this class's docstring."
        )
        # See AnthropicProvider.generate_stream()'s comment — the
        # unreachable yield is what makes this an async generator
        # function rather than a plain coroutine.
        yield
