"""Text chunking for Module 1.

The report asks for chunks of ~300 tokens with 15% overlap. A real tokenizer would
add a heavy dependency for no retrieval benefit, so we budget in whitespace words
and convert with a fixed English ratio (~1.33 sub-word tokens per word).
"""

TOKENS_PER_WORD = 1.33


def words_per_chunk(chunk_tokens: int) -> int:
    return max(1, int(round(chunk_tokens / TOKENS_PER_WORD)))


def chunk_table(text: str, chunk_tokens: int = 300) -> list[str]:
    """Split a markdown table by rows, repeating the caption and header in every chunk.

    Splitting a table by words would cut rows in half and strip the column names from
    all but the first piece.
    """
    lines = [l for l in text.split("\n") if l.strip()]
    rows = [l for l in lines if l.lstrip().startswith("|")]
    if len(rows) < 3:
        return chunk_words(text, chunk_tokens, 0.0)
    caption = [l for l in lines if not l.lstrip().startswith("|")]
    header = caption + rows[:2]  # caption, column names, separator
    budget = words_per_chunk(chunk_tokens)
    base = sum(len(l.split()) for l in header)

    chunks, current, used = [], [], base
    for row in rows[2:]:
        n = len(row.split())
        if current and used + n > budget:
            chunks.append("\n".join(header + current))
            current, used = [], base
        current.append(row)
        used += n
    if current:
        chunks.append("\n".join(header + current))
    return chunks


def chunk_words(text: str, chunk_tokens: int = 300, overlap_ratio: float = 0.15) -> list[str]:
    """Split ``text`` into overlapping windows of about ``chunk_tokens`` tokens."""
    words = text.split()
    if not words:
        return []
    window = words_per_chunk(chunk_tokens)
    overlap = int(window * overlap_ratio)
    step = max(1, window - overlap)

    chunks: list[str] = []
    start = 0
    while start < len(words):
        piece = words[start : start + window]
        chunks.append(" ".join(piece))
        if start + window >= len(words):
            break  # the last window already reaches the end; no tail duplicate
        start += step
    return chunks
