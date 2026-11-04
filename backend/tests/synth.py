"""Build small but realistic PDFs for tests (no external files needed)."""

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz  # type: ignore


def make_paper(path: str, title: str, sections: list[tuple[str, str]], references: list[str], figure_caption: str | None):
    """Single-column paper: title, numbered sections, an optional vector figure, references."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    y = 90.0

    def text(rect_h, body, size=10, bold=False):
        nonlocal y, page
        if y + rect_h > 780:
            page = doc.new_page(width=595, height=842)
            y = 90.0
        rect_h = max(rect_h, size * 2.0)
        rc = fitz.Rect(72, y, 523, y + rect_h)
        left = page.insert_textbox(rc, body, fontsize=size, fontname="hebo" if bold else "helv")
        assert left >= 0, f"text overflow ({left}) for {body[:30]!r}"
        y += rect_h + 8

    text(64, title, size=18, bold=True)
    for i, (heading, body) in enumerate(sections, start=1):
        text(20, f"{i} {heading}", size=13, bold=True)
        lines = max(3, len(body) // 78 + 2)
        text(lines * 13, body)
        if i == 1 and figure_caption:
            if y + 190 > 780:
                page = doc.new_page(width=595, height=842)
                y = 90.0
            shape = page.new_shape()
            shape.draw_rect(fitz.Rect(120, y, 470, y + 140))
            shape.finish(fill=(0.85, 0.92, 1.0), color=(0.2, 0.3, 0.6))
            for k in range(5):
                shape.draw_line((140 + k * 60, y + 20), (170 + k * 60, y + 110))
            shape.finish(color=(0.8, 0.2, 0.2), width=2)
            shape.commit()
            y += 148
            text(28, figure_caption, size=9)
    text(20, "References", size=13, bold=True)
    for ref in references:
        text(max(1, len(ref) // 78 + 1) * 13, ref)
    doc.save(path)
    doc.close()
