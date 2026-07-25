# Backend Architecture

## Layering

```
api/routes/*.py     — HTTP only: parse the request, call a service, shape the response.
                       Never contains business logic or a raw SQL/ORM query.
services/*.py        — Business logic. Validates, orchestrates, raises domain
                       exceptions (never HTTPException — that translation is the
                       route's job).
repositories/*.py    — Persistence only. One class per table, generic CRUD from
                       BaseRepository, entity-specific queries added on top.
models/*.py          — SQLAlchemy table definitions. No behavior beyond
                       relationships and column defaults.
core/*.py            — Cross-cutting infrastructure: config, database engine,
                       security (JWT/bcrypt), logging, metrics, storage,
                       vector store, rate limiting.
```

Each layer only ever calls the layer directly below it. A route never touches a repository directly; a repository never raises an `HTTPException`. This isn't a style preference — it's what makes every layer independently testable (see [`testing.md`](testing.md)).

## Dependency Injection

Every service receives its collaborators through its constructor — never builds them internally, never imports a module-level singleton and calls it directly. `api/dependencies.py` is the **only** place production dependencies are wired together (via FastAPI's `Depends()`); `tests/conftest.py` is the only place test fakes are wired in. Application code never has an `if TESTING` branch anywhere — the swap happens entirely at the dependency-injection boundary.

Two DI patterns coexist deliberately:

- **Structural typing via `Protocol`** (`EmbeddingModel`, `Storage`, `LLMProvider`, `ConversationStore`/`MessageStore`, `AIMetricsRecorder`) — a fake only needs to match the *shape* used, no inheritance required. This is what lets `FakeLLM` (a plain class in `tests/conftest.py`) stand in for four different real provider implementations.
- **Concrete-class typing** (`VectorStore`, `DocumentRepository`) for classes that haven't been given a `Protocol` yet — duck-typing still works at runtime (Python doesn't enforce type hints), but this is a real, acknowledged inconsistency, not an oversight (see [`testing.md`](testing.md#a-known-typing-gap) for exactly where this was found and why it wasn't silently "fixed").

## Why a Service Layer, Not "Fat Routes"

A route function only ever does three things: resolve dependencies via `Depends()`, call exactly one service method, and translate a domain exception into an HTTP status code. This means the *entire* business rule set (ownership checks, token budgeting, anti-enumeration error shaping, cascading-delete semantics) is reachable and testable without an HTTP client — see how much of the test suite (unit-level service tests) never touches `TestClient` at all.

## Database Design

Five tables — `users`, `documents`, `conversations`, `messages`, `teams` — with real foreign-key constraints, not just application-level checks:

| Relationship | On delete | Why |
|---|---|---|
| `User → Document` | `CASCADE` | A deleted user's uploaded documents have no meaningful owner left |
| `User → Conversation → Message` | `CASCADE` (two levels) | Same reasoning, two tables deep |
| `Team → User` | `SET NULL` | Losing your team shouldn't delete *you* — just un-assign the relationship |
| `User.email` | `UNIQUE` | Enforced at the database level, independent of the application-level duplicate check `UserService` also performs — verified directly that the database itself rejects a duplicate even if that check were ever bypassed |

Schema evolves via Alembic migrations (`alembic/versions/`) — never hand-edited once applied to any real environment. Migration-chain integrity (exactly one head, no orphaned revisions) is verified by a dedicated, database-free test (`tests/test_alembic_migrations.py`).

## Structured Logging & Observability

Every log line is one JSON object (`core/logging.py`), correlated by `request_id` (and `user_id` once authenticated) via `contextvars` — not passed as an explicit parameter through every function call, but automatically available to any code running within that request's async context. AI-specific events (LLM calls, retrieval, generation) get their own structured fields (`llm_provider`, `estimated_cost_usd`, `retrieval_chunk_count`, ...) recorded through `AIMetricsService`, which also drives the Prometheus `/metrics` endpoint and the admin-only `/internal/ai-metrics` JSON summary.

## Error Handling

One consistent envelope (`schemas/errors.py`'s `ErrorResponse`) for every error path: a deliberately-raised `HTTPException`, a FastAPI validation error, and — the gap closed during the security-hardening phase — a genuinely unhandled exception. That third case required a real fix, not just registering a handler: this app's custom `@app.middleware("http")` (built on Starlette's `BaseHTTPMiddleware`) has a documented upstream interaction where a registered `@app.exception_handler(Exception)` doesn't reliably catch an exception raised inside a route using an async-generator dependency (i.e., almost every real route, via `Depends(get_db)`). The actual fix wraps `call_next()` directly inside the middleware — see `main.py`'s `add_process_time_and_log` for the full reasoning, verified by a dedicated test.

## Security Posture

See [`security.md`](security.md) for the full review. Summary: bcrypt password hashing, JWT with a startup check against the insecure default secret, role-based access control, anti-enumeration error responses, rate limiting on login and signup, CORS restricted to a real allowlist, file-upload content-type validation, and dependency vulnerability scanning in CI.
