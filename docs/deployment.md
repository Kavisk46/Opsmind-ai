# Deployment

## Docker

Both `backend/Dockerfile` and `frontend/Dockerfile` are **multi-stage** builds — a `builder` stage installs dependencies (Python: into an isolated venv; Node: `npm ci`), a fresh final stage copies over only the *result*, never the build tools, package caches, or source-only artifacts. Both run as a **non-root user** and declare a real `HEALTHCHECK` against an actual endpoint (`GET /health` for the backend; the root route for the frontend) — not a fake sleep.

```bash
cd backend && docker build -t opsmind-backend .
cd frontend && docker build -t opsmind-frontend .
```

### Why the frontend needs `output: "standalone"`

Set in `frontend/next.config.ts`. Next.js traces exactly which files a production build actually needs — including a curated subset of `node_modules` — into `.next/standalone`, plus a minimal `server.js`. The final Docker stage copies only that output, never running `npm install` in the production image at all.

## Docker Compose

```bash
cp .env.example .env      # review defaults, especially SECRET_KEY
docker compose build
docker compose up
```

Four services: `db` (Postgres), `redis` (provisioned ahead of the caching feature that will consume it — documented as such directly in `docker-compose.yml`, not silently added as if load-bearing), `backend`, `frontend`. All share one explicit, named bridge network (`opsmind-network`) — what makes `backend` able to resolve `db` by service name via Compose's internal DNS.

**Persistence**: named volumes for `postgres_data`, `backend_storage` (uploaded files), and `backend_chroma` (vector index) — without these, every `docker compose down` would silently discard every uploaded document and embedding, since a container's own writable layer dies with the container.

**Two different `DATABASE_URL`s, on purpose**: `backend/.env.example` uses `localhost` (correct for running the backend directly on the host); `docker-compose.yml` computes its own value using the Docker-internal service name `db` (correct inside the network) — deliberately *not* trusted from `.env`, specifically to prevent the two from ever being confused for each other.

```bash
docker compose build     # build every service's image
docker compose up        # start everything, wait for db's healthcheck first
docker compose down      # stop + remove containers (volumes survive by default)
docker compose logs -f backend   # follow one service's logs
```

## CI/CD

`.github/workflows/ci.yml` runs on every push and pull request to `main`:

```
checkout → setup Python (cached deps) → Ruff → mypy → pip-audit
  → pytest with coverage → upload coverage artifact → docker build
```

**Fail-fast ordering**: the fastest checks run first — a lint failure means mypy, the test suite, and the (slowest) Docker build never even start.

**Dependency caching**: `actions/setup-python`'s built-in pip cache, keyed off *both* `requirements.txt` and `requirements-dev.txt` (not just the latter) — `requirements-dev.txt` only *references* the other file via `-r requirements.txt`, and the cache key is computed from the literal file(s) listed, not anything they reference. Listing only one risks silently serving a stale cache after a production-dependency change.

**Dependency scanning is informational, not blocking** (`continue-on-error: true`) — verified directly that it currently finds 28 real CVEs, most with an available fix, one (`chromadb`) without one yet. A blocking scan on a finding with no fix would freeze every future merge — worse than the vulnerability itself.

**No secrets required**: the whole pipeline runs against SQLite (never a real Postgres) and `FakeLLM` (never a real API call) — a direct payoff of the same test-isolation architecture described in [`testing.md`](testing.md).

## What a Real Production Deployment Would Still Need

Named honestly, not glossed over: a managed Postgres instance (not the `db` container — a single-container database has no real backup/failover story); secrets from a real secret manager, not a `.env` file; `SECRET_KEY` rotation strategy; the Redis-backed rate limiter/conversation-cache upgrade already flagged throughout this project's own code comments (the current in-memory `RateLimiter` is single-process, correct at today's scale, not at real multi-replica scale); TLS termination (a reverse proxy or platform-level concern, not something this repo's Dockerfiles handle); and the CVEs listed in [`security.md`](security.md) actually upgraded, not just tracked.
