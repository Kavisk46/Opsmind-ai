import { apiClient } from "@/lib/api";

// Wire shape verified directly against
// backend/services/ai_metrics_service.py's AIMetricsService.summary() —
// never guessed. Every sub-object is a bounded, in-memory, per-process
// snapshot of at most the last 200 recorded events (see that file's
// class docstring) — there is no time-series/history behind this, and no
// per-day breakdown exists anywhere in the backend. Fields beyond
// total_requests/total_answers are OMITTED by the backend entirely (not
// zeroed) when there's no history yet, hence the optional markers below.
interface LlmSummaryWire {
  total_requests: number;
  success_count?: number;
  failure_count?: number;
  avg_latency_ms?: number;
  total_tokens?: number;
  total_estimated_cost_usd?: number;
}

interface RetrievalSummaryWire {
  total_requests: number;
  avg_chunk_count?: number;
  avg_latency_ms?: number;
  avg_confidence?: number | null;
}

interface GenerationEvalSummaryWire {
  total_answers: number;
  avg_citation_count?: number;
  zero_citation_rate?: number;
  avg_answer_length_chars?: number;
}

interface AiMetricsSummaryWire {
  llm: LlmSummaryWire;
  retrieval: RetrievalSummaryWire;
  generation_eval: GenerationEvalSummaryWire;
}

export interface AiMetricsSummary {
  totalRequests: number;
  successCount: number;
  failureCount: number;
  avgLatencyMs: number | null;
  totalTokens: number;
  totalEstimatedCostUsd: number;
  avgCitationCount: number | null;
  zeroCitationRate: number | null;
}

function toAiMetricsSummary(wire: AiMetricsSummaryWire): AiMetricsSummary {
  return {
    totalRequests: wire.llm.total_requests,
    successCount: wire.llm.success_count ?? 0,
    failureCount: wire.llm.failure_count ?? 0,
    avgLatencyMs: wire.llm.avg_latency_ms ?? null,
    totalTokens: wire.llm.total_tokens ?? 0,
    totalEstimatedCostUsd: wire.llm.total_estimated_cost_usd ?? 0,
    avgCitationCount: wire.generation_eval.avg_citation_count ?? null,
    zeroCitationRate: wire.generation_eval.zero_citation_rate ?? null,
  };
}

// GET /internal/ai-metrics — requires the ADMIN role (verified in
// api/routes/ai_metrics.py: `Depends(require_role(UserRole.ADMIN))`), a
// real, deliberate authorization gate, not an oversight. A regular signed-
// up user (default role is MEMBER — see models/user.py) will get a 403
// here; callers MUST check `error.status === 403` and show a real
// "admin access required" state rather than treating it as a generic
// failure or retrying.
export async function getAiMetricsSummary(options?: {
  signal?: AbortSignal;
}): Promise<AiMetricsSummary> {
  const summary = await apiClient.get<AiMetricsSummaryWire>(
    "/internal/ai-metrics",
    { signal: options?.signal }
  );
  return toAiMetricsSummary(summary);
}
