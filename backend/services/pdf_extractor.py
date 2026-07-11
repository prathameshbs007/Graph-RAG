import base64
import io
import logging
import os
import re

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

from config import settings

logger = logging.getLogger(__name__)

MAX_FIGURE_BASE64_BYTES = 200 * 1024

# Common abbreviations that precede a period without ending a sentence. Keeps the
# regex splitter from breaking on "et al.", "Fig. 3", "e.g.", "Dr. Smith", etc.,
# which are common in academic text.
_ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "vs", "etc",
    "e.g", "i.e", "fig", "figs", "eq", "eqs", "et", "al", "no",
    "vol", "pp", "p", "ch", "sec", "approx", "cf", "ref", "refs",
    "resp", "u.s", "u.k", "inc", "ltd", "co",
}

# A boundary candidate is sentence-ending punctuation followed by whitespace and
# the start of a new sentence (capital letter, digit, quote, or open paren).
_BOUNDARY_RE = re.compile(r'[.!?](\s+)(?=[A-Z0-9"‘“(]|$)')
_TRAILING_WORD_RE = re.compile(r'(\b[A-Za-z.]+)\.$')


def split_sentences(text: str) -> list[str]:
    """Split text into sentences, treating common academic abbreviations as
    non-boundaries so "et al. (2020) showed..." stays one sentence."""
    text = text.strip()
    if not text:
        return []

    sentences = []
    start = 0
    for match in _BOUNDARY_RE.finditer(text):
        end = match.start() + 1  # include the punctuation mark itself
        candidate = text[start:end]
        word_match = _TRAILING_WORD_RE.search(candidate)
        if word_match and word_match.group(1).lower().rstrip(".") in _ABBREVIATIONS:
            continue  # not a real sentence boundary; keep accumulating
        sentences.append(candidate.strip())
        start = match.end()

    tail = text[start:].strip()
    if tail:
        sentences.append(tail)

    return [s for s in sentences if s]


def _encode_figure_base64(pil_img: Image.Image, max_bytes: int = MAX_FIGURE_BASE64_BYTES) -> str:
    """JPEG-encode a downscaled copy of the figure as base64, staying under max_bytes."""
    thumb = pil_img.copy()
    thumb.thumbnail((800, 800))
    quality = 85
    while True:
        buf = io.BytesIO()
        thumb.save(buf, format="JPEG", quality=quality)
        data = buf.getvalue()
        if len(data) <= max_bytes or quality <= 30:
            return base64.b64encode(data).decode("utf-8")
        quality -= 15

def chunk_text(text: str, chunk_size: int = 512) -> list[str]:
    """Pack sentences into chunks of up to chunk_size words, never splitting a
    sentence across chunks. Consecutive chunks share their boundary sentence for
    continuity. A single sentence longer than chunk_size still becomes its own
    (oversized) chunk rather than being cut mid-sentence."""
    sentences = split_sentences(text)
    if not sentences:
        return []

    chunks = []
    current_sentences: list[str] = []
    current_word_count = 0

    for sentence in sentences:
        sentence_word_count = len(sentence.split())
        if current_sentences and current_word_count + sentence_word_count > chunk_size:
            chunks.append(" ".join(current_sentences))
            overlap_sentence = current_sentences[-1]
            current_sentences = [overlap_sentence, sentence]
            current_word_count = len(overlap_sentence.split()) + sentence_word_count
        else:
            current_sentences.append(sentence)
            current_word_count += sentence_word_count

    if current_sentences:
        chunks.append(" ".join(current_sentences))

    return chunks

def extract_pdf_data(file_path: str, paper_id: str, output_dir: str):
    doc = fitz.open(file_path)
    chunks_data = []
    figures_data = []

    os.makedirs(output_dir, exist_ok=True)

    for page_num in range(len(doc)):
        page = doc[page_num]

        # Text extraction
        text = page.get_text("text").strip()

        # Fallback to OCR if page has no text layer (scanned document / image PDF)
        if not text:
            try:
                # Require Tesseract to be installed in the Docker image
                text = page.get_textpage_ocr(flags=0, dpi=300, full=True).extractText().strip()
            except Exception as e:
                logger.error("OCR failed for page %d: %s", page_num + 1, e)

        if text:
            page_chunks = chunk_text(text, settings.CHUNK_SIZE)
            for c in page_chunks:
                chunks_data.append({
                    "chunk_text": c,
                    "page": page_num + 1,
                })

        # Image extraction
        image_list = page.get_images(full=True)
        for img_idx, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]

            fig_id = f"{paper_id}_p{page_num+1}_f{img_idx}"
            image_filename = f"{fig_id}.jpg" # Saving as RGB JPEG
            image_filepath = os.path.join(output_dir, image_filename)

            try:
                pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                pil_img.save(image_filepath)

                figures_data.append({
                    "figure_id": fig_id,
                    "caption": f"Figure {img_idx + 1} on page {page_num + 1}",
                    "page": page_num + 1,
                    "file_path": image_filepath,
                    "image_base64": _encode_figure_base64(pil_img),
                })

                # Perform secondary OCR directly on the embedded image to catch chart labels/data!
                img_text = pytesseract.image_to_string(pil_img).strip()
                if len(img_text) > 5:
                    chunks_data.append({
                        "chunk_text": f"[Data extracted from Figure {img_idx + 1}]: {img_text}",
                        "page": page_num + 1,
                    })

            except Exception as e:
                logger.error("Failed to process image %s: %s", fig_id, e)

    doc.close()

    for i, c in enumerate(chunks_data):
        c["chunk_index"] = i

    return chunks_data, figures_data
