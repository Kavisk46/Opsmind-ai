import uuid
from dataclasses import dataclass, field
from typing import Protocol

from repositories.document_repository import DocumentRepository
from repositories.user_repository import UserRepository
from services.citation_service import CitationService
from services.context_service import ContextService
from services.query_service import QueryService
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
    """Wraps the hybrid retrieval engine (QueryService -> RetrievalService.
    retrieve_hybrid -> ContextService -> CitationService) and adapts its
    output into this module's ToolResult/Citation shapes. Before this
    phase, chat used RetrievalService.retrieve() directly — plain vector
    search, no keyword leg, no reranking, no token-budgeted context
    assembly. Wiring chat through the SAME hybrid engine the standalone
    /retrieval/search endpoint already used is this phase's whole point:
    one retrieval pipeline, two callers (chat and that endpoint), not two
    independently-maintained ones.

    Needs no DocumentRepository of its own anymore — retrieve_hybrid()
    already resolves every returned chunk's filename before returning it
    (see RetrievalService's own docstring), so the N+1 citation-name
    lookup that used to live in THIS class is gone, not just moved.
    """

    name = "rag_retrieval"

    def __init__(
        self,
        retrieval_service: RetrievalService,
        query_service: QueryService,
        context_service: ContextService,
        citation_service: CitationService,
        *,
        top_k: int,
        max_returned_chunks: int,
        max_context_tokens: int,
    ):
        self.retrieval_service = retrieval_service
        self.query_service = query_service
        self.context_service = context_service
        self.citation_service = citation_service
        self.top_k = top_k
        self.max_returned_chunks = max_returned_chunks
        self.max_context_tokens = max_context_tokens

    async def run(self, *, query: str, owner_id: uuid.UUID) -> ToolResult:
        # query is already guaranteed non-empty here — ChatService.ask()/
        # ask_stream() reject an empty question before AIOrchestrator (and
        # therefore this tool) is ever reached — but QueryService.process()
        # still does real work beyond that guarantee: normalizing
        # whitespace before it reaches embedding/keyword search.
        processed_query = self.query_service.process(query)

        chunks, _timing = await self.retrieval_service.retrieve_hybrid(
            query=processed_query.text,
            owner_id=owner_id,
            top_k=self.top_k,
            max_returned_chunks=self.max_returned_chunks,
        )

        assembled_context = self.context_service.assemble(
            chunks, max_context_tokens=self.max_context_tokens
        )
        # CitationService's Citation has `filename`, not `document_name`
        # — adapted into THIS module's own Citation shape (which
        # schemas/chat.py's CitationResponse is built from) rather than
        # changing that public API's field name for this phase.
        citations = [
            Citation(
                document_id=citation.document_id,
                document_name=citation.filename,
                chunk_index=citation.chunk_index,
                page_number=citation.page_number,
            )
            for citation in self.citation_service.build_citations(chunks)
        ]

        return ToolResult(
            tool_name=self.name,
            success=True,
            output_text=assembled_context.text,
            citations=citations,
            retrieval_metadata=RetrievalMetadata(
                chunk_count=len(chunks),
                confidence_scores=[chunk.combined_score for chunk in chunks],
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

    def __init__(self, document_repository: DocumentRepository, user_repository: UserRepository):
        self.document_repository = document_repository
        self.user_repository = user_repository

    async def run(self, *, query: str, owner_id: uuid.UUID) -> ToolResult:
        # Stage 1 of the multi-workspace rollout (see
        # services/workspace_service.py) deliberately keeps chat/
        # AIOrchestrator owner_id-scoped, deferring a full workspace-aware
        # Tool protocol to Stage 2 — but DocumentRepository's read methods
        # were already re-scoped from owner_id to workspace_id (shared
        # workspace visibility), so there is no owner-scoped document
        # query left to call directly. Resolving the caller's own default
        # workspace here is the minimal bridge between the two: it keeps
        # this tool's answer scoped to what the current user can already
        # see everywhere else (their default workspace's documents),
        # without threading workspace_id through the whole tool pipeline.
        user = await self.user_repository.get_by_id(owner_id)
        documents = (
            await self.document_repository.list_by_workspace(user.default_workspace_id)
            if user is not None and user.default_workspace_id is not None
            else []
        )

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
