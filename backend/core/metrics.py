from prometheus_client import Counter, Histogram

# Two metrics, the standard minimal pair for HTTP observability: a
# Counter (how many requests, broken down by outcome) and a Histogram
# (how long they took, as a distribution — not just an average, which
# hides whether most requests are fast with a few very slow outliers, or
# uniformly medium).
#
# Labeled by the ROUTE TEMPLATE ("/documents/{document_id}"), never the
# resolved path with a real ID in it — this matters. Prometheus creates
# one time series PER UNIQUE LABEL COMBINATION; using the real path would
# mean a new time series for every distinct document/user/conversation ID
# ever requested, growing without bound ("cardinality explosion") and
# eventually overwhelming whatever stores these metrics. The template
# has a small, fixed number of possible values — one series per actual
# route, forever, regardless of how much traffic or how many resources
# exist.
REQUEST_COUNT = Counter(
    "opsmind_http_requests_total",
    "Total HTTP requests handled",
    ["method", "path", "status_code"],
)

REQUEST_DURATION_SECONDS = Histogram(
    "opsmind_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)


# AI-specific metrics (AI Evaluation and Observability phase). Same
# cardinality reasoning as above: provider ("local"/"openai"/...), model
# (one configured model name at a time — see core/config.py's comment on
# why model name is a single shared setting), and tool ("rag_retrieval"/
# "document_metadata") are all small, fixed sets, never per-request IDs.
AI_REQUEST_COUNT = Counter(
    "opsmind_ai_requests_total",
    "Total AI (LLM) requests handled, by outcome",
    ["provider", "model", "status"],
)

AI_REQUEST_DURATION_SECONDS = Histogram(
    "opsmind_ai_request_duration_seconds",
    "AI (LLM) request duration in seconds",
    ["provider", "model"],
)

AI_TOKENS_TOTAL = Counter(
    "opsmind_ai_tokens_total",
    "Total tokens consumed by AI requests",
    ["provider", "model", "token_type"],
)

# A running total, not a snapshot — Counters only ever increase, matching
# how cost actually accumulates. This is an ESTIMATE (see
# services/ai_metrics_service.py's pricing table), never a real billing
# figure.
AI_ESTIMATED_COST_USD = Counter(
    "opsmind_ai_estimated_cost_usd_total",
    "Estimated cumulative USD cost of AI requests (approximate, not real billing)",
    ["provider", "model"],
)

RETRIEVAL_CHUNK_COUNT = Histogram(
    "opsmind_retrieval_chunk_count",
    "Number of chunks returned per retrieval",
    ["tool"],
)

RETRIEVAL_DURATION_SECONDS = Histogram(
    "opsmind_retrieval_duration_seconds",
    "Retrieval duration in seconds",
    ["tool"],
)


# Volume 4 Phase 4: Observability & Monitoring.
#
# Labeled by `operation` (get_by_id/get_all/create/update/delete/exists —
# BaseRepository's own six generic methods) and `model` (the entity name,
# e.g. "User"/"Document" — repositories/base.py's `self.model.__name__`).
# Both are small, fixed sets — one series per (operation, model) pair,
# never per query/row, same cardinality discipline as every metric above.
#
# Deliberately instrumented at BaseRepository, not in every individual
# repository method — this covers the ~80% shared path every repository
# inherits (the same reasoning BaseRepository itself already documents
# for code reuse) in one place. Repository-SPECIFIC queries
# (UserRepository.get_by_email, ConversationRepository.list_by_owner,
# etc.) are NOT individually instrumented — each would need its own
# timing code, which is real, uncaptured effort left for whenever a
# specific slow custom query actually needs investigating, not applied
# blindly everywhere up front.
DB_QUERY_DURATION_SECONDS = Histogram(
    "opsmind_db_query_duration_seconds",
    "Database query duration in seconds, for BaseRepository's shared CRUD methods",
    ["operation", "model"],
)

# Labeled by `outcome` (success/failed/deleted_before_processing) — a
# document deleted between upload and background-task pickup is a real,
# normal, non-error outcome (see IngestionService.process_document's
# early return), worth distinguishing from a genuine processing failure
# rather than lumping both under "not success."
INGESTION_DURATION_SECONDS = Histogram(
    "opsmind_ingestion_duration_seconds",
    "Document ingestion pipeline duration in seconds (extract -> chunk -> embed -> store)",
    ["outcome"],
    # Ingestion is measured in whole seconds, not milliseconds (unlike
    # the HTTP/AI histograms above, which use Prometheus's default
    # buckets) — a document can legitimately take many seconds to
    # process, so the default buckets (topping out at 10s) would bucket
    # almost everything into the same "+Inf" catch-all, losing exactly
    # the resolution that matters for this metric.
    buckets=(1, 2, 5, 10, 30, 60, 120, 300),
)
