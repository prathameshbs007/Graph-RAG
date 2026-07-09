from services.pdf_extractor import chunk_text


def test_chunk_text_empty_string_returns_no_chunks():
    assert chunk_text("") == []


def test_chunk_text_shorter_than_chunk_size_returns_single_chunk():
    text = "one two three"
    chunks = chunk_text(text, chunk_size=10, overlap=2)
    assert chunks == ["one two three"]


def test_chunk_text_respects_chunk_size_in_words():
    words = [f"w{i}" for i in range(25)]
    text = " ".join(words)
    chunks = chunk_text(text, chunk_size=10, overlap=0)
    assert len(chunks) == 3
    assert chunks[0] == " ".join(words[0:10])
    assert chunks[1] == " ".join(words[10:20])
    assert chunks[2] == " ".join(words[20:25])


def test_chunk_text_overlap_repeats_words_between_chunks():
    words = [f"w{i}" for i in range(15)]
    text = " ".join(words)
    chunks = chunk_text(text, chunk_size=10, overlap=5)
    assert chunks[0].split()[-5:] == chunks[1].split()[:5]
