# --- builder: install dependencies into an isolated virtualenv --------
# Separated from the runtime stage so pip's build artifacts, its cache,
# and (if any dependency ever needs one) a C compiler never end up in
# the final image — only the installed *virtualenv* gets copied forward
# below. requirements.txt is copied and installed BEFORE the rest of the
# source so Docker's layer cache only reinstalls dependencies when
# requirements.txt itself changes, not on every code edit — this
# already existed and is worth keeping exactly as-is.
FROM python:3.12-slim AS builder

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- runtime: the actual production image ------------------------------
# Fresh FROM python:3.12-slim, not `FROM builder` — pip itself, any
# build-only tooling, and requirements.txt's own resolution metadata
# never exist in this final image, only the /opt/venv this stage copies
# in below.
FROM python:3.12-slim AS runtime

WORKDIR /app

# PYTHONUNBUFFERED: without it, Python buffers stdout/stderr when they
# aren't a real TTY — always true inside a container. Log lines can sit
# in that buffer instead of reaching `docker logs`/the log collector in
# real time, and are lost outright if the process is killed before the
# buffer flushes. A real, common, easy-to-miss production gap — this
# app's structured JSON logging (core/logging.py) is only as useful as
# its timeliness.
# PYTHONDONTWRITEBYTECODE: skips writing .pyc files into the image's
# writable layer — no runtime behavior change, just avoids bytecode
# nobody will reuse (the container is rebuilt from source every deploy).
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# A dedicated, unprivileged user — this process should never run as
# root inside the container, even though the container is already
# namespace-isolated from the host (defense in depth: a bug that lets
# an attacker execute arbitrary code inside this container still can't
# trivially escalate to root within it).
RUN groupadd --system app && useradd --system --gid app --no-create-home app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY . .

# storage/ and the ChromaDB persist dir are both written to by this
# process at runtime (uploaded files, vector index) — owned by `app`
# specifically so a non-root process can actually write there; without
# this, the first real upload would fail with a permissions error the
# moment USER app takes effect below.
RUN mkdir -p storage/documents storage/chroma \
    && chown -R app:app /app

USER app

EXPOSE 8000

# Hits the real, already-existing GET /health endpoint (api/routes/health.py)
# — no separate healthcheck script needed. start-period gives the
# process time to finish import-time work (this app's heaviest imports —
# torch/transformers/sentence-transformers/chromadb — genuinely take
# real wall-clock time, verified directly during this project's own
# perf-testing phase) before a slow *first* check counts as a failure.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=3).status == 200 else 1)"

# Migrations run as part of every container start, not a manually-typed
# platform dashboard field — nothing in this repo's deployment path ever
# invoked `alembic upgrade head` otherwise (only README's local "Getting
# Started" section did), which is exactly why `users` and every other
# table never existed on a fresh Neon database despite the migration
# files themselves being complete and correct. Shell form (not exec-array
# JSON form) specifically so `&&` works: alembic runs to completion and
# exits 0 before uvicorn ever starts, and a failed migration fails the
# container/health check loudly instead of booting a server with no
# schema. Idempotent on every restart — Alembic's own alembic_version
# table means "already at head" is a fast no-op, not a re-apply.
CMD alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000
