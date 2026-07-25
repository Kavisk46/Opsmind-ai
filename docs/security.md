# Security

## Summary

| Control | Status |
|---|---|
| Password hashing | bcrypt, real salted hash |
| Password policy | 8–128 chars, length-focused (NIST 800-63B-aligned) |
| JWT | HS256, 30-minute expiry, startup check refuses the insecure default secret outside `development` |
| Authorization | Role-based (`member`/`manager`/`admin`), enforced via `require_role()`, layered cleanly on top of authentication |
| Anti-enumeration | "Doesn't exist" and "not yours" return identical 404s throughout; wrong password and unknown email return identical 401s |
| SQL injection | Not applicable — SQLAlchemy's query builder is used exclusively, every value parameter-bound, verified by direct search for any string-interpolated SQL (none found) |
| CORS | Explicit allowlist (`settings.cors_allowed_origins`), never a wildcard |
| Security headers | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` on every response |
| Rate limiting | Login (5/60s) and signup (10/60s), per-IP, in-memory |
| File upload validation | Size limit + content-type allowlist enforced synchronously at upload time, not discovered later in background processing |
| Error responses | One consistent envelope, real exception detail logged server-side only, never echoed to a client |
| Dependency scanning | `pip-audit` in CI (informational — see [`deployment.md`](deployment.md#cicd) for why) |

## What Was Actually Found and Fixed

This wasn't a theoretical checklist — every item below was found by reading the real code, then verified fixed by running the actual test suite:

- **CORS was completely unconfigured.** Without it, a real browser running the frontend at a different origin than the API would have every cross-origin request silently blocked — never wired up before this review.
- **Zero security headers on the API.** The frontend had some (`next.config.ts`); the backend had none.
- **No password length requirement at all** — a single-character password was valid, all the way to a real bcrypt hash.
- **File upload content-type was never validated before acceptance** — any file, with any declared type, was accepted, stored, and only discovered as unprocessable later, during background ingestion.
- **No rate limiting on signup** — only login was protected.
- **No startup check against the insecure default `SECRET_KEY`** — the app would boot silently in any environment with a publicly-known, hardcoded signing secret.
- **A deeper bug, found while building the fix for unhandled exceptions**: a registered `@app.exception_handler(Exception)` alone does **not** reliably catch an exception raised inside any route using `Depends(get_db)` — i.e. almost every real route — when combined with this app's custom `@app.middleware("http")`. This is a documented upstream Starlette interaction (`BaseHTTPMiddleware` + generator-based dependencies), reproduced and confirmed with a standalone diagnostic before being fixed properly by wrapping `call_next()` directly inside the middleware.

## Known, Accepted Limitations

Stated honestly, not hidden:

- **`RateLimiter` is in-memory and single-process** — correct at this project's current scale; a multi-replica deployment would need the counters moved to Redis (`INCR`+`EXPIRE`), already noted as the intended upgrade path throughout the codebase.
- **File-type validation is declared-header-based, not magic-byte content sniffing** — a client can still lie about `Content-Type`. The extraction pipeline fails safely either way (a malformed PDF/text file is caught and marked `FAILED`, never crashes the process), but this is a real, named limit worth stating precisely rather than overclaiming protection that doesn't exist.
- **28 known CVEs across dependencies** (`pip-audit`, run for the first time during this review) — `pyjwt`, `python-multipart`, and `starlette` each have an available fix version not yet applied (a live upgrade-and-full-retest pass was deliberately deferred rather than rushed this same session); `chromadb`'s finding currently has no published fix at all.

## Production Deployment Checklist

- [ ] Real `SECRET_KEY`, from a secret manager, never the default (enforced by startup check)
- [ ] `DATABASE_URL` uses real, non-default credentials; Postgres not exposed on a public port
- [ ] CORS allowlist reflects the real production frontend origin(s), not `localhost`
- [ ] `pyjwt` / `python-multipart` / `starlette` upgraded to their fixed versions; `chromadb`'s open CVE tracked
- [ ] Non-root Docker users confirmed in both images (already true)
- [ ] Branch protection requires CI passing before merge (a GitHub repo setting, not part of `ci.yml` itself)
- [ ] TLS termination in front of the API (not something this repo's Dockerfiles handle)
