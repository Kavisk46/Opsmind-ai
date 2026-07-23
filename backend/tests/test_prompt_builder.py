from services.prompt_builder import ContextChunk, PromptBuilder


# --- format_context() ---


def test_format_context_returns_placeholder_for_empty_chunks():
    result = PromptBuilder.format_context([])
    assert "No relevant context" in result


def test_format_context_includes_source_name_and_page_number():
    chunks = [ContextChunk(text="the pipeline stalled", source_name="postmortem.pdf", page_number=3)]
    result = PromptBuilder.format_context(chunks)
    assert "[Source 1: postmortem.pdf, page 3]" in result
    assert "the pipeline stalled" in result


def test_format_context_omits_page_number_when_none():
    chunks = [ContextChunk(text="some text", source_name="notes.txt", page_number=None)]
    result = PromptBuilder.format_context(chunks)
    assert "[Source 1: notes.txt]" in result
    assert "page" not in result


def test_format_context_omits_source_name_when_none():
    chunks = [ContextChunk(text="some text", source_name=None, page_number=None)]
    result = PromptBuilder.format_context(chunks)
    assert "[Source 1]" in result


def test_format_context_numbers_multiple_chunks_in_order():
    chunks = [
        ContextChunk(text="first", source_name="a.txt"),
        ContextChunk(text="second", source_name="b.txt"),
    ]
    result = PromptBuilder.format_context(chunks)
    assert "[Source 1: a.txt] first" in result
    assert "[Source 2: b.txt] second" in result


# --- Chat template ---


def test_build_assembles_instructions_context_and_question():
    builder = PromptBuilder()
    prompt = builder.build(question="What is OpsMind?", context_text="OpsMind is a platform.")
    assert "Context:\nOpsMind is a platform." in prompt
    assert "Question: What is OpsMind?" in prompt
    # Question must be the LAST thing before the model has to answer.
    assert prompt.rstrip().endswith("Answer:")


def test_build_omits_history_section_when_no_history():
    builder = PromptBuilder()
    prompt = builder.build(question="hello", context_text="ctx")
    assert "Previous conversation" not in prompt


def test_build_includes_history_when_present():
    builder = PromptBuilder()
    prompt = builder.build(
        question="What is my name?",
        context_text="ctx",
        history=[("user", "My name is Ada."), ("assistant", "Nice to meet you, Ada.")],
    )
    assert "My name is Ada." in prompt
    assert "Nice to meet you, Ada." in prompt


def test_build_truncates_history_to_max_history_messages():
    builder = PromptBuilder(max_history_messages=2)
    history = [
        ("user", "message one"),
        ("assistant", "reply one"),
        ("user", "message two"),
        ("assistant", "reply two"),
    ]
    prompt = builder.build(question="latest question", context_text="ctx", history=history)
    # Only the last 2 entries should survive.
    assert "message two" in prompt
    assert "reply two" in prompt
    assert "message one" not in prompt
    assert "reply one" not in prompt


# --- Prompt versioning ---


def test_chat_prompt_defaults_to_v1():
    builder = PromptBuilder()
    prompt = builder.build(question="q", context_text="ctx")
    assert "OpsMind, an assistant that answers questions" in prompt


def test_chat_prompt_v2_produces_different_instructions():
    v1_builder = PromptBuilder(chat_prompt_version="v1")
    v2_builder = PromptBuilder(chat_prompt_version="v2")

    v1_prompt = v1_builder.build(question="q", context_text="ctx")
    v2_prompt = v2_builder.build(question="q", context_text="ctx")

    assert v1_prompt != v2_prompt
    assert "at most 3 sentences" in v2_prompt
    assert "at most 3 sentences" not in v1_prompt
    # Both versions still carry the same grounding guardrail — versioning
    # changes tone/instructions, not whether hallucination prevention
    # applies at all.
    assert "grounded in the provided context" in v1_prompt
    assert "grounded in the provided context" in v2_prompt


# --- Summarization template ---


def test_build_summarization_prompt():
    builder = PromptBuilder()
    prompt = builder.build_summarization_prompt(
        document_name="postmortem.pdf", content="The outage lasted 3 hours."
    )
    assert "Document: postmortem.pdf" in prompt
    assert "The outage lasted 3 hours." in prompt
    assert prompt.rstrip().endswith("Summary:")


# --- Document comparison template ---


def test_build_comparison_prompt():
    builder = PromptBuilder()
    prompt = builder.build_comparison_prompt(
        document_a_name="v1.pdf",
        document_a_content="Deploys take 10 minutes.",
        document_b_name="v2.pdf",
        document_b_content="Deploys take 2 minutes.",
    )
    assert "Document A (v1.pdf):" in prompt
    assert "Document B (v2.pdf):" in prompt
    assert "Deploys take 10 minutes." in prompt
    assert "Deploys take 2 minutes." in prompt


# --- Report generation template ---


def test_build_report_prompt_reuses_format_context():
    builder = PromptBuilder()
    chunks = [ContextChunk(text="bottleneck details", source_name="report.txt", page_number=1)]
    prompt = builder.build_report_prompt(topic="Q3 bottlenecks", chunks=chunks)

    assert "Topic: Q3 bottlenecks" in prompt
    assert "[Source 1: report.txt, page 1] bottleneck details" in prompt
    assert "sections with headings" in prompt
