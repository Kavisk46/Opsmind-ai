import uuid
from dataclasses import dataclass

from core.tokens import estimate_token_count
from services.reranking_service import RankedChunk

_NO_CONTEXT_TEXT = "(No relevant context was found in the user's documents.)"


@dataclass
class AssembledContext:
    text: str
    source_document_ids: list[uuid.UUID]
    chunk_ids: list[tuple[uuid.UUID, int]]


def _empty_context() -> AssembledContext:
    return AssembledContext(text=_NO_CONTEXT_TEXT, source_document_ids=[], chunk_ids=[])


class ContextService:
    """Assembles retrieved, reranked chunks into one LLM-ready context
    string. Deliberately separate from PromptBuilder.format_context()
    (services/prompt_builder.py), which stays exactly as it is for chat —
    that method only labels and joins; this one additionally enforces a
    token budget and deduplicates paragraphs, neither of which chat's
    existing path does today (see this phase's Change Summary for why
    that's a deliberate choice, not an oversight).
    """

    def assemble(
        self, chunks: list[RankedChunk], *, max_context_tokens: int
    ) -> AssembledContext:
        if not chunks:
            return _empty_context()

        ordered_chunks = self._order_by_document_then_chunk_index(chunks)

        seen_paragraphs: set[str] = set()
        parts: list[str] = []
        chunk_ids: list[tuple[uuid.UUID, int]] = []
        source_document_ids: list[uuid.UUID] = []
        tokens_remaining = max_context_tokens

        for chunk in ordered_chunks:
            kept_text = self._dedupe_paragraphs(chunk.text, seen_paragraphs)
            if not kept_text:
                # Every paragraph in this chunk was a duplicate of one
                # already included — nothing new to add, and nothing to
                # count against the token budget either.
                continue

            estimated_tokens = estimate_token_count(kept_text)
            if parts and estimated_tokens > tokens_remaining:
                # Budget exhausted. Stopping here (not truncating THIS
                # chunk's text to fit) is deliberate — chunks are already
                # ordered by relevance, so cutting off the tail is a
                # meaningful trade-off; emitting half a chunk would hand
                # the model a garbled fragment instead, and "preserve
                # chunk order" — this phase's own requirement — implies
                # a chunk is included whole or not at all.
                break

            parts.append(self._format_chunk(chunk, kept_text, source_number=len(chunk_ids) + 1))
            chunk_ids.append((chunk.document_id, chunk.chunk_index))
            if chunk.document_id not in source_document_ids:
                source_document_ids.append(chunk.document_id)
            tokens_remaining -= estimated_tokens

        if not parts:
            return _empty_context()

        return AssembledContext(
            text="\n\n".join(parts),
            source_document_ids=source_document_ids,
            chunk_ids=chunk_ids,
        )

    @staticmethod
    def _order_by_document_then_chunk_index(
        chunks: list[RankedChunk],
    ) -> list[RankedChunk]:
        """Preserves DOCUMENT order (whichever document's best chunk
        ranked highest appears first) and CHUNK order (within one
        document, chunks appear in their original chunk_index order, not
        reranked order) — a document's own internal narrative shouldn't
        be scrambled just because chunk 5 happened to score higher than
        chunk 2.
        """
        first_seen_order: list[uuid.UUID] = []
        grouped: dict[uuid.UUID, list[RankedChunk]] = {}
        for chunk in chunks:
            if chunk.document_id not in grouped:
                grouped[chunk.document_id] = []
                first_seen_order.append(chunk.document_id)
            grouped[chunk.document_id].append(chunk)

        for document_id in first_seen_order:
            grouped[document_id].sort(key=lambda c: c.chunk_index)

        return [chunk for document_id in first_seen_order for chunk in grouped[document_id]]

    @staticmethod
    def _dedupe_paragraphs(text: str, seen_paragraphs: set[str]) -> str:
        kept = []
        for paragraph in text.split("\n\n"):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            # Normalized (lowercased, whitespace-collapsed) purely for
            # the seen-check — the ORIGINAL paragraph text (case,
            # spacing) is what actually gets kept and returned.
            normalized = " ".join(paragraph.lower().split())
            if normalized in seen_paragraphs:
                continue
            seen_paragraphs.add(normalized)
            kept.append(paragraph)
        return "\n\n".join(kept)

    @staticmethod
    def _format_chunk(chunk: RankedChunk, text: str, *, source_number: int) -> str:
        label = f"Source {source_number}"
        if chunk.filename:
            label += f": {chunk.filename}"
            if chunk.page_number is not None:
                label += f", page {chunk.page_number}"
        return f"[{label}] {text}"
