import statistics
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Protocol

from core.logging import logger
from core.metrics import (
    AI_ESTIMATED_COST_USD,
    AI_REQUEST_COUNT,
    AI_REQUEST_DURATION_SECONDS,
    AI_TOKENS_TOTAL,
    RETRIEVAL_CHUNK_COUNT,
    RETRIEVAL_DURATION_SECONDS,
)

# Illustrative, approximate USD price per 1,000 tokens for a handful of
# well-known hosted models — NOT a live pricing feed and not real billing
# (providers round/bill in their own units, and prices change over time).
# Good enough to answer "roughly how much is this costing us" during
# development; a real production system would source this from the
# provider's own billing API or a maintained pricing config, not a
# hardcoded dict. A model missing from this table (including "local",
# which is genuinely free) returns None from estimate_cost_usd() below —
# "no cost estimate available", never a silent 0.0 that could be
# misread as "confirmed free."
_PRICING_PER_1K_TOKENS_USD: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-3.5-turbo": (0.0005, 0.0015),
    "claude-3-haiku-20240307": (0.00025, 0.00125),
}


def estimate_cost_usd(
    *, model: str, prompt_tokens: int | None, completion_tokens: int | None
) -> float | None:
    """A deliberately simple estimate: (tokens / 1000) * price-per-1000,
    summed across prompt and completion (most providers price these
    differently — completion tokens are usually pricier, since they're
    the part the model actually generates). Returns None whenever a real
    number can't be trusted: missing token counts (the local provider
    never reports them) or a model this table doesn't recognize.
    """
    if prompt_tokens is None or completion_tokens is None:
        return None
    pricing = _PRICING_PER_1K_TOKENS_USD.get(model)
    if pricing is None:
        return None
    prompt_price, completion_price = pricing
    return round(
        (prompt_tokens / 1000) * prompt_price + (completion_tokens / 1000) * completion_price,
        6,
    )


class AIMetricsRecorder(Protocol):
    """The shape AIOrchestrator actually depends on — not the full
    AIMetricsService surface (summary()/aggregation is a concern of the
    internal metrics endpoint, never of the orchestrator itself). A test
    can hand the orchestrator a plain spy satisfying just these three
    methods instead of a real AIMetricsService — the same DI pattern
    ConversationService uses for its repositories (see
    services/conversation_service.py's ConversationStore/MessageStore).
    """

    def record_llm_request(
        self,
        *,
        provider: str,
        model: str,
        prompt_tokens: int | None,
        completion_tokens: int | None,
        latency_seconds: float,
        success: bool,
        conversation_id: uuid.UUID | None = None,
        error: str | None = None,
    ) -> None: ...

    def record_retrieval(
        self,
        *,
        tool_name: str,
        chunk_count: int,
        latency_seconds: float,
        confidence_scores: list[float] | None = None,
        conversation_id: uuid.UUID | None = None,
    ) -> None: ...

    def record_generation_eval(
        self,
        *,
        tool_used: str,
        citation_count: int,
        context_provided: bool,
        answer_length_chars: int,
        conversation_id: uuid.UUID | None = None,
    ) -> None: ...


@dataclass
class LLMRequestRecord:
    provider: str
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    latency_seconds: float
    success: bool
    estimated_cost_usd: float | None
    conversation_id: uuid.UUID | None = None
    error: str | None = None


@dataclass
class RetrievalRecord:
    tool_name: str
    chunk_count: int
    latency_seconds: float
    avg_confidence: float | None
    conversation_id: uuid.UUID | None = None


@dataclass
class GenerationEvalRecord:
    tool_used: str
    citation_count: int
    context_provided: bool
    answer_length_chars: int
    conversation_id: uuid.UUID | None = None


class AIMetricsService:
    """Central place every AI-related metric flows through: Prometheus
    counters/histograms (scraped via GET /metrics, for a real monitoring
    stack), structured JSON logs (for per-request debugging/correlation),
    and a small bounded in-memory history plus running aggregates (for
    GET /internal/ai-metrics's human-readable summary). One class owns
    all three so AIOrchestrator's instrumentation calls stay to one
    method call per event — it never touches Prometheus or the logger
    directly itself (see AIMetricsRecorder above).

    In-memory, per-process, not persisted to a database — the same
    accepted tradeoff as RateLimiter (api/dependencies.py): correct for a
    single-instance development/demo deployment, and GET /metrics already
    gives you a real path to a persistent time series (a Prometheus
    server scraping this process) without this class needing to
    reimplement one. A multi-replica production deployment would need
    metrics aggregated centrally (Prometheus federation, or this data
    pushed to a shared store) rather than read per-instance like this.
    """

    _MAX_RECENT = 200

    def __init__(self) -> None:
        self._llm_records: deque[LLMRequestRecord] = deque(maxlen=self._MAX_RECENT)
        self._retrieval_records: deque[RetrievalRecord] = deque(maxlen=self._MAX_RECENT)
        self._generation_eval_records: deque[GenerationEvalRecord] = deque(
            maxlen=self._MAX_RECENT
        )

    def record_llm_request(
        self,
        *,
        provider: str,
        model: str,
        prompt_tokens: int | None,
        completion_tokens: int | None,
        latency_seconds: float,
        success: bool,
        conversation_id: uuid.UUID | None = None,
        error: str | None = None,
    ) -> None:
        total_tokens = (
            prompt_tokens + completion_tokens
            if prompt_tokens is not None and completion_tokens is not None
            else None
        )
        cost = estimate_cost_usd(
            model=model, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
        )

        self._llm_records.append(
            LLMRequestRecord(
                provider=provider,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_seconds=latency_seconds,
                success=success,
                estimated_cost_usd=cost,
                conversation_id=conversation_id,
                error=error,
            )
        )

        status = "success" if success else "failure"
        AI_REQUEST_COUNT.labels(provider=provider, model=model, status=status).inc()
        AI_REQUEST_DURATION_SECONDS.labels(provider=provider, model=model).observe(
            latency_seconds
        )
        if prompt_tokens is not None:
            AI_TOKENS_TOTAL.labels(
                provider=provider, model=model, token_type="prompt"
            ).inc(prompt_tokens)
        if completion_tokens is not None:
            AI_TOKENS_TOTAL.labels(
                provider=provider, model=model, token_type="completion"
            ).inc(completion_tokens)
        if cost is not None:
            AI_ESTIMATED_COST_USD.labels(provider=provider, model=model).inc(cost)

        log_fn = logger.info if success else logger.error
        log_fn(
            "AI request %s",
            status,
            extra={
                "llm_provider": provider,
                "llm_model": model,
                "llm_duration_ms": round(latency_seconds * 1000, 2),
                "llm_success": success,
                "llm_prompt_tokens": prompt_tokens,
                "llm_completion_tokens": completion_tokens,
                "estimated_cost_usd": cost,
                "conversation_id": str(conversation_id) if conversation_id else None,
                "error": error,
            },
        )

    def record_retrieval(
        self,
        *,
        tool_name: str,
        chunk_count: int,
        latency_seconds: float,
        confidence_scores: list[float] | None = None,
        conversation_id: uuid.UUID | None = None,
    ) -> None:
        avg_confidence = (
            round(statistics.mean(confidence_scores), 4) if confidence_scores else None
        )
        self._retrieval_records.append(
            RetrievalRecord(
                tool_name=tool_name,
                chunk_count=chunk_count,
                latency_seconds=latency_seconds,
                avg_confidence=avg_confidence,
                conversation_id=conversation_id,
            )
        )

        RETRIEVAL_CHUNK_COUNT.labels(tool=tool_name).observe(chunk_count)
        RETRIEVAL_DURATION_SECONDS.labels(tool=tool_name).observe(latency_seconds)

        logger.info(
            "Retrieval evaluated",
            extra={
                "tool": tool_name,
                "retrieval_chunk_count": chunk_count,
                "retrieval_duration_ms": round(latency_seconds * 1000, 2),
                "retrieval_avg_confidence": avg_confidence,
                "conversation_id": str(conversation_id) if conversation_id else None,
            },
        )

    def record_generation_eval(
        self,
        *,
        tool_used: str,
        citation_count: int,
        context_provided: bool,
        answer_length_chars: int,
        conversation_id: uuid.UUID | None = None,
    ) -> None:
        self._generation_eval_records.append(
            GenerationEvalRecord(
                tool_used=tool_used,
                citation_count=citation_count,
                context_provided=context_provided,
                answer_length_chars=answer_length_chars,
                conversation_id=conversation_id,
            )
        )

        logger.info(
            "Generation evaluated",
            extra={
                "tool": tool_used,
                "citation_count": citation_count,
                "context_provided": context_provided,
                "answer_length_chars": answer_length_chars,
                "conversation_id": str(conversation_id) if conversation_id else None,
            },
        )

    def summary(self) -> dict:
        """Aggregated, human-readable snapshot for the internal dev
        endpoint — recomputed fresh from the bounded in-memory history on
        every call, never cached, since this is a low-traffic debugging
        endpoint, not a hot path worth optimizing.
        """
        return {
            "llm": self._llm_summary(),
            "retrieval": self._retrieval_summary(),
            "generation_eval": self._generation_eval_summary(),
        }

    def _llm_summary(self) -> dict:
        records = list(self._llm_records)
        if not records:
            return {"total_requests": 0}

        by_provider_model: dict[str, dict] = defaultdict(
            lambda: {
                "count": 0,
                "success_count": 0,
                "total_tokens": 0,
                "estimated_cost_usd": 0.0,
            }
        )
        for r in records:
            bucket = by_provider_model[f"{r.provider}:{r.model}"]
            bucket["count"] += 1
            bucket["success_count"] += int(r.success)
            bucket["total_tokens"] += r.total_tokens or 0
            bucket["estimated_cost_usd"] += r.estimated_cost_usd or 0.0

        return {
            "total_requests": len(records),
            "success_count": sum(1 for r in records if r.success),
            "failure_count": sum(1 for r in records if not r.success),
            "avg_latency_ms": round(
                statistics.mean(r.latency_seconds for r in records) * 1000, 2
            ),
            "total_tokens": sum(r.total_tokens or 0 for r in records),
            "total_estimated_cost_usd": round(
                sum(r.estimated_cost_usd or 0.0 for r in records), 6
            ),
            "by_provider_model": dict(by_provider_model),
        }

    def _retrieval_summary(self) -> dict:
        records = list(self._retrieval_records)
        if not records:
            return {"total_requests": 0}

        confidences = [r.avg_confidence for r in records if r.avg_confidence is not None]
        return {
            "total_requests": len(records),
            "avg_chunk_count": round(statistics.mean(r.chunk_count for r in records), 2),
            "avg_latency_ms": round(
                statistics.mean(r.latency_seconds for r in records) * 1000, 2
            ),
            "avg_confidence": round(statistics.mean(confidences), 4) if confidences else None,
        }

    def _generation_eval_summary(self) -> dict:
        records = list(self._generation_eval_records)
        if not records:
            return {"total_answers": 0}

        zero_citation_count = sum(1 for r in records if r.citation_count == 0)
        return {
            "total_answers": len(records),
            "avg_citation_count": round(
                statistics.mean(r.citation_count for r in records), 2
            ),
            "zero_citation_rate": round(zero_citation_count / len(records), 4),
            "avg_answer_length_chars": round(
                statistics.mean(r.answer_length_chars for r in records), 2
            ),
        }
