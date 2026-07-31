from dataclasses import dataclass

from core.tokens import estimate_token_count


class EmptyQueryError(Exception):
    """Raised when a query is empty, or becomes empty once whitespace is
    trimmed/collapsed — e.g. a query that was only spaces/newlines. Never
    worth embedding or searching for.
    """


@dataclass
class ProcessedQuery:
    text: str
    estimated_token_count: int


class QueryService:
    """The entry point for a retrieval request's raw question — normalizes
    it, rejects anything empty, and estimates its size. Deliberately
    minimal: query REWRITING, spell correction, and language detection are
    real, separate features this class is structured to grow into later
    (each would slot in as another step inside process(), before the
    returned ProcessedQuery is built) — not implemented here, since none
    of them have a concrete requirement driving them yet.
    """

    def process(self, raw_query: str) -> ProcessedQuery:
        # Collapses ALL whitespace runs (spaces, tabs, newlines) to single
        # spaces, not just a leading/trailing strip() — a query pasted
        # from another document can carry internal line breaks/extra
        # spaces that mean nothing to an embedding model but would
        # otherwise flow straight into it unchanged.
        normalized = " ".join(raw_query.split())
        if not normalized:
            raise EmptyQueryError("Query must not be empty.")

        return ProcessedQuery(
            text=normalized,
            estimated_token_count=estimate_token_count(normalized),
        )
