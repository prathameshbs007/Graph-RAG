from services.pdf_extractor import chunk_text, split_sentences


def _make_sentence(index: int, word_count: int = 20) -> str:
    words = ["Word"] + [f"w{i}" for i in range(word_count - 1)]
    return " ".join(words) + f" number{index}."


def test_chunk_text_empty_string_returns_no_chunks():
    assert chunk_text("") == []


def test_chunk_text_shorter_than_chunk_size_returns_single_chunk():
    text = "One sentence here. Another short one."
    chunks = chunk_text(text, chunk_size=50)
    assert chunks == ["One sentence here. Another short one."]


def test_split_sentences_basic_punctuation():
    text = "This is one sentence. This is another! Is this a third?"
    assert split_sentences(text) == [
        "This is one sentence.",
        "This is another!",
        "Is this a third?",
    ]


def test_split_sentences_does_not_split_on_abbreviations():
    text = "Vaswani et al. showed that attention works well. Fig. 2 illustrates this."
    assert split_sentences(text) == [
        "Vaswani et al. showed that attention works well.",
        "Fig. 2 illustrates this.",
    ]


def test_split_sentences_empty_input_returns_no_sentences():
    assert split_sentences("") == []
    assert split_sentences("   ") == []


def test_chunk_text_never_splits_a_sentence_across_chunks():
    sentences = [_make_sentence(i) for i in range(10)]
    text = " ".join(sentences)
    chunks = chunk_text(text, chunk_size=50)
    for chunk in chunks:
        for s in split_sentences(chunk):
            assert s in sentences, f"chunk contains a fragment not matching any full sentence: {s!r}"


def test_chunk_text_consecutive_chunks_share_boundary_sentence():
    sentences = [_make_sentence(i) for i in range(10)]
    text = " ".join(sentences)
    chunks = chunk_text(text, chunk_size=50)
    assert len(chunks) >= 2
    first_chunk_sentences = split_sentences(chunks[0])
    second_chunk_sentences = split_sentences(chunks[1])
    assert first_chunk_sentences[-1] == second_chunk_sentences[0]


def test_chunk_text_single_long_sentence_becomes_its_own_chunk():
    long_sentence = "Word " + " ".join(f"w{i}" for i in range(99)) + "."
    chunks = chunk_text(long_sentence, chunk_size=50)
    assert chunks == [long_sentence]


def test_chunk_text_long_sentence_followed_by_short_one_splits_into_two_chunks():
    long_sentence = "Word " + " ".join(f"w{i}" for i in range(99)) + "."
    short_sentence = "Short sentence here."
    text = f"{long_sentence} {short_sentence}"
    chunks = chunk_text(text, chunk_size=50)
    assert len(chunks) == 2
    assert chunks[0] == long_sentence
    assert short_sentence in chunks[1]
