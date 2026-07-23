def chunk_text(text: str, *, chunk_size: int, overlap: int) -> list[str]:
    """Splits text into overlapping, fixed-size windows.

    Deliberately simple — character-count splitting, not sentence- or
    paragraph-aware. A more linguistically-informed splitter (respecting
    sentence boundaries, headings, etc.) is a real improvement worth
    making once retrieval quality is actually being measured against
    something; starting there before there's a way to evaluate "is this
    better" would be tuning blind.

    Overlap exists so an idea split across a chunk boundary still appears
    whole in at least one chunk: with chunk_size=1000, overlap=200, chunk
    2 starts 200 characters before chunk 1 ended, not immediately after it.
    """
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    step = chunk_size - overlap
    while start < len(text):
        chunks.append(text[start : start + chunk_size])
        start += step
    return chunks
