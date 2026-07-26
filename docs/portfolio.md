# Portfolio Materials

## Demo Script (5 minutes)

**0:00–0:30 — Framing.** "OpsMind is a RAG platform I built to demonstrate production AI-systems engineering, not just calling an LLM API — the parts most tutorials skip: token budgeting, retrieval evaluation, cost tracking, a real test suite, CI, and a security review."

**0:30–1:30 — The core loop.** Show `POST /documents` (upload a real doc), poll `GET /documents/{id}/status` through `uploaded → processing → embedding → ready`, then `POST /chat` asking a question grounded in it — point at the citation in the response. "The answer isn't just plausible text — it's traceable back to a specific chunk of a specific document."

**1:30–2:30 — What's underneath.** Open `docs/architecture.md`'s diagrams. Walk through the layered architecture (routes → services → repositories) and explain the one dependency-injection idea that makes the whole test suite possible: every collaborator — the database, the vector store, the LLM — is swappable at one seam, never hardcoded.

**2:30–3:30 — The AI observability angle.** Hit `GET /internal/ai-metrics` as an admin — show token counts, estimated cost, retrieval confidence per request. "This is the difference between 'I called an LLM' and 'I built the layer that makes an LLM usable as a real product' — you can't operate what you can't measure."

**3:30–4:30 — Engineering rigor.** `pytest -q` — 228 tests, seconds, zero external dependencies. Show `.github/workflows/ci.yml` running lint → type-check → dependency scan → test → Docker build. Mention the golden regression dataset for retrieval quality specifically — "most RAG demos never prove retrieval doesn't silently regress; this one does."

**4:30–5:00 — Honest close.** "The backend and AI pipeline are real and fully tested. The frontend — auth, AI chat with real streaming and history, and documents — is now wired to this real backend too, through a typed API client with real request caching. What's left mock is scoped precisely, not hidden: most of the dashboard and analytics charts, since there's genuinely no backend data behind them yet."

## Resume Project Description

**One-line version:**
> OpsMind — Production-grade RAG platform (FastAPI, PostgreSQL, ChromaDB) with token-budgeted conversation memory, AI cost/retrieval observability, 228-test suite, Docker/CI/CD, and a full security-hardening pass.

**Bullet version (for a resume's project section):**
- Designed and built a layered FastAPI backend (routes/services/repositories) with dependency injection throughout, enabling a 228-test suite with zero external dependencies (no live database, vector store, or LLM API calls in CI)
- Implemented a full RAG pipeline — document ingestion, chunking, embedding, vector retrieval, prompt construction, multi-provider LLM generation — with token-budgeted conversation memory and per-request AI cost/latency/retrieval-quality tracking
- Built a golden regression dataset to catch retrieval-quality regressions, distinct from and complementary to unit/integration testing
- Set up GitHub Actions CI (lint, type-check, dependency vulnerability scanning, test+coverage, Docker build) and multi-stage Docker builds for both backend and frontend
- Conducted a security review that found and fixed a real Starlette/FastAPI middleware bug affecting exception handling on nearly every route, plus CORS, rate-limiting, and file-upload validation gaps

## Portfolio / Personal Site Description

> **OpsMind** is a Retrieval-Augmented Generation platform built to show what production AI-systems engineering actually looks like — not a weekend LLM wrapper. The backend is a real, independently-designed FastAPI service: layered architecture, dependency injection, a Postgres schema with real foreign-key constraints, and an AI pipeline instrumented for cost and retrieval-quality observability, not just "did it respond." Every claim in the codebase is backed by a 228-test suite spanning unit, database-integration, API, and AI-pipeline layers, running in CI alongside static typing, linting, and dependency vulnerability scanning. A security review found and fixed a genuine, non-obvious bug in how FastAPI's exception handling interacts with custom middleware — the kind of finding that only shows up when you actually test the thing you built, not just build it.
>
> [GitHub](https://github.com/Kavisk46/Opsmind-ai) · Backend: FastAPI, PostgreSQL, ChromaDB, Docker · Frontend: Next.js, React, TypeScript

## Technical Blog Outline

**Title ideas:** *"What a RAG Backend Looks Like When You Actually Test It"* / *"The Starlette Bug That Only Showed Up When I Tried to Fix Error Handling"*

1. **The premise** — most RAG tutorials stop at "call the LLM with retrieved context." What's missing: token budgeting, cost tracking, retrieval evaluation, and knowing when any of it breaks.
2. **The architecture** — layered backend, dependency injection as the thing that makes testing possible at all (concrete before/after: what a test would need without it).
3. **Token budgeting, concretely** — why message-count caps lie, what a token-budget-based truncation actually buys you, the two-layer defense-in-depth reasoning.
4. **Golden regression testing** — why a semantically-blind fake embedding model (fine for plumbing tests) is *not* fine for a retrieval-regression dataset, and the specific bug (an all-zero embedding vector from a query with no matching keyword) that proved it.
5. **The middleware bug** — the centerpiece. Walk through: registering `@app.exception_handler(Exception)`, assuming it was sufficient, writing a test that proved otherwise, isolating the exact trigger (`Depends(get_db)`'s async-generator pattern) with a minimal reproduction, and the actual fix (wrapping `call_next()`, not rewriting the whole middleware stack).
6. **What's still not done, and why that's stated plainly** — no path to the `admin` role for a real user, the CVEs with fix versions not yet applied, the `Protocol` inconsistency, the still-mock dashboard/analytics surface with no backend data behind it. A real engineering project has a roadmap, not a claim of completeness.

## Interview Talking Points

**"Tell me about a bug you found."** The Starlette `BaseHTTPMiddleware` + exception-handler interaction — walk through the full diagnostic process: wrote a test expecting the registered handler to work, it failed with the raw exception instead of a clean response, built a minimal standalone reproduction to isolate the exact trigger (an async-generator dependency, not "any exception"), confirmed the theory precisely before touching the fix, then fixed it at the correct layer instead of the first thing that looked like it might work.

**"How do you approach testing?"** Point at the pyramid actually built: unit tests using hand-written fakes (not `Mock()` — explain why, concretely, with the "a typo'd method fails loudly vs. silently" reasoning), repository tests against a real (if swapped) database to catch real constraint violations, and a golden dataset specifically because plumbing tests can't catch a retrieval-quality regression.

**"How do you think about AI systems specifically, versus a normal backend?"** The observability angle — token budgeting and cost tracking aren't optional extras, they're what turns "I called an API" into an operable product. Concrete example: `context_provided`/`citation_count` as an honest, scoped substitute for real hallucination detection — knowing the difference between what you've built and what you'd need to build next matters as much as the code itself.

**"What would you do differently, or next?"** A real admin-role path first (the RBAC-gated Analytics feature is unreachable for any real signed-up user today — a genuine gap, not a hypothetical one); the `Protocol`-typing inconsistency between `EmbeddingModel`/`Storage`/`LLMProvider` and `VectorStore`/`DocumentRepository` — a good, honest example of scope discipline (noticed, documented, deliberately deferred rather than rushed as a side effect of an unrelated change).
