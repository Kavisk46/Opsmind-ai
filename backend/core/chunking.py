import re

# Tried in priority order when deciding where a chunk should END, the
# same "recursive" idea LangChain's RecursiveCharacterTextSplitter uses:
# prefer a bigger structural break (a paragraph) over a smaller one (a
# sentence) over no break at all (a hard character cutoff). Both are
# searched for from the END of the chunk_size window backward, so a
# chunk stays as close to chunk_size as possible while still ending on a
# real boundary rather than mid-word.
_PARAGRAPH_BREAK_RE = re.compile(r"\n\s*\n")
_SENTENCE_END_RE = re.compile(r"[.!?][\"')\]]?(?:\s+|$)")


def _last_match_end(pattern: re.Pattern[str], window: str, min_offset: int) -> int | None:
    """The end offset of the LAST match of `pattern` in `window` that
    isn't so early it would produce a degenerate, tiny chunk — a period
    at position 3 of an 800-character window is a real sentence boundary,
    but ending the chunk there instead of near position 800 would defeat
    the point of chunk_size entirely.
    """
    last = None
    for match in pattern.finditer(window):
        if match.end() >= min_offset:
            last = match.end()
    return last


def _find_chunk_end(text: str, start: int, chunk_size: int) -> int:
    """Where this chunk should end: a paragraph break if one exists in
    the window, else a sentence boundary, else a hard cutoff at
    start + chunk_size. `min_offset` (half the window) keeps whichever
    boundary is chosen from being so close to `start` that the chunk
    ends up far smaller than chunk_size for no good reason.
    """
    hard_end = min(start + chunk_size, len(text))
    if hard_end >= len(text):
        return len(text)

    window = text[start:hard_end]
    min_offset = chunk_size // 2

    boundary = _last_match_end(_PARAGRAPH_BREAK_RE, window, min_offset)
    if boundary is None:
        boundary = _last_match_end(_SENTENCE_END_RE, window, min_offset)
    return start + boundary if boundary is not None else hard_end


def chunk_text(text: str, *, chunk_size: int, overlap: int) -> list[str]:
    """Splits text into overlapping windows of roughly chunk_size
    characters, preferring to end each chunk on a paragraph or sentence
    boundary rather than mid-word — "recursive" in the same sense as
    LangChain's RecursiveCharacterTextSplitter: try a coarser separator
    (paragraph) first, fall back to a finer one (sentence), and fall back
    to a hard character cutoff only when neither exists nearby. This is
    "whenever possible," not guaranteed — a wall of text with no
    punctuation still gets a hard cutoff, exactly like before.

    Overlap exists so an idea split across a chunk boundary still appears
    whole in at least one chunk: with chunk_size=1000, overlap=200, chunk
    2 starts 200 characters before chunk 1 ended, not immediately after
    it — the same guarantee as the original fixed-width splitter, just
    measured from wherever the boundary-aware end actually landed rather
    than from a fixed offset.
    """
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = _find_chunk_end(text, start, chunk_size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        # Guards against zero/negative progress: a boundary landing very
        # close to `start` (allowed by min_offset, but still possible)
        # could otherwise make `end - overlap` <= start, looping forever
        # on the same position. Falling back to `end` (no overlap this
        # one time) guarantees start always strictly advances.
        next_start = end - overlap
        start = next_start if next_start > start else end
    return chunks
