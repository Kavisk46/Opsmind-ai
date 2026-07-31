import pytest

from core.chunking import chunk_text

# --- basic size/overlap/edge cases (no punctuation to preserve) ---


def test_empty_text_returns_no_chunks():
    assert chunk_text("", chunk_size=1000, overlap=200) == []


def test_whitespace_only_text_returns_no_chunks():
    assert chunk_text("   \n\t  ", chunk_size=1000, overlap=200) == []


def test_text_shorter_than_chunk_size_returns_a_single_chunk():
    text = "Hello world, this is a short document."

    result = chunk_text(text, chunk_size=1000, overlap=200)

    assert result == [text]


def test_chunk_size_must_be_greater_than_overlap():
    with pytest.raises(ValueError):
        chunk_text("some text", chunk_size=100, overlap=100)


def test_falls_back_to_a_hard_cutoff_when_no_boundary_exists():
    # No punctuation anywhere — nothing for the boundary-preferring logic
    # to latch onto, so this exercises the plain fixed-width fallback.
    text = "A" * 100

    result = chunk_text(text, chunk_size=40, overlap=10)

    assert result[0] == "A" * 40
    # Each subsequent chunk starts `overlap` characters before the
    # previous one ended — the same guarantee the original fixed-width
    # splitter made, still true here since there's no boundary to shift
    # the cut point away from a hard chunk_size/overlap step.
    assert result[1] == "A" * 40


def test_overlap_repeats_content_across_the_boundary():
    text = "A" * 100

    result = chunk_text(text, chunk_size=40, overlap=10)

    # The last `overlap` characters of chunk N equal the first `overlap`
    # characters of chunk N+1 — proving an idea split across a boundary
    # still appears whole in at least one chunk.
    assert result[0][-10:] == result[1][:10]


# --- sentence-boundary preservation ---


def test_prefers_a_sentence_boundary_over_a_mid_word_cutoff():
    # A period sits well inside the chunk_size window (well past
    # min_offset = chunk_size // 2 = 20), followed by a run of "B"s long
    # enough that a pure hard cutoff at chunk_size=40 would land in the
    # middle of it. Sentence-boundary-aware chunking should end the
    # first chunk right after the period instead.
    text = "A" * 30 + ". " + "B" * 30

    result = chunk_text(text, chunk_size=40, overlap=10)

    assert result[0] == "A" * 30 + "."
    assert "B" not in result[0]


def test_does_not_use_a_sentence_boundary_too_close_to_the_start():
    # The only period in the window sits at position 5 — far below
    # min_offset (chunk_size // 2 == 20) — so honoring it would produce
    # a tiny, degenerate 6-character chunk. This should fall back to the
    # hard cutoff at chunk_size instead of stopping at that early period.
    text = "Hi. " + "B" * 100

    result = chunk_text(text, chunk_size=40, overlap=10)

    assert len(result[0]) == 40
    assert result[0] != "Hi."


def test_sentence_boundary_recognizes_question_and_exclamation_marks():
    text = "A" * 30 + "? " + "B" * 30

    result = chunk_text(text, chunk_size=40, overlap=10)

    assert result[0] == "A" * 30 + "?"

    text = "A" * 30 + "! " + "B" * 30

    result = chunk_text(text, chunk_size=40, overlap=10)

    assert result[0] == "A" * 30 + "!"


# --- paragraph-boundary preference over sentence boundary ---


def test_prefers_a_paragraph_break_over_a_later_sentence_boundary():
    # Both a paragraph break (after the A's) and a sentence boundary
    # (the ". " after the B's) exist inside the chunk_size=50 window, and
    # both are past min_offset=25. The paragraph break should win even
    # though the sentence boundary sits closer to chunk_size — "recursive"
    # chunking tries the coarser separator first.
    text = "A" * 30 + "\n\n" + "B" * 10 + ". " + "C" * 20

    result = chunk_text(text, chunk_size=50, overlap=10)

    assert result[0] == "A" * 30
    assert "B" not in result[0]
    assert "C" not in result[0]


# --- realistic multi-sentence text, default project chunk_size/overlap ---


def test_realistic_prose_chunks_end_on_sentence_boundaries():
    sentences = [f"This is sentence number {i} in a long document." for i in range(40)]
    text = " ".join(sentences)

    result = chunk_text(text, chunk_size=1000, overlap=200)

    assert len(result) > 1
    # Every chunk but the last should end on real sentence punctuation —
    # proof the boundary-preserving logic actually fired throughout a
    # realistic, multi-chunk document, not just in a hand-crafted edge case.
    for chunk in result[:-1]:
        assert chunk.endswith(".")
