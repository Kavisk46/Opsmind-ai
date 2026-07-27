from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.config import settings

# Managed Postgres providers (Neon, Supabase, RDS, ...) hand out
# connection strings with libpq-style query params — sslmode,
# channel_binding — meant for psycopg2/libpq clients. The asyncpg
# dialect's create_connect_args() forwards EVERY url query param
# verbatim into asyncpg.connect(**opts) (see
# sqlalchemy/dialects/postgresql/asyncpg.py), and asyncpg.connect() has
# no sslmode or channel_binding parameter at all — only `ssl`, which
# happens to accept the exact same string values ('require',
# 'verify-full', ...) asyncpg's own docs confirm this. So: translate
# sslmode into the connect_args asyncpg actually understands, then drop
# both keys from the URL so they're never merged into opts a second time.
# channel_binding has no asyncpg equivalent — dropped outright, since
# asyncpg already only ever negotiates SCRAM-SHA-256 regardless.
# difference_update_query is SQLAlchemy's own URL API for this — no
# manual string/regex parsing of the connection string.
_url = make_url(settings.database_url)
_connect_args = {}
if "sslmode" in _url.query:
    _connect_args["ssl"] = _url.query["sslmode"]
_url = _url.difference_update_query(["sslmode", "channel_binding"])

# One engine per process. SQLAlchemy pools connections internally, so this
# is created once at import time and reused across every request rather
# than opening a fresh connection per request.
#
# pool_size / max_overflow: pool_size is the number of connections kept
# open and ready even when idle; max_overflow is how many *additional*
# connections SQLAlchemy is allowed to open temporarily under a burst of
# concurrent requests, beyond pool_size, before a request has to wait for
# one to free up. Values below are SQLAlchemy's own defaults, made
# explicit and configurable rather than left implicit.
#
# pool_pre_ping: issues a cheap "is this connection still alive" check
# before handing a pooled connection to a request. Without it, a
# connection that Postgres (or a container restart) silently closed while
# sitting idle in the pool would surface as a confusing mid-request error
# on whatever query happened to draw it next — exactly the kind of
# transient failure a Docker deployment (Postgres and the backend as
# independently restartable containers) needs to tolerate.
engine = create_async_engine(
    _url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    """FastAPI dependency that yields a DB session scoped to one request.

    Routes ask for a session via `Depends(get_db)` instead of importing a
    module-level session directly. That indirection is what lets FastAPI
    guarantee the session is closed after the request finishes — even if
    the handler raises — and lets tests swap in a different session/database
    later without changing a single route's code.

    Also owns the transaction boundary for the whole request: commits if
    everything below completed without raising, rolls back otherwise. This
    means repositories/services never call commit() themselves — they
    can't forget to, because it isn't their job. (Read-only routes like
    /health/ready are unaffected: committing a transaction that only ever
    ran a SELECT is a harmless no-op.)
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
