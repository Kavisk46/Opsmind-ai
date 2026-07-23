from services.ai_metrics_service import AIMetricsService, estimate_cost_usd


# --- estimate_cost_usd() ---


def test_estimate_cost_usd_known_model():
    cost = estimate_cost_usd(model="gpt-4o-mini", prompt_tokens=1000, completion_tokens=1000)
    # round() to sidestep float-representation noise (0.00015 + 0.0006
    # and the function's own rounded return value aren't bit-identical
    # even though they're mathematically the same number) — comparing
    # unrounded floats for exact equality here would be testing binary
    # floating-point representation, not the pricing logic.
    assert cost == round(0.00015 + 0.0006, 6)


def test_estimate_cost_usd_returns_none_for_unknown_model():
    assert estimate_cost_usd(model="local-qwen", prompt_tokens=100, completion_tokens=50) is None


def test_estimate_cost_usd_returns_none_when_tokens_missing():
    assert estimate_cost_usd(model="gpt-4o-mini", prompt_tokens=None, completion_tokens=None) is None


# --- record_llm_request() ---


def test_llm_summary_empty_before_any_request():
    service = AIMetricsService()
    assert service.summary()["llm"] == {"total_requests": 0}


def test_llm_summary_counts_success_and_failure_separately():
    service = AIMetricsService()
    service.record_llm_request(
        provider="openai", model="gpt-4o-mini", prompt_tokens=100, completion_tokens=50,
        latency_seconds=0.5, success=True,
    )
    service.record_llm_request(
        provider="openai", model="gpt-4o-mini", prompt_tokens=None, completion_tokens=None,
        latency_seconds=0.1, success=False, error="timeout",
    )

    summary = service.summary()["llm"]
    assert summary["total_requests"] == 2
    assert summary["success_count"] == 1
    assert summary["failure_count"] == 1


def test_llm_summary_totals_tokens_and_cost_across_requests():
    service = AIMetricsService()
    service.record_llm_request(
        provider="openai", model="gpt-4o-mini", prompt_tokens=1000, completion_tokens=1000,
        latency_seconds=0.5, success=True,
    )
    service.record_llm_request(
        provider="openai", model="gpt-4o-mini", prompt_tokens=1000, completion_tokens=1000,
        latency_seconds=0.5, success=True,
    )

    summary = service.summary()["llm"]
    assert summary["total_tokens"] == 4000
    assert summary["total_estimated_cost_usd"] == round(2 * (0.00015 + 0.0006), 6)


def test_llm_summary_groups_by_provider_and_model():
    service = AIMetricsService()
    service.record_llm_request(
        provider="openai", model="gpt-4o-mini", prompt_tokens=10, completion_tokens=10,
        latency_seconds=0.1, success=True,
    )
    service.record_llm_request(
        provider="local", model="qwen", prompt_tokens=None, completion_tokens=None,
        latency_seconds=1.0, success=True,
    )

    by_provider_model = service.summary()["llm"]["by_provider_model"]
    assert set(by_provider_model.keys()) == {"openai:gpt-4o-mini", "local:qwen"}
    assert by_provider_model["openai:gpt-4o-mini"]["count"] == 1
    assert by_provider_model["local:qwen"]["total_tokens"] == 0


def test_llm_summary_handles_missing_token_counts_without_crashing():
    service = AIMetricsService()
    service.record_llm_request(
        provider="local", model="qwen", prompt_tokens=None, completion_tokens=None,
        latency_seconds=2.0, success=True,
    )

    summary = service.summary()["llm"]
    assert summary["total_tokens"] == 0
    assert summary["total_estimated_cost_usd"] == 0.0


# --- record_retrieval() ---


def test_retrieval_summary_empty_before_any_retrieval():
    service = AIMetricsService()
    assert service.summary()["retrieval"] == {"total_requests": 0}


def test_retrieval_summary_averages_chunk_count_and_confidence():
    # avg_confidence is the mean of each RETRIEVAL's own average
    # confidence (0.75 and 0.5 below), not a pooled mean across every
    # individual chunk score regardless of which retrieval it came from
    # — each retrieval event counts equally, whether it returned 4 chunks
    # or 2.
    service = AIMetricsService()
    service.record_retrieval(
        tool_name="rag_retrieval", chunk_count=4, latency_seconds=0.2,
        confidence_scores=[0.9, 0.8, 0.7, 0.6],
    )
    service.record_retrieval(
        tool_name="rag_retrieval", chunk_count=2, latency_seconds=0.1,
        confidence_scores=[0.5, 0.5],
    )

    summary = service.summary()["retrieval"]
    assert summary["total_requests"] == 2
    assert summary["avg_chunk_count"] == 3.0
    assert summary["avg_confidence"] == round((0.75 + 0.5) / 2, 4)


def test_retrieval_summary_confidence_is_none_when_no_scores_ever_given():
    service = AIMetricsService()
    service.record_retrieval(tool_name="rag_retrieval", chunk_count=0, latency_seconds=0.05)

    summary = service.summary()["retrieval"]
    assert summary["avg_confidence"] is None


# --- record_generation_eval() ---


def test_generation_eval_summary_empty_before_any_answer():
    service = AIMetricsService()
    assert service.summary()["generation_eval"] == {"total_answers": 0}


def test_generation_eval_summary_computes_zero_citation_rate():
    service = AIMetricsService()
    service.record_generation_eval(
        tool_used="rag_retrieval", citation_count=2, context_provided=True,
        answer_length_chars=120,
    )
    service.record_generation_eval(
        tool_used="rag_retrieval", citation_count=0, context_provided=False,
        answer_length_chars=40,
    )

    summary = service.summary()["generation_eval"]
    assert summary["total_answers"] == 2
    assert summary["zero_citation_rate"] == 0.5
    assert summary["avg_citation_count"] == 1.0
    assert summary["avg_answer_length_chars"] == 80.0


# --- bounded history ---


def test_llm_history_is_bounded_and_does_not_grow_unbounded():
    service = AIMetricsService()
    for _ in range(service._MAX_RECENT + 50):
        service.record_llm_request(
            provider="local", model="qwen", prompt_tokens=None, completion_tokens=None,
            latency_seconds=0.01, success=True,
        )

    assert service.summary()["llm"]["total_requests"] == service._MAX_RECENT
