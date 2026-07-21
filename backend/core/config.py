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
