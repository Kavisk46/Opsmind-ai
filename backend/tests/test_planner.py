from services.planner import Planner, RetrievalPlan


def _plan(question: str) -> RetrievalPlan:
    return Planner().plan(question)


# --- query rewriting ---


def test_strips_what_is_prefix():
    plan = _plan("What is SOC2?")
    assert plan.rewritten_query == "SOC2"


def test_strips_what_happened_during_prefix():
    plan = _plan("What happened during incident 52?")
    assert plan.rewritten_query == "incident 52"


def test_strips_tell_me_about_prefix():
    plan = _plan("Tell me about the deployment pipeline")
    assert plan.rewritten_query == "the deployment pipeline"


def test_strips_trailing_question_mark_even_without_a_recognized_prefix():
    # "What is?" has no space before "?", so it doesn't match the
    # "what is " prefix at all — only the trailing "?" gets stripped.
    plan = _plan("What is?")
    assert plan.rewritten_query == "What is"


def test_leaves_a_question_with_no_recognized_prefix_unchanged():
    plan = _plan("SOC2 compliance requirements")
    assert plan.rewritten_query == "SOC2 compliance requirements"


def test_falls_back_to_the_original_question_if_stripping_leaves_nothing():
    # The prefix matches ("what is ") but everything after it is just
    # whitespace/punctuation — stripping it would leave an empty string,
    # which is never a useful thing to search for, so this falls back to
    # the original (outer-whitespace-trimmed) question instead.
    plan = _plan("What is   ?")
    assert plan.rewritten_query == "What is   ?"


def test_only_strips_a_leading_prefix_not_one_appearing_mid_question():
    plan = _plan("Our runbook explains what is expected during an incident")
    assert plan.rewritten_query == "Our runbook explains what is expected during an incident"


# --- top_k selection ---


def test_default_top_k_for_a_simple_factual_question():
    plan = _plan("What is SOC2?")
    assert plan.top_k == 5


def test_higher_top_k_for_an_incident_question():
    plan = _plan("What happened during incident 52?")
    assert plan.top_k == 8


def test_higher_top_k_for_a_detailed_history_question():
    plan = _plan("Give me a detailed history of the outage")
    assert plan.top_k == 8


# --- search_strategy ---


def test_search_strategy_is_always_hybrid():
    # RetrievalService.retrieve_hybrid() always runs both legs — this
    # phase doesn't modify retrieval internals, so nothing downstream
    # can actually act on "vector" or "keyword" alone yet.
    assert _plan("What is SOC2?").search_strategy == "hybrid"
    assert _plan("What happened during incident 52?").search_strategy == "hybrid"


# --- use_metadata ---


def test_flags_a_document_count_question_as_metadata():
    plan = _plan("How many documents have I uploaded?")
    assert plan.use_metadata is True


def test_flags_a_list_documents_question_as_metadata():
    plan = _plan("List my documents")
    assert plan.use_metadata is True


def test_does_not_flag_a_content_question_as_metadata():
    plan = _plan("What is SOC2?")
    assert plan.use_metadata is False
