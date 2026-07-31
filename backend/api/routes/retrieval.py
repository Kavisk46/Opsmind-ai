from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import (
    get_ai_metrics_service,
    get_citation_service,
    get_context_service,
    get_current_user,
    get_query_service,
    get_retrieval_service,
)
from core.config import settings
from core.logging import logger
from core.tokens import estimate_token_count
from models.user import User
from schemas.retrieval import (
    CitationResponse,
    RetrievalSearchRequest,
    RetrievalSearchResponse,
    RetrievedChunkResponse,
)
from services.ai_metrics_service import AIMetricsService
from services.citation_service import CitationService
from services.context_service import ContextService
from services.query_service import EmptyQueryError, QueryService
from services.retrieval_service import RetrievalService

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.post("/search", response_model=RetrievalSearchResponse)
async def search(
    payload: RetrievalSearchRequest,
    current_user: User = Depends(get_current_user),
    query_service: QueryService = Depends(get_query_service),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    context_service: ContextService = Depends(get_context_service),
    citation_service: CitationService = Depends(get_citation_service),
    ai_metrics_service: AIMetricsService = Depends(get_ai_metrics_service),
):
    """Pure retrieval — query processing, hybrid vector+keyword search,
    reranking, context assembly, citation generation. Deliberately calls
    no LLM at all (see this phase's stop condition): the response is
    exactly what a generation step would be HANDED, not an answer.
    """
    try:
        processed_query = query_service.process(payload.question)
    except EmptyQueryError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Query must not be empty."
        ) from error

    top_k = payload.top_k or settings.retrieval_top_k
    chunks, timing = await retrieval_service.retrieve_hybrid(
        query=processed_query.text,
        owner_id=current_user.id,
        top_k=top_k,
        max_returned_chunks=settings.retrieval_max_returned_chunks,
    )
    assembled_context = context_service.assemble(
        chunks, max_context_tokens=settings.retrieval_max_context_tokens
    )
    citations = citation_service.build_citations(chunks)

    total_seconds = (
        timing.embedding_seconds
        + timing.vector_search_seconds
        + timing.keyword_search_seconds
        + timing.reranking_seconds
    )
    # Reuses AIMetricsService.record_retrieval() rather than inventing a
    # second, parallel metrics path — this endpoint is just another
    # caller of the same "how many chunks, how long, how confident" shape
    # RAGRetrievalTool already reports under tool_name="rag_retrieval";
    # this one reports under its own tool name so the two stay
    # distinguishable in Prometheus/logs.
    ai_metrics_service.record_retrieval(
        tool_name="retrieval_search",
        chunk_count=len(chunks),
        latency_seconds=total_seconds,
        confidence_scores=[chunk.combined_score for chunk in chunks],
    )
    logger.info(
        "Retrieval search complete: query=%r embedding=%.3fs vector_search=%.3fs "
        "keyword_search=%.3fs reranking=%.3fs context_size_tokens=%d chunks=%d "
        "total=%.3fs",
        processed_query.text,
        timing.embedding_seconds,
        timing.vector_search_seconds,
        timing.keyword_search_seconds,
        timing.reranking_seconds,
        estimate_token_count(assembled_context.text),
        len(chunks),
        total_seconds,
    )

    return {
        "context": assembled_context.text,
        "citations": [
            CitationResponse(
                document_id=citation.document_id,
                filename=citation.filename,
                chunk_index=citation.chunk_index,
                page_number=citation.page_number,
            )
            for citation in citations
        ],
        "chunks": [
            RetrievedChunkResponse(
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                filename=chunk.filename or "(unknown document)",
                text=chunk.text,
                vector_score=chunk.vector_score,
                keyword_score=chunk.keyword_score,
                combined_score=chunk.combined_score,
            )
            for chunk in chunks
        ],
    }
