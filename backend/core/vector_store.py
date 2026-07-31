import chromadb

# ChromaDB's default distance metric is squared L2, not cosine — fine for
# some use cases, but cosine is the metric embedding models like
# all-MiniLM-L6-v2 are actually trained/evaluated against (it's what the
# semantic-similarity numbers from the ingestion-phase verification script
# were computed with). Configuring it explicitly at collection-creation
# time, rather than accepting the implicit default, is what makes
# retrieval's similarity scores meaningfully comparable to that earlier
# verification.
_COLLECTION_METADATA = {"hnsw:space": "cosine"}

# ChromaDB metadata values must be str/int/float/bool — None isn't
# allowed. -1 is an explicit sentinel for "no page number" (plain text/
# Markdown documents), translated back to None the moment it leaves this
# module (see query()'s return value) so nothing outside core/ needs to
# know this workaround exists.
_NO_PAGE_NUMBER = -1


class VectorStoreUnavailableError(Exception):
    """Raised when the underlying ChromaDB collection itself can't be
    read from or written to — a corrupted local index, a disk I/O
    failure, permission denied on persist_dir, and similar. Wraps
    whatever chromadb's client raised so every caller (IngestionService,
    RetrievalService) can catch ONE clean, purpose-built exception
    instead of needing to know chromadb's own internal exception types.

    Deliberately does NOT wrap the whole of add_chunks()/query()/
    delete_by_document() — only the actual chromadb client calls inside
    them. A bug in THIS class's own translation logic (e.g. the
    strict=True zip() in query() below) is a different kind of failure
    than "the vector store is unavailable," and should surface as
    exactly what it is, not get relabeled as unavailability.
    """


class VectorStore:
    """Wraps a ChromaDB persistent (embedded) client — a real vector
    database, just running in-process and writing to local disk, the
    same relationship SQLite has to a full database server. No Docker
    service, no network connection: `chromadb.PersistentClient` opens (or
    creates) an index rooted at `persist_dir` the same way `LocalStorage`
    opens a directory. Swapping this for a hosted Chroma server, or a
    different vector database entirely, later means rewriting this one
    class — nothing that calls it changes.
    """

    def __init__(self, persist_dir: str):
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._collection = self._client.get_or_create_collection(
            "documents", metadata=_COLLECTION_METADATA
        )

    def add_chunks(
        self,
        *,
        document_id: str,
        owner_id: str,
        chunks: list[str],
        embeddings: list[list[float]],
        page_numbers: list[int | None] | None = None,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> None:
        # IDs must be unique within the collection — "<document_id>:<index>"
        # is what lets re-processing the same document correctly REPLACE
        # its old chunk 0 instead of accumulating a duplicate — but only
        # because this calls upsert(), not add(). add()'s own docstring
        # says it raises ValueError if an ID already exists (or, as
        # verified directly while writing tests/test_vector_store.py,
        # this chromadb version silently keeps the OLD document text
        # instead of raising) — either way, a real bug this phase's
        # testing found: re-ingesting a document would have left stale
        # chunk content permanently searchable. upsert() is the method
        # that actually provides insert-or-replace semantics.
        # owner_id is stored as metadata specifically so retrieve()/query()
        # can filter to "only this user's documents" without a separate
        # per-user collection.
        if page_numbers is None:
            page_numbers = [None] * len(chunks)

        ids = [f"{document_id}:{i}" for i in range(len(chunks))]
        metadatas = []
        for i in range(len(chunks)):
            page_number = page_numbers[i]
            metadata: dict[str, str | int] = {
                "document_id": document_id,
                "owner_id": owner_id,
                "chunk_index": i,
                "page_number": page_number if page_number is not None else _NO_PAGE_NUMBER,
            }
            # Omitted entirely (not stored as a sentinel like page_number
            # above) when not supplied — every real caller (IngestionService)
            # always has both, so None here only happens in tests that
            # don't care about these two fields.
            if filename is not None:
                metadata["filename"] = filename
            if content_type is not None:
                metadata["content_type"] = content_type
            metadatas.append(metadata)

        try:
            # chromadb's stubs declare `embeddings`/`metadatas` in terms of
            # numpy ndarray types more specific than the plain Python
            # list[list[float]]/list[dict] this method actually passes; at
            # runtime the client accepts plain lists directly (proven by this
            # project's own real, passing tests against a real embedded
            # ChromaDB — see tests/test_vector_store.py). The stub being
            # stricter than the library actually is, not a bug here — hence
            # the ignore on the specific line mypy flags below.
            self._collection.upsert(
                ids=ids,
                embeddings=embeddings,  # type: ignore[arg-type]
                documents=chunks,
                metadatas=metadatas,  # type: ignore[arg-type]
            )
        except Exception as error:
            raise VectorStoreUnavailableError(str(error)) from error

    def query(
        self, *, query_embedding: list[float], owner_id: str, top_k: int
    ) -> list[dict]:
        """Returns the top_k chunks, across ALL of owner_id's documents,
        closest to query_embedding — scoped via the `where` filter to the
        owner_id metadata every chunk was tagged with in add_chunks. This
        is retrieval's entire job: no LLM, no prompt construction, just
        "which stored chunks are most semantically similar to this
        vector," which is exactly what RetrievalService calls this for.
        """
        try:
            # Same stub-vs-reality gap as upsert() above — query_embeddings
            # accepts a plain list[list[float]] at runtime.
            results = self._collection.query(
                query_embeddings=[query_embedding],  # type: ignore[arg-type]
                n_results=top_k,
                where={"owner_id": owner_id},
            )
        except Exception as error:
            raise VectorStoreUnavailableError(str(error)) from error

        chunks = []
        # Each indexed field's stub type is Optional (the Chroma API can
        # be asked to omit any of them) — in practice these three are
        # always populated since none of them were explicitly excluded
        # above, so the stub is being more cautious than this specific,
        # fixed call actually needs to account for.
        documents = results["documents"][0]  # type: ignore[index]
        metadatas = results["metadatas"][0]  # type: ignore[index]
        distances = results["distances"][0]  # type: ignore[index]
        # strict=True: these three lists all come from the same Chroma
        # query result, one entry per returned match — they should always
        # be the same length. Making that assumption explicit means a
        # future Chroma API change that ever violated it would raise
        # loudly here, not silently truncate to the shortest list.
        for text, metadata, distance in zip(documents, metadatas, distances, strict=True):
            page_number = metadata.get("page_number", _NO_PAGE_NUMBER)
            chunks.append(
                {
                    "text": text,
                    "document_id": metadata["document_id"],
                    "chunk_index": metadata["chunk_index"],
                    "page_number": (
                        None if page_number == _NO_PAGE_NUMBER else page_number
                    ),
                    # With hnsw:space="cosine", Chroma's returned "distance"
                    # is 1 - cosine_similarity — converting back to
                    # similarity here means every caller works with
                    # "higher = more similar", the intuitive direction,
                    # rather than remembering which way distance runs.
                    "similarity_score": 1 - distance,
                    # None for any chunk indexed before filename/content_type
                    # were added to metadata, or for tests that never
                    # supplied them to add_chunks() — not every caller of
                    # this dict needs these two fields.
                    "filename": metadata.get("filename"),
                    "content_type": metadata.get("content_type"),
                }
            )
        return chunks

    def delete_by_document(self, *, document_id: str) -> None:
        try:
            self._collection.delete(where={"document_id": document_id})
        except Exception as error:
            raise VectorStoreUnavailableError(str(error)) from error

    def count(self) -> int:
        # Test/verification convenience — not used by the ingestion
        # pipeline itself.
        return self._collection.count()
