from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central, typed source of truth for all environment-driven config.

    Every value has a safe local-dev default so the app runs with zero setup;
    a real deployment overrides them via actual environment variables (see
    .env.example), never by editing this file.
    """

    app_name: str = "OpsMind AI Backend"
    environment: str = "development"

    # Defaults to the docker-compose "db" service credentials — matches
    # docker-compose.yml exactly so `docker compose up` works with zero
    # extra config. A real deployment overrides this via a real env var,
    # never by editing this default.
    database_url: str = "postgresql+asyncpg://opsmind:opsmind@localhost:5432/opsmind"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Instantiated once at import time and reused everywhere — see the "why one
# Settings instance" note in the Phase 0 write-up for why this beats calling
# os.environ.get() ad hoc across the codebase.
settings = Settings()
