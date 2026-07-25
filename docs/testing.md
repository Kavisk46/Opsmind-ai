# Testing Strategy

228 tests across 29 files, run in ~2–3 minutes with **zero external dependencies** — no real Postgres, no real ChromaDB network calls, no real LLM API calls, anywhere.

```bash
cd backend
pytest -q                                                             # everything
pytest --cov=api --cov=core --cov=services --cov-report=term-missing  # + coverage
pytest tests/test_orchestrator.py -q                                  # one file
```

## The Pyramid, as Actually Built

| Layer | Files (examples) | What's real, what's faked |
|---|---|---|
| **Unit** | `test_prompt_builder.py`, `test_orchestrator.py`, `test_retrieval_service.py`, `test_ai_metrics_service.py`, `test_conversation_service.py`, `test_tools.py` | Nothing real — every collaborator is a hand-written fake or stub |
| **Repository / DB integration** | `test_user_repository.py`, `test_document_repository.py`, `test_db_constraints.py`, `test_alembic_migrations.py` | A real SQLite engine (swapped in for Postgres), real constraints, real cascades — `PRAGMA foreign_keys=ON` explicitly enabled, since SQLite doesn't enforce FKs by default the way Postgres always does |
| **API** | `test_chat.py`, `test_documents.py`, `test_users_rbac.py`, `test_auth.py`, `test_observability.py` | Full FastAPI `TestClient` request/response cycle, real routing/auth/validation, fake AI dependencies |
| **AI pipeline / golden** | `test_vector_store.py`, `test_golden_retrieval.py` | A real embedded ChromaDB (no network dependency — safe to use for real), a semantically-meaningful fake embedding model built specifically for regression testing |

## Why Fakes, Not Mocks, for Most of This

The suite is built almost entirely from hand-written fake classes (`FakeLLM`, `FakeEmbeddingModel`, `FakeVectorStore`, `FakeRetriever`, `FakeConversationStore`) rather than `unittest.mock.Mock()`. A hand-written fake has to actually implement the right method shape to work at all — a typo'd method name fails loudly. A bare `Mock()` accepts *any* attribute access or call silently, which can hide a real interface mismatch instead of catching it. The one deliberate exception: `test_llm_providers.py` mocks the OpenAI SDK client directly — mocking a third-party SDK you don't own is exactly the case a full hand-written fake would be overkill for.

## Test Isolation

Every test gets a **fresh in-memory SQLite database** (not a shared database with per-test transaction rollback — the simpler of the two standard strategies, a deliberate choice given how cheap SQLite schema creation is at this scale). Stateful singletons (`RateLimiter`, `AIMetricsService`) are rebuilt fresh per test via `tests/conftest.py`'s fixtures — without this, a rate-limit counter or metrics aggregate would silently accumulate across unrelated tests in the same run.

## Golden Regression Testing

`test_golden_retrieval.py` is the one place retrieval *quality* — not just plumbing — gets verified: five documents on distinct topics, five realistic questions each paired with the one document that should come back. A dedicated sanity test (`test_every_golden_query_contains_at_least_one_vocabulary_keyword`) exists because an early draft of this file had two queries that "passed" for the wrong reason — a query containing none of the fake embedding model's vocabulary produces an all-zero vector, an undefined similarity that Chroma resolves by arbitrary tie-breaking, not real matching. Caught, understood, and guarded against — not just patched.

## A Known Typing Gap

Running mypy with `check_untyped_defs = true` (checking inside untyped test bodies) surfaces ~45 findings, almost all the same shape: a test fake (`FakeVectorStore`, `FakeDocumentRepository`) passed where a constructor is typed against a *concrete class* rather than a `Protocol`. This is real and structural — some dependencies (`EmbeddingModel`, `Storage`, `LLMProvider`) already use `Protocol`; others (`VectorStore`, `DocumentRepository`) don't yet. `mypy.ini` deliberately leaves `check_untyped_defs` at its default (off) rather than either ignoring the finding or rushing a Protocol-introduction refactor as a side effect of configuring a linter — a real, named future improvement, not a silently-swept-under gap.

## Load, Stress, and Spike Testing

`scripts/locustfile.py` defines realistic weighted user scenarios (login, upload, chat, health check) against a real HTTP server with fake AI dependencies (isolating *backend* performance from AI-inference latency). This work directly found and fixed a real bug: `bcrypt`'s password hashing was blocking the asyncio event loop under concurrent load — fixed with `asyncio.to_thread`, verified by re-running the load test and confirming request latency no longer degraded under concurrency.

## Static Analysis (Ruff + mypy)

Both run in CI (`.github/workflows/ci.yml`) and both were run against this codebase for the **first time** during the CI-setup phase — verified directly, not assumed clean. Ruff found 106 initial findings (mostly a single false-positive rule for FastAPI's `Depends()` pattern, plus real, safe modernizations, all applied and re-verified against the full test suite). mypy found 16 real issues on its first run, every one fixed properly (explicit type narrowing, `TYPE_CHECKING`-guarded imports for lazily-loaded SDKs, targeted `# type: ignore` comments only where a third-party stub was verifiably stricter than the library's real runtime behavior).
