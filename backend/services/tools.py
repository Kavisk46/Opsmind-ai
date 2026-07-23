import uuid
from dataclasses import dataclass, field
from typing import Protocol

from repositories.document_repository import DocumentRepository
from services.prompt_builder import ContextChunk, PromptBuilder
from services.retrieval_service import RetrievalService


@dataclass
class Citation:
    """A fully-resolved citation — document_name is looked up from
    Postgres, so the caller never has to make a second round trip to know
    what to display. Only RAGRetrievalTool ever populates these;
    DocumentMetadataTool's answers aren't chunk-grounded in the same way.
    """

    document_id: uuid.UUID
    document_name: str
    chunk_index: int
    page_number: int | None


@dataclass
class RetrievalMetadata:
    """Lightweight retrieval-EVALUATION metadata — how many chunks came
    back and how confident the vector search was in each, for
    AIOrchestrator to hand to AIMetricsService.record_retrieval() (see
    services/ai_metrics_service.py). Populated only by tools that
    actually perform semantic retrieval (RAGRetrievalTool below);
    DocumentMetadataTool leaves ToolResult.retrieval_metadata as None —
    "how many documents do you have" runs a real Postgres query, but
    there's no similarity search, and therefore no retrieval quality, to
    evaluate.
    """

    chunk_count: int
    confidence_scores: list[float]


@dataclass
class ToolResult:
    """What every tool hands back to the orchestrator — deliberately the
    SAME shape regardless of which tool produced it. `output_text` is
    already formatted, ready to drop straight into a prompt as "Context"
    — formatting is the tool's job, not PromptBuilder's, which is what
    lets PromptBuilder stay tool-agnostic (see its docstring).
    """

    tool_name: str
    success: bool
    output_text: str
    citations: list[Citation] = field(default_factory=list)
    error: str | None = None
    retrieval_metadata: RetrievalMetadata | None = None


class Tool(Protocol):
    """The shape any tool must provide. The orchestrator depends on this,
    never on a concrete tool — adding a third tool later means writing
    one new class with a run() method and registering it; the
    orchestrator's routing/execution code never changes (see
    ToolRegistry).
    """

    name: str

    async def run(self, *, query: str, owner_id: uuid.UUID) -> ToolResult: ...


class RAGRetrievalTool:
    """Wraps RetrievalService (embed query, search ChromaDB) and formats
    the result as prompt-ready text plus resolved citations. RetrievalService
    itself stays exactly as it was — this is an adapter on top of it, not
    a replacement; a future non-chat feature (e.g. a standalone "search my
    documents" endpoint) can still use RetrievalService directly without
    going through this Tool wrapper at all.
    """

    name = "rag_retrieval"

    def __init__(
        self,
        retrieval_service: RetrievalService,
        document_repository: DocumentRepository,
        top_k: int,
    ):
        self.retrieval_service = retrieval_service
        self.document_repository = document_repository
        self.top_k = top_k

    async def run(self, *, query: str, owner_id: uuid.UUID) -> ToolResult:
        chunks = self.retrieval_service.retrieve(
            query=query, owner_id=owner_id, top_k=self.top_k
        )

        # One DocumentRepository.get_by_id() call per chunk — a real N+1
        # query pattern, deliberately not optimized away with a batched
        # IN-query. At a small top_k this is at most a handful of extra
        # lookups per question; worth revisiting only if top_k grows large
        # enough for that cost to actually show up in a profiler. The
        # SAME lookup feeds both the citation (for the API response) and
        # the ContextChunk (for the prompt) — one document fetch, two uses.
        context_chunks: list[ContextChunk] = []
        citations: list[Citation] = []
        for chunk in chunks:
            document = await self.document_repository.get_by_id(chunk.document_id)
            document_name = document.filename if document else "(deleted document)"

            context_chunks.append(
                ContextChunk(
                    text=chunk.text,
                    source_name=document_name,
                    page_number=chunk.page_number,
                )
            )
            citations.append(
                Citation(
                    document_id=chunk.document_id,
                    document_name=document_name,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                )
            )

        # format_context() lives on PromptBuilder (services/prompt_builder.py)
        # — this tool doesn't build its own "[Source N]"-style text, it
        # calls the one shared formatter every context-producing tool
        # uses, now enriched with document name + page number so a
        # citation instruction in the prompt has something concrete to
        # reference.
        output_text = PromptBuilder.format_context(context_chunks)

        return ToolResult(
            tool_name=self.name,
            success=True,
            output_text=output_text,
            citations=citations,
            retrieval_metadata=RetrievalMetadata(
                chunk_count=len(chunks),
                confidence_scores=[chunk.similarity_score for chunk in chunks],
            ),
        )


class DocumentMetadataTool:
    """Answers questions ABOUT a user's documents as a collection — count,
    filenames, upload status — none of which RAG can answer at all, since
    semantic search operates over document CONTENT, not document
    metadata. This is the concrete proof routing is needed: "how many
    documents have I uploaded" has no meaningful embedding to search for;
    it needs a real query against Postgres, which is exactly what this
    tool runs instead.
    """

    name = "document_metadata"

    def __init__(self, document_repository: DocumentRepository):
        self.document_repository = document_repository

    async def run(self, *, query: str, owner_id: uuid.UUID) -> ToolResult:
        documents = await self.document_repository.list_by_owner(owner_id)

        if not documents:
            output_text = "The user has not uploaded any documents yet."
        else:
            lines = [f"The user has {len(documents)} document(s):"]
            for document in documents:
                lines.append(
                    f"- {document.filename} (status: {document.status}, "
                    f"uploaded: {document.created_at.date()})"
                )
            output_text = "\n".join(lines)

        return ToolResult(tool_name=self.name, success=True, output_text=output_text)
