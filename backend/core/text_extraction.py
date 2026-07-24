import io

from pypdf import PdfReader

# The single source of truth for "what file types can this pipeline
# actually do anything with" — imported by services/document_service.py
# to reject an unsupported upload immediately (400), not just here,
# where it would otherwise only be discovered during background
# ingestion (see IngestionService.process_document), after the file has
# already been accepted, stored, and the client told 202. One constant,
# not two independently-maintained lists that could drift apart.
SUPPORTED_CONTENT_TYPES = frozenset({"text/plain", "text/markdown", "application/pdf"})


class UnsupportedContentTypeError(Exception):
    """Raised when a document's content_type has no known text-extraction
    path. Caught by the ingestion service and turned into
    DocumentStatus.FAILED — an unsupported file type is an expected,
    recoverable condition (the upload itself already succeeded), not a
    bug.
    """


def extract_text(*, content_type: str, data: bytes) -> list[tuple[int | None, str]]:
    """Pulls plain text out of raw file bytes, keeping PAGE BOUNDARIES
    intact — returns a list of (page_number, text) pairs rather than one
    joined string. This is what lets a citation later say "page 3" and
    mean it: once text from every page is joined into a single string
    (the old behavior), there is no way to recover which page any given
    chunk came from.

    page_number is 1-indexed for formats that have real pages (PDF), and
    None for formats that don't (plain text, Markdown) — a citation with
    no page number is the correct, honest answer for those formats, not
    a bug to work around.
    """
    if content_type in ("text/plain", "text/markdown"):
        return [(None, data.decode("utf-8", errors="replace"))]

    if content_type == "application/pdf":
        reader = PdfReader(io.BytesIO(data))
        return [
            (page_index + 1, page.extract_text() or "")
            for page_index, page in enumerate(reader.pages)
        ]

    raise UnsupportedContentTypeError(content_type)


def clean_text(text: str) -> str:
    """Light normalization applied after extraction, before chunking.
    Strips null bytes (which occasionally leak out of a malformed PDF's
    extracted text and would otherwise flow into the embedding model) and
    collapses blank/whitespace-only lines.

    Deliberately NOT a markdown/HTML stripper — removing `#`/`**`/link
    syntax would need a real parser, and embedding models are reasonably
    robust to a bit of leftover markdown syntax in the input. Adding that
    complexity isn't justified by anything measured yet; it's the kind of
    premature optimization worth avoiding until retrieval quality is
    actually being evaluated against something.
    """
    text = text.replace("\x00", "")
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)
