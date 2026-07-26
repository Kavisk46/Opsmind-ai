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
- [x] Complete Next.js application — dashboard, AI chat UI, document library, analytics, settings, auth flows, full accessibility and responsive-design pass
- [x] Authentication wired to the real backend — JWT login/signup, session restoration on reload, automatic logout on token expiry (guest/portfolio-demo mode intentionally kept, entirely separate from real accounts)
- [x] AI chat wired to the real backend — real SSE streaming, real per-conversation history (list/select/delete against `GET/POST/DELETE /conversations`), real citations, real cancellation/retry
- [x] Documents wired to the real backend — real multipart upload with live progress, retry, validation, listing, delete, client-side pagination and search over the real list
- [x] Dashboard partially wired — document count, AI query/latency stats (with a real "Admin access required" fallback for non-admin viewers), and a Recent Activity feed built from real uploads + real conversations (no dedicated activity-log endpoint exists, so this is assembled from two real, timestamped sources instead)
- [x] Real request caching — TanStack Query was already installed and configured but unused; documents/conversations/AI-metrics/activity reads now go through it, sharing query keys across components so e.g. the dashboard and the upload modal don't issue duplicate requests for the same data

## Next (highest-impact first)

1. **Give a real user a path to the `admin` role.** Signup always assigns `member`; there is no invite/promote flow anywhere. This means `GET /internal/ai-metrics` (and the Analytics KPIs that depend on it) is currently unreachable through any real user-facing flow — the single highest-leverage remaining gap.
2. **Upgrade `pyjwt`, `python-multipart`, `starlette`** to their fixed versions (real CVEs found by `pip-audit`, fix versions available, deferred pending a dedicated upgrade-and-retest pass — see [`security.md`](security.md)).
3. **Add frontend CI.** `.github/workflows/ci.yml` only builds/tests the backend; there is no automated lint/typecheck/build step for the frontend, and no frontend test suite exists at all yet.
4. **Introduce `Protocol` types for `VectorStore` and `DocumentRepository`**, matching the pattern already used for `EmbeddingModel`/`Storage`/`LLMProvider` — closes the one structural typing inconsistency documented in [`testing.md`](testing.md#a-known-typing-gap).
5. **Real content-type sniffing for uploads** (magic bytes, not just the declared header) — meaningful once uploads accept files from a less-trusted source than "an authenticated user of this specific app."

## Later (real, but lower-priority)

- Redis-backed rate limiting and an AI-metrics summary cache (Redis is already provisioned in `docker-compose.yml`, unused by application code — intentionally, see `deployment.md`)
- Refresh tokens / shorter-lived access tokens — today's JWT hard-expires after 30 minutes with no renewal path
- Move the frontend's session JWT out of a plain client-set cookie (currently as XSS-exposed as `localStorage` would be) and into a backend-set `httpOnly` cookie on login — a backend change, not just a frontend one
- Real document rename/download/preview — none of the three has a backend endpoint today (no `PATCH`/`PUT` on `/documents/{id}`, no file-serving route, no exposed extracted-content endpoint); each needs a real backend design decision, not a frontend-only fix
- Wire the remaining mock Dashboard/Analytics surface (team/AI-status/server-status cards, trend charts, query log) to real data once there's a real backend source for any of it — today none of it has one
- An LLM-based router (replacing the current keyword-based one) if retrieval-vs-metadata routing ever needs to handle genuinely ambiguous questions
- A real hallucination-detection pass on top of the existing `context_provided`/`citation_count` proxy signal
- Backend-facing screenshots (Swagger UI, a real request/response, Prometheus output) for the README

## Explicitly Not Planned (and why)

- **A distributed rate limiter today** — the in-memory version is correct at this project's actual current scale (one process); building for a multi-replica deployment that doesn't exist yet would be premature.
- **A full Content-Security-Policy header set** — this is a JSON API with no server-rendered HTML; the smaller, targeted header set already added covers this API's real risk surface.
- **PEP 695 generic syntax / `StrEnum` migration** — both flagged as real, legitimate modernizations by Ruff, both deliberately left alone (`ruff.toml` documents why): they touch core, pervasively-used abstractions with subtly different runtime semantics, and deserve a dedicated, deliberate change — not a side effect of configuring a linter.
