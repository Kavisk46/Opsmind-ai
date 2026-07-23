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
