import uuid
from dataclasses import dataclass

from core.embeddings import EmbeddingModel
from core.vector_store import VectorStore


@dataclass
class RetrievedChunk:
    """One chunk retrieval found relevant, plus enough metadata for a
    citation. Deliberately a plain dataclass, not a Pydantic schema —
    this is an internal, service-to-service data shape, never serialized
    directly to an HTTP response (ChatService/the chat route translate it
    into schemas/chat.py's CitationResponse for that).
    """

    document_id: uuid.UUID
    chunk_index: int
    page_number: int | None
    text: str
    similarity_score: float


class RetrievalService:
    """Embeds a query and searches ChromaDB for the most semantically
    similar chunks. Deliberately knows nothing about prompts or LLMs —
    ChatService composes this with PromptBuilder and an LLM, but this
    class is independently testable and independently reusable (a future
    "search my documents" feature, with no chat involved at all, could
    use this exact class unmodified).
    """

    def __init__(self, embedding_model: EmbeddingModel, vector_store: VectorStore):
        self.embedding_model = embedding_model
        self.vector_store = vector_store

    def retrieve(
        self, *, query: str, owner_id: uuid.UUID, top_k: int
    ) -> list[RetrievedChunk]:
        # embed() takes a list and returns a list (batching multiple
        # chunks at once during ingestion is what it's optimized for) —
        # a single query is just a batch of one, hence the [0].
        query_embedding = self.embedding_model.embed([query])[0]

        raw_results = self.vector_store.query(
            query_embedding=query_embedding,
            owner_id=str(owner_id),
            top_k=top_k,
        )

        return [
            RetrievedChunk(
                document_id=uuid.UUID(result["document_id"]),
                chunk_index=result["chunk_index"],
                page_number=result["page_number"],
                text=result["text"],
                similarity_score=result["similarity_score"],
            )
            for result in raw_results
        ]
