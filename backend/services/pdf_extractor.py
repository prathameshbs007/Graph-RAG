import fitz  # PyMuPDF
from PIL import Image
import io
import logging
import os
import pytesseract
from config import settings

logger = logging.getLogger(__name__)

def chunk_text(text: str, chunk_size=512, overlap=50) -> list[str]:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        i += chunk_size - overlap
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
            page_chunks = chunk_text(text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
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
            image_ext = base_image["ext"]
            
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
                    "file_path": image_filepath
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
