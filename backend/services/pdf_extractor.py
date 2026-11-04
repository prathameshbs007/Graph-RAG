"""PDF parsing for Module 1: text, headings, tables, figures (with caption, page and
bounding box) and the reference list.

Nothing here is tuned to a particular paper or publisher. It relies on properties
that hold for typeset papers in general:

* reading order is the PDF stream order (``sort=True`` would interleave columns);
* body text is the most common font size; headings are larger and/or bold and short;
* running headers/footers repeat on many pages; margin stamps (e.g. the arXiv
  sidebar) are rotated;
* a figure caption sits next to the image / vector drawing it describes;
* images repeated across pages are decoration (logos, watermarks), not figures.

Text is split into chunks of ~300 tokens with 15% overlap *within a page and section*,
so every chunk can cite an exact page and section.
"""

import collections
import os
import re
import unicodedata
from dataclasses import dataclass, field

try:  # PyMuPDF >= 1.24 exposes the new name; older builds only have ``fitz``
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz  # type: ignore

from config import settings
from services.chunking import chunk_table, chunk_words
from services.citations import split_references

FIGURE_CAPTION = re.compile(r"^\s*(figure|fig\.?)\s*(\d+|[IVX]+)\b", re.I)
TABLE_CAPTION = re.compile(r"^\s*table\s*(\d+|[IVX]+)\b", re.I)
REFERENCES_HEADING = re.compile(
    r"^\s*(\d+\.?\s*|[IVX]+\.?\s*)?(references|bibliography|literature cited|works cited)\s*:?\s*$", re.I
)
APPENDIX_HEADING = re.compile(r"^\s*(\d+\.?\s*|[A-Z]\.?\s*)?(appendix|appendices|supplementary)\b", re.I)
_BAD_TITLE = re.compile(r"(\.(pdf|tex|dvi|docx?|indd)$|untitled|microsoft word|^main$|^paper$)", re.I)
_YEAR = re.compile(r"\b(19[89]\d|20[0-3]\d)\b")

MAX_DRAWINGS_FOR_CLUSTERING = 20000  # plots with more vector paths than this are skipped (slow)
# Running headers, footers and page numbers sit in the outer part of the page; plot tick labels
# near the top of a figure must not be mistaken for them.
FURNITURE_ZONE = 0.08


@dataclass
class ExtractedPDF:
    chunks: list[dict] = field(default_factory=list)
    figures: list[dict] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    pages: int = 0


# ----------------------------------------------------------------- helpers
def _clean(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)  # ligatures: "ﬁ" -> "fi"
    text = re.sub(r"-\s*\n\s*(?=[a-z])", "", text)  # de-hyphenate line breaks
    return re.sub(r"\s+", " ", text).strip()


def _block_text(block: dict) -> str:
    return _clean("\n".join("".join(span["text"] for span in line["spans"]) for line in block.get("lines", [])))


def _is_horizontal(block: dict) -> bool:
    """False for rotated text (margin stamps, rotated table headers)."""
    return all(abs(line.get("dir", (1.0, 0.0))[0]) > 0.9 for line in block.get("lines", []))


def _block_stats(block: dict) -> tuple[float, bool, int]:
    spans = [s for l in block.get("lines", []) for s in l["spans"] if s["text"].strip()]
    if not spans:
        return 0.0, False, 0
    size = max(s["size"] for s in spans)
    bold = all((s["flags"] & 16) or "bold" in s["font"].lower() for s in spans)
    return size, bool(bold), len(block.get("lines", []))


def _text_dict(page, textpage=None) -> dict:
    """Stream-order text blocks without embedded image bytes; ligatures expanded."""
    flags = fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES & ~fitz.TEXT_PRESERVE_LIGATURES
    return page.get_text("dict", flags=flags, textpage=textpage)


def _page_dict(page, ocr_cache: dict | None = None, min_chars: int = 25) -> dict:
    """Text blocks of a page; falls back to OCR for scanned pages with no text layer.

    OCR is slow, so its result is kept in ``ocr_cache`` for the later passes over the page.
    """
    if ocr_cache is not None and page.number in ocr_cache:
        return ocr_cache[page.number]
    if len(page.get_text("text").strip()) < min_chars:
        try:
            result = _text_dict(page, textpage=page.get_textpage_ocr(flags=0, dpi=300, full=True))
            if ocr_cache is not None:
                ocr_cache[page.number] = result
            return result
        except Exception as exc:  # noqa: BLE001 - tesseract not installed / failed
            print(f"[pdf] OCR unavailable for page {page.number + 1}: {exc}")
    return _text_dict(page)


def _body_font_size(doc, ocr_cache: dict, max_pages: int = 10) -> float:
    """Most common font size by characters. Uses the OCR-aware text so scanned papers are
    measured too; otherwise every OCR'd line would look "larger than body" and be taken
    for a heading."""
    sizes: collections.Counter = collections.Counter()
    for i, page in enumerate(doc):
        if i >= max_pages:
            break
        for b in _page_dict(page, ocr_cache)["blocks"]:
            for l in b.get("lines", []):
                for s in l["spans"]:
                    sizes[round(s["size"], 1)] += len(s["text"].strip())
    return sizes.most_common(1)[0][0] if sizes else 10.0


def _furniture_key(text: str) -> str:
    return re.sub(r"\d+", "#", text.lower())


def _repeated_furniture(doc) -> set[str]:
    """Texts that recur in the top/bottom margin of many pages (running headers, footers)."""
    if len(doc) < 4:
        return set()
    counts: collections.Counter = collections.Counter()
    for page in doc:
        h = page.rect.height
        seen = set()
        for b in _text_dict(page)["blocks"]:
            if b["type"] != 0:
                continue
            if b["bbox"][3] < h * FURNITURE_ZONE or b["bbox"][1] > h * (1 - FURNITURE_ZONE):
                key = _furniture_key(_block_text(b))
                if key and key not in seen:
                    seen.add(key)
                    counts[key] += 1
    return {k for k, n in counts.items() if n >= max(3, 0.4 * len(doc))}


def _decorative_xrefs(doc) -> set:
    """Images placed on several pages (watermarks, logos, banners) are not figures."""
    if len(doc) < 3:
        return set()
    pages_per_xref: collections.Counter = collections.Counter()
    for page in doc:
        for xref in {i.get("xref") for i in page.get_image_info(xrefs=True)}:
            if xref:
                pages_per_xref[xref] += 1
    return {x for x, n in pages_per_xref.items() if n >= 2}


def _horiz_overlap(a, b) -> float:
    return max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0))


def _overlap_area(a, b) -> float:
    w = min(a.x1, b.x1) - max(a.x0, b.x0)
    h = min(a.y1, b.y1) - max(a.y0, b.y0)
    return w * h if w > 0 and h > 0 else 0.0


def _merge_rects(rects: list, gap: float = 12.0) -> list:
    """Union rectangles that overlap or lie within ``gap`` points of each other."""
    rects = [fitz.Rect(r) for r in rects]
    changed = True
    while changed:
        changed = False
        for i in range(len(rects)):
            grown = fitz.Rect(rects[i].x0 - gap, rects[i].y0 - gap, rects[i].x1 + gap, rects[i].y1 + gap)
            for j in range(i + 1, len(rects)):
                if grown.intersects(rects[j]):
                    rects[i] |= rects[j]
                    rects.pop(j)
                    changed = True
                    break
            if changed:
                break
    return rects


def _find_tables(page) -> list[tuple]:
    try:
        found = page.find_tables()
    except Exception:  # noqa: BLE001 - older PyMuPDF
        return []
    out = []
    for t in found.tables:
        try:
            md = t.to_markdown().strip()
        except Exception:  # noqa: BLE001
            continue
        if t.row_count >= 2 and t.col_count >= 2 and len(md) > 20:
            out.append((fitz.Rect(t.bbox), md))
    return out


def _figure_regions(page, tables: list, decorative: set) -> list:
    """Candidate figure rectangles: raster images and clusters of vector drawings."""
    page_area = page.rect.get_area()
    rects = []
    for info in page.get_image_info(xrefs=True):
        if info.get("xref") in decorative:
            continue
        r = fitz.Rect(info["bbox"])
        if r.width >= 40 and r.height >= 40:
            rects.append(r)
    try:
        if len(page.get_drawings()) <= MAX_DRAWINGS_FOR_CLUSTERING:
            for r in page.cluster_drawings():
                r = fitz.Rect(r)
                if r.width >= 60 and r.height >= 40:
                    rects.append(r)
    except Exception:  # noqa: BLE001 - older PyMuPDF
        pass
    out = []
    for r in _merge_rects(rects):
        if r.get_area() > 0.92 * page_area:  # page background / scan
            continue
        if any(_overlap_area(r, t[0]) > 0.5 * r.get_area() for t in tables):
            continue
        out.append(r)
    return out


def _merge_caption_continuations(items: list[dict]) -> list[dict]:
    """A caption paragraph is often split over several PDF blocks (e.g. when its first words
    are bold or italic). Append the text blocks that directly follow it in the same column."""
    out: list[dict] = []
    for it in items:
        prev = out[-1] if out else None
        if (
            prev is not None
            and prev["kind"] in ("figure_caption", "table_caption")
            and it["kind"] == "text"
            and -2 <= it["rect"].y0 - prev["rect"].y1 <= max(3.0, prev["size"] * 0.45)
            and abs(it["rect"].x0 - prev["rect"].x0) <= 8
            and it["rect"].x1 <= prev["rect"].x1 + 10
            and abs(it["size"] - prev["size"]) <= 0.6
        ):
            prev["text"] += " " + it["text"]
            prev["rect"] = fitz.Rect(prev["rect"] | it["rect"])
            continue
        out.append(dict(it))
    return out


def _pick_figure_region(cap, other_caps: list, regions: list, used: list, page_rect, top_floor, bottom_ceil):
    """The graphics a figure caption describes, or ``None``.

    A caption owns only the part of a region that lies *above* it (or just below it, for
    captions placed above their figure), and, if another caption sits on the same row,
    only its own side of the gap between the two. This keeps working when several
    figures have been merged into one big cluster of drawings, or when a cluster's box
    runs into its own caption.
    """
    left, right = page_rect.x0, page_rect.x1
    for o in other_caps:  # side-by-side figures: split the page at the gap between captions
        if abs(o.y0 - cap.y0) < 40 and _horiz_overlap(cap, o) == 0:
            if o.x0 >= cap.x1:
                right = min(right, (cap.x1 + o.x0) / 2)
            else:
                left = max(left, (o.x1 + cap.x0) / 2)

    def clipped(r, y_min, y_max):
        # never reach into the running header / footer zone (its rule lines are drawings too)
        y_min, y_max = max(y_min, top_floor), min(y_max, bottom_ceil)
        c = fitz.Rect(max(r.x0, left), max(r.y0, y_min), min(r.x1, right), min(r.y1, y_max))
        if c.width < 40 or c.height < 40 or _horiz_overlap(c, cap) <= 0:
            return None
        if any(_overlap_area(c, u) > 0.5 * c.get_area() for u in used):
            return None
        return c

    above, below = [], []
    for r in regions:
        if r.y0 < cap.y0 - 10:
            c = clipped(r, page_rect.y0, cap.y0 - 1)
            if c is not None and cap.y0 - c.y1 < 110:
                above.append(c)
        if r.y1 > cap.y1 + 10:
            c = clipped(r, cap.y1 + 1, page_rect.y1)
            if c is not None and c.y0 - cap.y1 < 60:
                below.append(c)

    if above:
        group = fitz.Rect(max(above, key=lambda c: c.y1))
        pool = above
    elif below:
        group = fitz.Rect(min(below, key=lambda c: c.y0))
        pool = below
    else:
        return None
    grew = True
    while grew:  # pull in sub-figures stacked in the same column
        grew = False
        for c in pool:
            if group.contains(c) or _horiz_overlap(c, group) <= 0:
                continue
            if max(c.y0 - group.y1, group.y0 - c.y1) < 30:
                group |= c
                grew = True
    return group


def _ocr_text(pix) -> str:
    try:
        import pytesseract
        from PIL import Image

        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        text = pytesseract.image_to_string(img).strip()
        return re.sub(r"\s+", " ", text)[:400] if len(text) > 5 else ""
    except Exception:  # noqa: BLE001 - OCR is a bonus, never a requirement
        return ""


# ------------------------------------------------------- title / year / authors
def _plausible_title(t: str) -> bool:
    t = t.strip()
    return len(t) >= 10 and len(t.split()) >= 3 and not _BAD_TITLE.search(t)


def guess_title(doc) -> str | None:
    meta = ((doc.metadata or {}).get("title") or "").strip()
    if _plausible_title(meta):
        return meta[:250]
    if len(doc) == 0:
        return None
    page = doc[0]
    blocks = [b for b in _text_dict(page)["blocks"] if b["type"] == 0 and _is_horizontal(b)]
    sized = [(b, _block_stats(b)[0]) for b in blocks if b["bbox"][1] < page.rect.height * 0.45]
    if not sized:
        return None
    top = max(s for _, s in sized)
    title = " ".join(_block_text(b) for b, s in sized if abs(s - top) < 0.6 and top > 0).strip()
    return title[:250] if _plausible_title(title) else None


def guess_authors(doc) -> list[str]:
    raw = ((doc.metadata or {}).get("author") or "").strip()
    if not raw or len(raw) > 300:
        return []
    parts = re.split(r"\s*(?:;|,|\band\b|&)\s*", raw)
    junk = re.compile(r"anonymous|unknown|admin|user|author|submission|\.(docx?|tex)$", re.I)
    return [p.strip() for p in parts if 2 < len(p.strip()) < 60 and not junk.search(p)]


def guess_year(doc, margin_text: str) -> int | None:
    """Year from page-1 margin text (arXiv stamp, conference banner), else PDF metadata."""
    years = [int(y) for y in _YEAR.findall(margin_text)]
    if years:
        return max(years)
    m = re.match(r"D:(\d{4})", (doc.metadata or {}).get("creationDate") or "")
    return int(m.group(1)) if m else None


# --------------------------------------------------------------- extraction
def extract_pdf_data(file_path: str, paper_id: str, output_dir: str) -> ExtractedPDF:
    doc = fitz.open(file_path)
    if doc.needs_pass:
        raise ValueError("PDF is password protected")
    os.makedirs(output_dir, exist_ok=True)
    ocr_cache: dict[int, dict] = {}
    body = _body_font_size(doc, ocr_cache)
    decorative = _decorative_xrefs(doc)
    furniture_keys = _repeated_furniture(doc)

    out = ExtractedPDF(pages=len(doc), title=guess_title(doc), authors=guess_authors(doc))
    margin_text = ""  # page-1 rotated stamps + header/footer text, used to guess the year

    section = "Front matter"
    # Headings wait here for the first body text after them and are then prepended to it, so a
    # block that was wrongly taken for a heading never loses its content, and the section title
    # is searchable. Carried across pages (a heading can be the last thing on a page).
    pending: list[str] = []
    in_refs = False
    ref_blocks: list[str] = []
    fig_counter = 0

    def flush(buffer: list[str], page_no: int, sec: str):
        for piece in chunk_words(" ".join(buffer), settings.CHUNK_SIZE, settings.CHUNK_OVERLAP_RATIO):
            out.chunks.append({"chunk_text": piece, "page": page_no, "section": sec, "block_type": "text"})

    for pno, page in enumerate(doc):
        page_no = pno + 1
        height = page.rect.height
        page_text = page.get_text("text")
        # Table / figure detection is the slow part, and only matters if the page has a caption.
        has_table_caption = re.search(r"(?mi)^\s*table\s*(\d+|[IVX]+)\b", page_text) is not None
        has_figure_caption = re.search(r"(?mi)^\s*(figure|fig\.?)\s*(\d+|[IVX]+)\b", page_text) is not None
        tables = _find_tables(page) if has_table_caption else []
        table_rects = [t[0] for t in tables]

        page_blocks = _page_dict(page, ocr_cache)["blocks"]
        title_min = None  # page 1: the largest text near the top is the title, whatever its size
        if pno == 0:
            top = [
                _block_stats(b)[0]
                for b in page_blocks
                if b["type"] == 0 and _is_horizontal(b) and b["bbox"][1] < height * 0.45
            ]
            if top and max(top) >= body * 1.25:
                title_min = max(top) - 0.6

        # ---- classify text blocks (stream order)
        items: list[dict] = []
        furniture_rects: list = []  # running headers / page numbers / margin text on this page
        for b in page_blocks:
            if b["type"] != 0:
                continue
            text = _block_text(b)
            if not text:
                continue
            rect = fitz.Rect(b["bbox"])
            if pno == 0 and (not _is_horizontal(b) or rect.y1 < height * 0.1 or rect.y0 > height * 0.9):
                margin_text += " " + text
            if not _is_horizontal(b):
                continue
            if any(_overlap_area(rect, t) > 0.5 * max(rect.get_area(), 1e-6) for t in table_rects):
                continue
            size, bold, n_lines = _block_stats(b)
            words = len(text.split())
            in_margin = rect.y1 < height * 0.06 or rect.y0 > height * 0.94
            in_zone = rect.y1 < height * FURNITURE_ZONE or rect.y0 > height * (1 - FURNITURE_ZONE)
            if (
                (in_margin and size <= body * 1.05)
                or (in_zone and re.fullmatch(r"[\d\s.\-–]+", text))
                or (in_zone and _furniture_key(text) in furniture_keys)
            ):
                furniture_rects.append(rect)
                continue
            if re.fullmatch(r"[\d\s.\-–]+", text):
                continue
            if FIGURE_CAPTION.match(text):
                kind = "figure_caption"
            elif TABLE_CAPTION.match(text) and words < 120:
                kind = "table_caption"
            elif title_min is not None and size >= title_min and rect.y0 < height * 0.45:
                kind = "title"
            elif n_lines <= 3 and words <= 18 and (size >= body * 1.12 or (bold and words <= 12)):
                kind = "heading"
            else:
                kind = "text"
            items.append({"rect": rect, "text": text, "kind": kind, "size": size})

        items = _merge_caption_continuations(items)
        top_floor = max([f.y1 + 8 for f in furniture_rects if f.y1 < height * FURNITURE_ZONE], default=page.rect.y0)
        bottom_ceil = min([f.y0 - 4 for f in furniture_rects if f.y0 > height * (1 - FURNITURE_ZONE)], default=page.rect.y1)

        # ---- a "table" with a figure caption beside it is really a gridded figure
        fig_caps =[i["rect"] for i in items if i["kind"] == "figure_caption"]
        tab_caps = [i["rect"] for i in items if i["kind"] == "table_caption"]

        def near(rect, caps):
            return any(min(abs(c.y0 - rect.y1), abs(c.y1 - rect.y0)) < 60 and _horiz_overlap(rect, c) > 0 for c in caps)

        tables = [(r, md) for r, md in tables if near(r, tab_caps) or not near(r, fig_caps)]

        # ---- figures: associate each figure caption with the region above (or below) it
        regions = _figure_regions(page, tables, decorative) if has_figure_caption else []
        consumed: set[int] = set()
        used: list = []  # figure rectangles already claimed by a caption on this page
        all_caps = [i["rect"] for i in items if i["kind"] == "figure_caption"]
        for idx, it in enumerate(items):
            if it["kind"] != "figure_caption":
                continue
            cap = it["rect"]
            group = _pick_figure_region(
                cap, [c for c in all_caps if c != cap], regions, used, page.rect, top_floor, bottom_ceil
            )
            if group is None:
                continue
            used.append(group)

            # short text lying inside the figure (axis labels, box labels) belongs to it
            inner = []
            for j, other in enumerate(items):
                if j == idx or other["kind"] in ("figure_caption", "title"):
                    continue
                if len(other["text"].split()) <= 25 and _overlap_area(other["rect"], group) >= 0.7 * other["rect"].get_area():
                    inner.append(other["text"])
                    consumed.add(j)

            crop = fitz.Rect(group | cap)
            crop = fitz.Rect(crop.x0 - 4, max(crop.y0 - 4, top_floor), crop.x1 + 4, min(crop.y1 + 4, bottom_ceil))
            crop = crop & page.rect
            fig_id = f"{paper_id}_p{page_no}_f{fig_counter}"
            fig_counter += 1
            path = os.path.join(output_dir, f"{fig_id}.png")
            pix = page.get_pixmap(clip=crop, dpi=150)
            pix.save(path)
            figure_text = " ".join(inner)[:400] or _ocr_text(pix)
            out.figures.append(
                {
                    "figure_id": fig_id,
                    "caption": it["text"],
                    "page": page_no,
                    "bbox": [round(v, 1) for v in (crop.x0, crop.y0, crop.x1, crop.y1)],
                    "file_path": path,
                    "ocr_text": figure_text,
                }
            )
            consumed.add(idx)  # the caption now lives with its figure

        # ---- body text, tables, references
        buffer: list[str] = []
        for idx, it in enumerate(items):
            kind, text = it["kind"], it["text"]
            if idx in consumed or kind == "title":
                continue
            if kind == "heading" and REFERENCES_HEADING.match(text):
                flush(buffer, page_no, section)
                buffer, in_refs, section, pending = [], True, "References", []
                continue
            if in_refs:
                # The reference list ends at an appendix / a real section heading (a bigger
                # font, not just bold text) or when a figure/table caption shows up.
                leaves = kind in ("figure_caption", "table_caption") or (
                    kind == "heading" and (APPENDIX_HEADING.match(text) or it["size"] >= body * 1.12)
                )
                if leaves:
                    in_refs = False
                    flush(buffer, page_no, section)
                    buffer, section = [], (text if kind == "heading" else "Appendix")
                    if kind == "heading":
                        pending.append(text)
                        continue
                else:
                    ref_blocks.append(text)
                    continue
            if kind == "heading":
                flush(buffer, page_no, section)
                buffer, section = [], text
                pending.append(text)
                continue
            if pending:
                buffer.extend(pending)
                pending.clear()
            buffer.append(text)
        flush(buffer, page_no, section)

        table_caps = [i for i in items if i["kind"] == "table_caption"]
        for rect, md in tables:
            close = [c for c in table_caps if min(abs(c["rect"].y0 - rect.y1), abs(c["rect"].y1 - rect.y0)) < 60]
            cap = min(close, key=lambda c: min(abs(c["rect"].y0 - rect.y1), abs(c["rect"].y1 - rect.y0)))["text"] if close else ""
            table_text = f"{cap}\n{md}" if cap else md
            for piece in chunk_table(table_text, settings.CHUNK_SIZE):
                out.chunks.append({"chunk_text": piece, "page": page_no, "section": section, "block_type": "table"})

    out.year = guess_year(doc, margin_text)
    out.references = split_references(ref_blocks)
    doc.close()
    for i, c in enumerate(out.chunks):
        c["chunk_index"] = i
    return out
