from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central, typed source of truth for all environment-driven config.

    Every value has a safe local-dev default so the app runs with zero setup;
    a real deployment overrides them via actual environment variables (see
    .env.example), never by editing this file.
    """

    app_name: str = "OpsMind Backend"
    # A single source of truth for the app's version — main.py's FastAPI(version=...)
    # and every route that reports version (GET /, GET /health) read this
    # same value, so bumping a release means editing exactly one line.
    app_version: str = "0.1.0"
    app_description: str = "AI Operational Intelligence Platform"
    environment: str = "development"

    # Defaults to the docker-compose "db" service credentials — matches
    # docker-compose.yml exactly so `docker compose up` works with zero
    # extra config. A real deployment overrides this via a real env var,
    # never by editing this default.
    database_url: str = "postgresql+asyncpg://opsmind:opsmind@localhost:5432/opsmind"

    # Connection pool sizing (see core/database.py's create_async_engine call).
    # Defaults below match SQLAlchemy's own built-in defaults exactly — making
    # them explicit settings changes nothing about today's behavior, but
    # turns "how many connections can this instance open" from an implicit,
    # hidden default into something a real deployment can tune per-environment
    # (e.g. lower per-instance limits once running many replicas behind a
    # fixed Postgres max_connections ceiling) without editing code.
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # JWT signing. The dev default below is fine for local work but MUST be
    # overridden with a real secret in any real deployment — anyone who
    # knows this value can forge valid tokens for any user.
    secret_key: str = "dev-only-insecure-secret-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Where uploaded document bytes are written (see core/storage.py's
    # LocalStorage). Relative to the backend process's working directory
    # by default; override to an absolute path in any real deployment.
    storage_dir: str = "storage/documents"
    max_upload_size_bytes: int = 20 * 1024 * 1024  # 20 MB

    # Local HuggingFace model, loaded once at process startup (see
    # main.py's lifespan) — no external API call, no API key. ~80MB,
    # CPU-friendly, the standard default for semantic search over
    # short-to-medium passages (this project's chunks are well within
    # its comfortable range).
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Where ChromaDB's embedded/persistent client writes its index —
    # analogous to storage_dir, but for vectors instead of file bytes.
    # No server process, no Docker service: like SQLite, it's a real
    # database, just embedded in this process rather than run separately.
    chroma_persist_dir: str = "storage/chroma"

    # Chunking: how the extracted text of a document is split before
    # embedding. Overlap exists so a sentence/idea split across a chunk
    # boundary still appears whole in at least one neighboring chunk.
    chunk_size_chars: int = 1000
    chunk_overlap_chars: int = 200

    # RAG: how many chunks to retrieve per question.
    retrieval_top_k: int = 5

    # Which LLM backend answers questions, and how. "local" (the default)
    # stays the free, no-API-key, no-external-dependency choice this
    # project has deliberately used throughout — switching to "openai" or
    # "anthropic" is a config change, not a code change, but requires a
    # real API key this project doesn't ship with. A Literal, not a plain
    # str, for the same reason DocumentStatus/UserRole are enums, not
    # free text: an invalid provider name fails fast and loudly at
    # startup (Pydantic validation), not silently at the first chat
    # request.
    llm_provider: Literal["local", "openai", "anthropic", "ollama"] = "local"
    # Model name is provider-specific in meaning (a HuggingFace repo ID
    # for "local", an OpenAI model name for "openai", etc.) but shared as
    # one setting — only one provider is ever active at a time, so there's
    # no need for four separate model-name settings.
    llm_model_name: str = "Qwen/Qwen2.5-0.5B-Instruct"
    # None by default — the local provider needs no key at all; only
    # openai/anthropic read this, and each raises a clear, explicit error
    # at call time (not a cryptic SDK error) if it's missing.
    llm_api_key: str | None = None
    # 0.0 (deterministic/greedy) matches the local provider's existing
    # do_sample=False choice — reproducible answers were already the
    # deliberate default; this makes that choice an explicit, visible
    # setting instead of a hardcoded implementation detail.
    llm_temperature: float = 0.0
    llm_max_output_tokens: int = 256
    # Only meaningful for network-based providers (openai/anthropic) —
    # the local provider runs in-process with no request to time out.
    # Still a shared setting rather than provider-specific, for the same
    # "only one provider active at once" reason as llm_model_name.
    llm_request_timeout_seconds: float = 30.0

    # How many prior messages (user + assistant combined) PromptBuilder
    # includes as conversation history — see services/prompt_builder.py.
    # Bounded rather than unlimited: an ever-growing conversation would
    # otherwise mean an ever-growing prompt, eventually exceeding the
    # model's context window and increasing latency/cost on every turn
    # regardless of whether the early history is still relevant.
    max_history_messages: int = 10

    # A TOKEN budget for conversation history — ConversationService's
    # primary truncation mechanism (see services/conversation_service.py),
    # more accurate than a flat message count since a handful of long
    # messages can consume far more of a model's context window than a
    # dozen short ones. max_history_messages above remains a secondary,
    # defensive cap in PromptBuilder in case token estimates are ever off.
    # ~2000 tokens is a deliberately modest default, leaving most of a
    # small model's context window for the retrieved document context and
    # the answer itself.
    max_history_tokens: int = 2000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Instantiated once at import time and reused everywhere — see the "why one
# Settings instance" note in the Phase 0 write-up for why this beats calling
# os.environ.get() ad hoc across the codebase.
settings = Settings()


def get_settings() -> Settings:
    """A FastAPI dependency wrapping the settings singleton above. Routes
    that need config should declare `Depends(get_settings)` rather than
    importing `settings` directly — identical behavior in production (this
    just returns the same singleton), but it means a test can override
    *what this returns* via app.dependency_overrides without touching the
    route or monkeypatching the module-level singleton.

    main.py itself still imports `settings` directly — that's fine and
    deliberate. DI matters for values read *inside request-handling code*
    that you might want to swap per-test; app construction at startup
    happens once, outside any request, so there's nothing to inject into.
    """
    return settings
