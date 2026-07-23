from dataclasses import dataclass

# Grounding/hallucination-prevention instructions, written ONCE and reused
# across every template below (chat, summarization, comparison, report) —
# the same three guardrails apply regardless of what task the model is
# doing: stay inside the given material, admit gaps instead of guessing,
# and cite which source a claim came from. Writing this four times, once
# per template, is exactly the duplication "avoid prompt duplication"
# warns against.
_GROUNDING_INSTRUCTIONS = (
    "Stay strictly grounded in the provided context — never invent "
    "information it doesn't support. If the context does not contain "
    "enough information to answer, say so plainly instead of guessing. "
    "When you use information from the context, reference it by its "
    "[Source N] label so the claim can be verified against its origin."
)

# Prompt versioning: each template's system instructions live in a dict
# keyed by version string, not hardcoded inline as one fixed constant.
# This is the entire mechanism — introducing a new version means adding a
# new key ("v2") without touching or losing "v1"; PromptBuilder is told
# which version to use per template via its constructor (defaulting to
# the current production version), so an experiment or a rollback is a
# one-argument change, never a rewrite of the prompt text itself.
_CHAT_SYSTEM_PROMPTS = {
    "v1": (
        "You are OpsMind, an assistant that answers questions about the "
        f"user's operational documents. {_GROUNDING_INSTRUCTIONS}"
    ),
    # A real second version, not a placeholder — proves the versioning
    # mechanism actually works (see tests/test_prompt_builder.py): a
    # noticeably different instruction, coexisting with v1, selectable at
    # construction time.
    "v2": (
        "You are OpsMind. Answer in at most 3 sentences, as concisely as "
        f"possible. {_GROUNDING_INSTRUCTIONS}"
    ),
}

_SUMMARIZATION_SYSTEM_PROMPTS = {
    "v1": (
        "You summarize operational documents concisely and accurately, "
        "capturing the key points a busy reader needs. "
        f"{_GROUNDING_INSTRUCTIONS} Do not add information not present in "
        "the document."
    ),
}

_COMPARISON_SYSTEM_PROMPTS = {
    "v1": (
        "You compare two operational documents, identifying concrete "
        f"similarities, differences, and gaps. {_GROUNDING_INSTRUCTIONS} "
        "If one document lacks information the other has, say so "
        "explicitly rather than inferring or assuming agreement."
    ),
}

_REPORT_SYSTEM_PROMPTS = {
    "v1": (
        "You generate a structured operational report from retrieved "
        "context, organized into clear sections with headings. "
        f"{_GROUNDING_INSTRUCTIONS}"
    ),
}


@dataclass
class ContextChunk:
    """Generic input to format_context() below — deliberately NOT
    RetrievedChunk (services/retrieval_service.py's RAG-specific shape).
    Any tool with some text plus an optional source name/page can format
    its output through this same, shared path, without PromptBuilder (or
    this dataclass) needing to know anything about ChromaDB, embeddings,
    or vector search.
    """

    text: str
    source_name: str | None = None
    page_number: int | None = None


class PromptBuilder:
    """Builds every prompt this project sends to an LLM — chat, document
    summarization, document comparison, and report generation — from a
    small set of reusable templates, not four independently-maintained
    prompt strings. Pure, side-effect-free: no I/O, no dependency on
    ChromaDB, the LLM, or the database, which is what makes every method
    here unit-testable with no real model, vector store, or conversation
    needed.
    """

    def __init__(
        self,
        *,
        chat_prompt_version: str = "v1",
        summarization_prompt_version: str = "v1",
        comparison_prompt_version: str = "v1",
        report_prompt_version: str = "v1",
        max_history_messages: int = 10,
    ):
        self.chat_prompt_version = chat_prompt_version
        self.summarization_prompt_version = summarization_prompt_version
        self.comparison_prompt_version = comparison_prompt_version
        self.report_prompt_version = report_prompt_version
        self.max_history_messages = max_history_messages

    @staticmethod
    def format_context(chunks: list[ContextChunk]) -> str:
        """Turns retrieved chunks into prompt-ready text, labeling each
        with its source and (if known) page number — e.g.
        "[Source 1: postmortem.pdf, page 3] ...". A static method, not
        tied to any prompt_version, because HOW a chunk is labeled isn't
        something that needs versioning independently of the template
        text around it; any tool with chunk-shaped data (RAGRetrievalTool
        today, any future one) calls this directly instead of
        duplicating "[Source N]"-style formatting itself.
        """
        if not chunks:
            # An explicit, honest placeholder — not an empty string. A
            # model told "Context:\n\n" with nothing after it is far more
            # likely to hallucinate an answer than one explicitly told no
            # relevant context was found, which is the entire point of
            # grounding an answer at all.
            return "(No relevant context was found in the user's documents.)"

        parts = []
        for i, chunk in enumerate(chunks):
            label = f"Source {i + 1}"
            if chunk.source_name:
                label += f": {chunk.source_name}"
                if chunk.page_number is not None:
                    label += f", page {chunk.page_number}"
            parts.append(f"[{label}] {chunk.text}")
        return "\n\n".join(parts)

    def _format_history(self, history: list[tuple[str, str]] | None) -> str | None:
        if not history:
            return None
        # Only the most recent max_history_messages turns — see
        # core/config.py's max_history_messages for why this is bounded
        # rather than unlimited. Keeps the last N, not the first N: the
        # most recent exchange is almost always the most relevant to a
        # follow-up question.
        trimmed = history[-self.max_history_messages :]
        return "\n".join(f"{role.capitalize()}: {content}" for role, content in trimmed)

    def build(
        self,
        *,
        question: str,
        context_text: str,
        history: list[tuple[str, str]] | None = None,
    ) -> str:
        """The chat template. Takes already-formatted `context_text`
        rather than raw chunks — this is what keeps PromptBuilder
        tool-agnostic: formatting chunk metadata happens once, in
        format_context() above (called by whichever tool has chunk
        data), not here. Three ingredients, always assembled in the same
        order — instructions, then context, then the question — because
        an instruction-tuned model follows a system-style instruction
        most reliably when it comes first, and answers a question most
        reliably when the question is the very last thing before it has
        to respond.
        """
        sections = [_CHAT_SYSTEM_PROMPTS[self.chat_prompt_version]]

        # Conversation memory: prior turns are included so a follow-up
        # question ("what about last month?") can be understood in
        # context — without this, every question would be answered as if
        # it were the first one ever asked in the conversation.
        history_text = self._format_history(history)
        if history_text:
            sections.append(f"Previous conversation:\n{history_text}")

        sections.append(f"Context:\n{context_text}")
        sections.append(f"Question: {question}\nAnswer:")

        return "\n\n".join(sections)

    def build_summarization_prompt(self, *, document_name: str, content: str) -> str:
        """Summarization template. Not wired into a live route yet — this
        phase built the prompt-construction piece; exposing it as an
        actual `POST /documents/{id}/summarize`-style feature is a
        separate, future decision (new schema, new route, new service
        orchestration), not something bundled into the prompt builder
        itself.
        """
        system = _SUMMARIZATION_SYSTEM_PROMPTS[self.summarization_prompt_version]
        return (
            f"{system}\n\n"
            f"Document: {document_name}\n\n"
            f"Content:\n{content}\n\n"
            f"Summary:"
        )

    def build_comparison_prompt(
        self,
        *,
        document_a_name: str,
        document_a_content: str,
        document_b_name: str,
        document_b_content: str,
    ) -> str:
        """Document comparison template — same "built, not yet wired to
        a route" scope as summarization above.
        """
        system = _COMPARISON_SYSTEM_PROMPTS[self.comparison_prompt_version]
        return (
            f"{system}\n\n"
            f"Document A ({document_a_name}):\n{document_a_content}\n\n"
            f"Document B ({document_b_name}):\n{document_b_content}\n\n"
            f"Comparison:"
        )

    def build_report_prompt(self, *, topic: str, chunks: list[ContextChunk]) -> str:
        """Report-generation template — retrieval-shaped like chat (a
        topic plus supporting chunks) but framed as producing a
        structured, multi-section document rather than answering one
        question. Reuses format_context() rather than re-implementing
        chunk formatting a third time.
        """
        system = _REPORT_SYSTEM_PROMPTS[self.report_prompt_version]
        context_text = self.format_context(chunks)
        return (
            f"{system}\n\n"
            f"Topic: {topic}\n\n"
            f"Context:\n{context_text}\n\n"
            f"Report (organize your answer into clear sections with headings):"
        )
