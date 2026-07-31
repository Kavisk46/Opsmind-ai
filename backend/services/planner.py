from dataclasses import dataclass
from typing import Literal

SearchStrategy = Literal["hybrid", "vector", "keyword"]

# Common lead-in phrasing that carries no retrieval signal of its own —
# stripped so the embedded/keyword-searched query is closer to the actual
# subject ("What is SOC2?" -> "SOC2") rather than diluted by words that
# match everything and nothing. Longest/most specific phrases first, so
# "what happened during incident 52" strips as one unit rather than
# matching a shorter, less specific prefix first.
_FILLER_PREFIXES = (
    "what happened during ",
    "what happened with ",
    "what happened to ",
    "what happened in ",
    "can you tell me about ",
    "tell me about ",
    "what is ",
    "what are ",
    "what was ",
    "what were ",
    "how does ",
    "how do ",
    "how did ",
    "who is ",
    "who are ",
    "explain ",
    "describe ",
)

# Present when a question is asking for a broad sweep of material rather
# than one fact — worth a wider net (higher top_k) than the default.
_DETAIL_KEYWORDS = (
    "incident",
    "history",
    "timeline",
    "detailed",
    "detail",
    "everything",
    "all of",
    "walk me through",
)

# Mirrors AIOrchestrator._route()'s existing keyword list (services/
# orchestrator.py) — deliberately the SAME words, not a second,
# independently-maintained list that could drift: both are answering the
# same underlying question, "is this asking about the document
# COLLECTION rather than document CONTENT."
_METADATA_KEYWORDS = (
    "how many document",
    "how many file",
    "list my document",
    "list documents",
    "which documents",
    "what documents",
    "document count",
    "when did i upload",
    "documents have i uploaded",
)

_DEFAULT_TOP_K = 5
_DETAILED_TOP_K = 8


@dataclass
class RetrievalPlan:
    """What the Planner decided about HOW to retrieve for one question —
    produced before any retrieval happens, consumed by AskService to
    parameterize its call into RetrievalService. Deliberately a plain,
    inert data holder: the Planner computes it, nothing about a
    RetrievalPlan itself does any work.
    """

    rewritten_query: str
    top_k: int
    search_strategy: SearchStrategy
    use_metadata: bool


class Planner:
    """Decides how to retrieve for a question, before any retrieval
    actually happens. Deliberately rule-based, not LLM-based: keyword
    heuristics need no live model call, add no latency or cost on top of
    the real answering call, and are fully deterministic to unit-test —
    the same reasoning AIOrchestrator._route() (services/orchestrator.py)
    already uses for its own, coarser "which tool" decision. This class
    answers a narrower question than that one: given that retrieval IS
    going to happen, how should it be tuned (query text, how many
    results, which search legs) — not whether to retrieve at all.

    search_strategy is always "hybrid" today — RetrievalService.
    retrieve_hybrid() (services/retrieval_service.py) always runs both
    the vector and keyword legs, and this phase's scope is explicitly
    "build the orchestration layer," not "modify retrieval internals."
    The field exists so a later phase can act on a genuinely different
    strategy per question without changing RetrievalPlan's shape again.
    """

    def plan(self, question: str) -> RetrievalPlan:
        normalized = question.strip().lower()

        return RetrievalPlan(
            rewritten_query=self._rewrite_query(question),
            top_k=self._choose_top_k(normalized),
            search_strategy="hybrid",
            use_metadata=any(keyword in normalized for keyword in _METADATA_KEYWORDS),
        )

    @staticmethod
    def _rewrite_query(question: str) -> str:
        stripped = question.strip()
        lowered = stripped.lower()
        for prefix in _FILLER_PREFIXES:
            if lowered.startswith(prefix):
                stripped = stripped[len(prefix) :]
                break
        rewritten = stripped.rstrip("?").strip()
        # A prefix strip that eats the ENTIRE question (a bare "What is?"
        # with nothing after it) would otherwise return an empty query —
        # falling back to the original, unstripped question is a more
        # useful thing to search for than nothing at all.
        return rewritten or question.strip()

    @staticmethod
    def _choose_top_k(normalized_question: str) -> int:
        if any(keyword in normalized_question for keyword in _DETAIL_KEYWORDS):
            return _DETAILED_TOP_K
        return _DEFAULT_TOP_K
