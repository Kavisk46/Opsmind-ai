# Roadmap

## Done

**Backend & data**
- [x] FastAPI backend with layered architecture (routes → services → repositories)
- [x] PostgreSQL schema with Alembic migrations, real foreign-key constraints and cascades
- [x] JWT authentication, bcrypt hashing, role-based access control

**AI pipeline**
- [x] Document ingestion: extraction → chunking → embedding → vector indexing (background task, pollable status)
- [x] RAG chat with citations, token-budgeted conversation memory
- [x] Multi-provider LLM support (local / OpenAI / Anthropic / Ollama) behind one `Protocol`
- [x] AI observability — token counts, estimated cost, retrieval quality, generation metadata
- [x] Golden regression dataset for retrieval quality

**Testing & quality**
- [x] 228 tests across unit / repository-integration / API / AI-pipeline layers
- [x] Ruff + mypy, both run for the first time this project and brought to fully clean
- [x] Load/stress/spike testing (Locust) — found and fixed a real event-loop-blocking bug

**Infrastructure**
- [x] Multi-stage Docker builds (backend + frontend), Docker Compose orchestration
- [x] GitHub Actions CI: lint → type-check → dependency scan → test+coverage → Docker build
- [x] Structured logging, Prometheus metrics, health/readiness checks
- [x] Security hardening: CORS, security headers, rate limiting, upload validation, dependency scanning

**Frontend**
- [x] Complete Next.js application — dashboard, AI chat UI, document library, analytics, settings, auth flows, full accessibility and responsive-design pass (currently running against mock data — see `frontend/README` equivalent section in the root README)

## Next (highest-impact first)

1. **Wire the frontend to the real backend.** The single highest-leverage remaining task — the frontend's typed `ApiClient` and mock-service boundary (`src/lib/mock-data/`) were built specifically for this swap; no UI restructuring should be required.
2. **Upgrade `pyjwt`, `python-multipart`, `starlette`** to their fixed versions (real CVEs found by `pip-audit`, fix versions available, deferred pending a dedicated upgrade-and-retest pass — see [`security.md`](security.md)).
3. **Introduce `Protocol` types for `VectorStore` and `DocumentRepository`**, matching the pattern already used for `EmbeddingModel`/`Storage`/`LLMProvider` — closes the one structural typing inconsistency documented in [`testing.md`](testing.md#a-known-typing-gap).
4. **Real content-type sniffing for uploads** (magic bytes, not just the declared header) — meaningful once uploads accept files from a less-trusted source than "an authenticated user of this specific app."

## Later (real, but lower-priority)

- Redis-backed rate limiting and conversation-history caching (Redis is already provisioned in `docker-compose.yml`, unused by application code — intentionally, see `deployment.md`)
- Refresh tokens / shorter-lived access tokens, if session-length requirements ever demand it
- An LLM-based router (replacing the current keyword-based one) if retrieval-vs-metadata routing ever needs to handle genuinely ambiguous questions
- A real hallucination-detection pass on top of the existing `context_provided`/`citation_count` proxy signal
- Backend-facing screenshots (Swagger UI, a real request/response, Prometheus output) for the README

## Explicitly Not Planned (and why)

- **A distributed rate limiter today** — the in-memory version is correct at this project's actual current scale (one process); building for a multi-replica deployment that doesn't exist yet would be premature.
- **A full Content-Security-Policy header set** — this is a JSON API with no server-rendered HTML; the smaller, targeted header set already added covers this API's real risk surface.
- **PEP 695 generic syntax / `StrEnum` migration** — both flagged as real, legitimate modernizations by Ruff, both deliberately left alone (`ruff.toml` documents why): they touch core, pervasively-used abstractions with subtly different runtime semantics, and deserve a dedicated, deliberate change — not a side effect of configuring a linter.
