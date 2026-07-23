from core.config import Settings
from services.llm.anthropic_provider import AnthropicProvider
from services.llm.local_provider import LocalTransformersProvider
from services.llm.ollama_provider import OllamaProvider
from services.llm.openai_provider import OpenAIProvider
from services.llm.protocol import LLMProvider


class UnknownLLMProviderError(Exception):
    """Not reachable through normal configuration — Settings.llm_provider
    is a Literal, so Pydantic already rejects any other value at startup,
    before this function is ever called. Kept as a defensive fallback for
    the same reason ToolRegistry.get() raises UnknownToolError: fail
    loudly if an assumption this code depends on is ever wrong, rather
    than silently returning None.
    """


def get_llm_provider(settings: Settings) -> LLMProvider:
    """The ONLY place in this codebase that decides which concrete
    provider class to instantiate — based on configuration
    (settings.llm_provider), not a code change. This is the Factory
    pattern: a caller asks for "the configured LLM provider" and
    receives something satisfying LLMProvider, never needing to know or
    care which concrete class it actually got.
    """
    if settings.llm_provider == "local":
        return LocalTransformersProvider(
            model_name=settings.llm_model_name,
            max_new_tokens=settings.llm_max_output_tokens,
        )

    if settings.llm_provider == "openai":
        return OpenAIProvider(
            api_key=settings.llm_api_key,
            model=settings.llm_model_name,
            temperature=settings.llm_temperature,
            max_output_tokens=settings.llm_max_output_tokens,
            timeout_seconds=settings.llm_request_timeout_seconds,
        )

    if settings.llm_provider == "anthropic":
        return AnthropicProvider(
            api_key=settings.llm_api_key, model=settings.llm_model_name
        )

    if settings.llm_provider == "ollama":
        return OllamaProvider(model=settings.llm_model_name)

    raise UnknownLLMProviderError(settings.llm_provider)
