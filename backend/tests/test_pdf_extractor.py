import os

import pytest

from services.chunking import chunk_table, words_per_chunk
from services.citations import cites, compact, split_references
from services.pdf_extractor import extract_pdf_data

from synth import make_paper

BODY = (
    "Hybrid retrieval combines keyword matching with dense embeddings so that exact terms and "
    "paraphrases are both found. " * 12
)


@pytest.fixture()
def pdf(tmp_path):
    p = tmp_path / "paper.pdf"
    make_paper(
        str(p),
        "Hybrid Retrieval With Reranker Feedback For Scientific Papers",
        [("Introduction", BODY), ("Method", BODY + " The reranker scores every candidate.")],
        [
            "[1] A. Author and B. Writer. Neural Passage Retrieval With Dense Embeddings. SIGIR 2021.",
            "[2] C. Third. Some unrelated earlier work on retrieval systems and indexing. 2019.",
            "[3] D. Fourth. Another reference entry that is long enough to count. ACL 2020.",
        ],
        "Figure 1: Architecture of the hybrid retriever with a feedback loop.",
    )
    return str(p)


def test_extracts_title_sections_figure_and_references(pdf, tmp_path):
    ex = extract_pdf_data(pdf, "P1", str(tmp_path / "figs"))
    assert ex.title == "Hybrid Retrieval With Reranker Feedback For Scientific Papers"
    sections = {c["section"] for c in ex.chunks}
    assert {"1 Introduction", "2 Method"} <= sections
    assert "References" not in sections  # the bibliography is not searchable text
    # chunk budget respected
    assert max(len(c["chunk_text"].split()) for c in ex.chunks) <= words_per_chunk(300)
    # the figure: found, captioned, with a bbox that includes the caption, and saved as an image
    assert len(ex.figures) == 1
    fig = ex.figures[0]
    assert fig["caption"].startswith("Figure 1: Architecture of the hybrid retriever")
    x0, y0, x1, y1 = fig["bbox"]
    assert x1 - x0 > 300 and y1 - y0 > 140
    assert os.path.getsize(fig["file_path"]) > 1000
    assert not any("Figure 1" in c["chunk_text"] for c in ex.chunks)  # caption lives with the figure
    # references
    assert len(ex.references) == 3
    assert cites("Neural Passage Retrieval With Dense Embeddings", compact(" ".join(ex.references)))


def test_page_numbers_and_headers_are_not_text(tmp_path):
    import pymupdf

    p = tmp_path / "long.pdf"
    doc = pymupdf.open()
    for i in range(6):
        pg = doc.new_page(width=595, height=842)
        pg.insert_text((72, 40), "Running Header Of This Journal", fontsize=8)
        pg.insert_text((290, 810), str(i + 1), fontsize=9)
        pg.insert_textbox(pymupdf.Rect(72, 100, 523, 300), f"Body paragraph number {i} about indexing. " * 12, fontsize=10)
    doc.save(str(p))
    ex = extract_pdf_data(str(p), "L", str(tmp_path / "f"))
    joined = " ".join(c["chunk_text"] for c in ex.chunks)
    assert "Running Header" not in joined
    assert all(ch["page"] >= 1 for ch in ex.chunks)


def test_table_chunks_keep_header_and_stay_small():
    rows = "\n".join(f"| model{i} | {i}.5 | {i * 2}.1 | some words here |" for i in range(80))
    md = "Table 3: Results.\n| Model | A | B | Notes |\n|---|---|---|---|\n" + rows
    chunks = chunk_table(md, 300)
    assert len(chunks) > 1
    for c in chunks:
        assert c.startswith("Table 3: Results.\n| Model | A | B | Notes |")
        assert len(c.split()) <= words_per_chunk(300) + 12
    assert sum(c.count("| model") for c in chunks) == 80  # no row lost or duplicated


# ------------------------------------------------------------------ references
def test_numbered_list_must_start_at_one():
    # appendix list items must not turn an author-year bibliography into a "numbered" one
    blocks = [
        "Alcorn, M. A., Li, Q. (2019). Strike with a pose. CVPR 2019.",
        "Amodei, D., Anubhai, R. (2016). Deep speech two. ICML 2016.",
        "1. Remove any phrases in brackets.",
        "2. Replace markers with a space and lowercase everything.",
        "3. Standardize spellings of numbers and words.",
    ]
    entries = split_references(blocks)
    assert any(e.startswith("Alcorn") for e in entries)


def test_author_year_and_numeric_styles():
    apa = ["Azuma, R. T. (1997). A survey of augmented reality. Presence, 6(4), 355-385. "
           "Billinghurst, M., & Kato, H. (1999). MIRAGE: A mixed reality interface. IWAR."]
    assert len(split_references(apa)) == 2
    ieee = [f"[{i}] Author {i}. A sufficiently long title number {i}. Venue 20{i:02d}." for i in range(1, 5)]
    assert len(split_references(ieee)) == 4


def test_title_matching_survives_hyphenation_case_and_wraps():
    refs = compact("Zhang, Y. 2020. Retrieval- augmented genera-\ntion for knowledge intensive NLP tasks. NeurIPS.")
    assert cites("Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks", refs)
    assert not cites("Introduction", refs)  # too short / generic to link on
    assert not cites("Attention Is All You Need", refs)


# ------------------------------------------------------------- regressions
def test_heading_text_is_kept_with_its_section(tmp_path):
    """A heading is searchable context, and a short block mistaken for one must not vanish."""
    p = tmp_path / "h.pdf"
    make_paper(str(p), "Some Paper Title About Retrieval Systems",
               [("Method", BODY), ("Discussion", BODY)],
               ["[1] A. B. A long enough reference entry to be counted. 2020."], None)
    ex = extract_pdf_data(str(p), "H", str(tmp_path / "f"))
    first = {c["section"]: c["chunk_text"] for c in reversed(ex.chunks)}
    assert first["1 Method"].startswith("1 Method ")
    assert first["2 Discussion"].startswith("2 Discussion ")


def test_scanned_pdf_goes_through_ocr_not_through_heading_detection(tmp_path):
    """Image-only page (no text layer). Needs Tesseract, which the Docker image has."""
    import io
    import shutil

    if shutil.which("tesseract") is None:
        pytest.skip("tesseract not installed on this machine (it is in the Docker image)")
    import pymupdf
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (1240, 1000), "white")
    d = ImageDraw.Draw(img)
    f = ImageFont.load_default(size=34)
    for i, line in enumerate(["Hybrid retrieval combines keyword matching with dense embeddings",
                              "The reranker scores every candidate passage for relevance."]):
        d.text((60, 100 + 60 * i), line, fill="black", font=f)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_image(pymupdf.Rect(30, 30, 565, 480), stream=buf.getvalue())
    path = tmp_path / "scan.pdf"
    doc.save(str(path))
    assert not pymupdf.open(str(path))[0].get_text().strip()  # really no text layer

    ex = extract_pdf_data(str(path), "S", str(tmp_path / "f"))
    text = " ".join(c["chunk_text"] for c in ex.chunks).lower()
    assert "dense embeddings" in text and "reranker" in text
