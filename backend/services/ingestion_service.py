import time
import uuid

from sqlalchemy.ext.asyncio import async_sessionmaker

from core.chunking import chunk_text
from core.embeddings import EmbeddingModel
from core.logging import logger
from core.metrics import INGESTION_DURATION_SECONDS
from core.storage import Storage
from core.text_extraction import SUPPORTED_CONTENT_TYPES, clean_text, extract_text
from core.tokens import estimate_token_count
from core.vector_store import VectorStore
from models.document import DocumentStatus
from repositories.chunk_repository import ChunkRepository
from repositories.document_repository import DocumentRepository

# Truncated before being stored/returned to a client — an unhandled
# exception's full message (or a corrupt file's raw error text) could in
# principle contain something long or awkward; a short, bounded reason is
# all a status endpoint needs to show a user anyway.
_MAX_ERROR_MESSAGE_LENGTH = 500


class IngestionService:
    """Turns an already-uploaded document into searchable vectors:
    extract text -> chunk -> embed -> store -> update status.

    Unlike every other service in this codebase, this one is constructed
    with a session FACTORY, not a live session — and it commits its own
    transactions internally (normally get_db()'s job, never a service's).
    Both are deliberate exceptions, for the same reason: this runs as a
    FastAPI BackgroundTask, which executes AFTER the request that
    triggered it has already returned its response. It has no enclosing
    per-request get_db() to delegate transaction ownership to — something
    has to play that role, and here it's this service, explicitly.

    It also needs its status transitions committed as SEPARATE
    transactions, not bundled into one: PROCESSING, then EMBEDDING, then
    the final READY/FAILED, each committed the moment it's set — so a
    client polling GET /documents/{id}/status mid-run actually sees which
    real stage it's in, not just "uploaded" followed by a sudden final
    result with nothing observable in between.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker,
        storage: Storage,
        embedding_model: EmbeddingModel,
        vector_store: VectorStore,
        chunk_size: int,
        chunk_overlap: int,
        embedding_model_name: str,
    ):
        self.session_factory = session_factory
        self.storage = storage
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # Recorded onto every DocumentChunk row this run writes (see
        # _store_chunks) — a separate value from whatever `embedding_model`
        # itself is, because a Protocol-typed dependency (see
        # core/embeddings.py) has no obligation to expose its own name;
        # the caller that built it already knows.
        self.embedding_model_name = embedding_model_name

    async def process_document(self, document_id: uuid.UUID) -> None:
        start_time = time.perf_counter()
        document = await self._set_status(document_id, DocumentStatus.PROCESSING)
        if document is None:
            # Deleted before processing ever started — a real, normal
            # outcome (see the class docstring), recorded under its own
            # label rather than silently skipping the metric or lumping
            # it in with "success."
            INGESTION_DURATION_SECONDS.labels(outcome="deleted_before_processing").observe(
                time.perf_counter() - start_time
            )
            return

        if document.content_type not in SUPPORTED_CONTENT_TYPES:
            # A valid upload (see DocumentService.ACCEPTED_UPLOAD_CONTENT_TYPES)
            # whose type this pipeline simply has no text-extraction path
            # for — a PNG screenshot, a DOCX, a CSV export. That's an
            # expected, non-error outcome: the file is fully stored and
            # available for download/preview, it just never becomes part
            # of the searchable knowledge base. Marking it READY (not
            # FAILED) keeps "can't extract text from this format" and
            # "something actually went wrong" as two honestly distinct
            # states, instead of showing an alarming failure badge on a
            # file that uploaded correctly.
            await self._set_status(document_id, DocumentStatus.READY)
            INGESTION_DURATION_SECONDS.labels(outcome="not_extractable").observe(
                time.perf_counter() - start_time
            )
            return

        try:
            data = self.storage.open(key=document.storage_key)
            pages = extract_text(content_type=document.content_type, data=data)

            # Chunked PER PAGE, not on one joined string — overlap never
            # crosses a page boundary this way (a defensible simplification:
            # ideas rarely need to span pages the way they span internal
            # chunk boundaries), and each resulting chunk carries the exact
            # page it came from, which is what makes page-number citations
            # possible. chunk_index below is global across the whole
            # document (position in the final flat list), not reset per
            # page — that's what lets a citation's chunk_index alone
            # unambiguously identify one chunk of one document.
            chunks: list[str] = []
            page_numbers: list[int | None] = []
            for page_number, page_text in pages:
                page_chunks = chunk_text(
                    clean_text(page_text),
                    chunk_size=self.chunk_size,
                    overlap=self.chunk_overlap,
                )
                chunks.extend(page_chunks)
                page_numbers.extend([page_number] * len(page_chunks))

            embedding_duration = 0.0
            indexing_duration = 0.0
            if chunks:
                # EMBEDDING committed as its own transaction, same reasoning
                # as PROCESSING above — running the actual model is the
                # measurably slowest step in this pipeline (verified
                # directly in the RAG phase: real embedding/generation runs
                # took real, observable time), so it's the one stage most
                # worth a client being able to see they're specifically
                # waiting on, rather than an undifferentiated "processing."
                await self._set_status(document_id, DocumentStatus.EMBEDDING)

                embedding_start = time.perf_counter()
                embeddings = self.embedding_model.embed(chunks)
                embedding_duration = time.perf_counter() - embedding_start

                indexing_start = time.perf_counter()
                self.vector_store.add_chunks(
                    document_id=str(document.id),
                    owner_id=str(document.owner_id),
                    chunks=chunks,
                    embeddings=embeddings,
                    page_numbers=page_numbers,
                    filename=document.filename,
                    content_type=document.content_type,
                )
                await self._store_chunks(
                    document_id=document.id,
                    owner_id=document.owner_id,
                    chunks=chunks,
                )
                indexing_duration = time.perf_counter() - indexing_start

            await self._set_status(document_id, DocumentStatus.READY)
            total_duration = time.perf_counter() - start_time
            logger.info(
                "Ingestion complete for document %s (owner %s): %d chunks, "
                "embedding=%.3fs, indexing=%.3fs, total=%.3fs",
                document_id,
                document.owner_id,
                len(chunks),
                embedding_duration,
                indexing_duration,
                total_duration,
            )
            INGESTION_DURATION_SECONDS.labels(outcome="success").observe(total_duration)
        except Exception as error:
            # Deliberately catches everything: a corrupt PDF, a storage
            # read failure, an embedding model error — all of them mean
            # the same thing from this document's point of view:
            # processing didn't succeed, and it should be marked FAILED
            # rather than left stuck on PROCESSING/EMBEDDING forever.
            #
            # Logged here, with the document_id for correlation, BEFORE
            # re-raising — this is the actual point of this phase's
            # "observability" requirement: a background task's exception
            # has no HTTP response to surface it to anyone; if this
            # service doesn't log it, the failure is only ever visible as
            # a status flip in the database, with no record of WHY.
            logger.error(
                "Ingestion failed for document %s: %s", document_id, error
            )
            await self._set_status(
                document_id,
                DocumentStatus.FAILED,
                error_message=str(error)[:_MAX_ERROR_MESSAGE_LENGTH],
            )
            INGESTION_DURATION_SECONDS.labels(outcome="failed").observe(
                time.perf_counter() - start_time
            )
            raise

    async def _set_status(
        self,
        document_id: uuid.UUID,
        status: DocumentStatus,
        *,
        error_message: str | None = None,
    ):
        async with self.session_factory() as session:
            repository = DocumentRepository(session)
            document = await repository.get_by_id(document_id)
            if document is None:
                return None
            await repository.update(
                document, status=status.value, error_message=error_message
            )
            await session.commit()
            return document

    async def _store_chunks(
        self,
        *,
        document_id: uuid.UUID,
        owner_id: uuid.UUID,
        chunks: list[str],
    ) -> None:
        """Mirrors `chunks` into Postgres (see repositories/chunk_repository.py)
        — a separate transaction from _set_status, same reasoning as every
        other step in this pipeline: this service manages its own
        transactions throughout, never borrowing one from a caller.

        replace_for_document (not a plain insert) is what makes this
        idempotent: reprocessing the same document_id always leaves
        Postgres holding exactly this run's chunks, never a duplicate or
        stale set.
        """
        async with self.session_factory() as session:
            repository = ChunkRepository(session)
            await repository.replace_for_document(
                document_id=document_id,
                owner_id=owner_id,
                chunks=[
                    {
                        "chunk_index": index,
                        "text": text,
                        "token_count": estimate_token_count(text),
                        "embedding_model": self.embedding_model_name,
                    }
                    for index, text in enumerate(chunks)
                ],
            )
            await session.commit()
