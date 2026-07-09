import logging
import os
import uuid

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from config import settings
from models.ingest import IngestAudioResponse, IngestPDFResponse
from services.audio_transcriber import transcriber
from services.clip_embedder import clip_embedder
from services.concept_extractor import extract_concepts
from services.embedder import get_text_embedding
from services.neo4j_client import graph_db
from services.pdf_extractor import extract_pdf_data
from services.qdrant_client import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
PDF_MAGIC_BYTES = b"%PDF"
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".flac", ".ogg"}


async def _read_upload_within_limit(file: UploadFile) -> bytes:
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 50 MB limit")
    if len(content) == 0:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")
    return content


@router.post("/pdf", response_model=IngestPDFResponse)
async def ingest_pdf(
    file: UploadFile = File(...),
    title: str = Form(None),
    authors: str = Form(None),
    year: int = Form(None)
):
    content = await _read_upload_within_limit(file)
    if not content.startswith(PDF_MAGIC_BYTES):
        raise HTTPException(status_code=422, detail="File is not a valid PDF")

    paper_id = str(uuid.uuid4())
    pdf_path = f"/tmp/{paper_id}.pdf"

    try:
        with open(pdf_path, "wb") as f:
            f.write(content)

        paper_title = title if title else file.filename
        author_list = [a.strip() for a in authors.split(",")] if authors else []
        paper_year = year if year else None

        figures_dir = settings.FIGURES_DIR
        chunks_data, figures_data = extract_pdf_data(pdf_path, paper_id, figures_dir)

        if chunks_data:
            texts = [chunk["chunk_text"] for chunk in chunks_data]
            try:
                embeddings = get_text_embedding(texts)
            except Exception as e:
                logger.error("Text embedding failed during PDF ingestion: %s", e)
                raise HTTPException(status_code=502, detail="Embedding service unavailable") from e
            for i, chunk in enumerate(chunks_data):
                chunk["paper_id"] = paper_id
                chunk["paper_title"] = paper_title
                chunk["authors"] = author_list
                chunk["year"] = paper_year
                chunk["vector"] = embeddings[i]

        for fig in figures_data:
            fig["paper_id"] = paper_id
            fig["paper_title"] = paper_title
            try:
                fig["vector"] = clip_embedder.get_image_embedding(fig["file_path"])
            except Exception as e:
                logger.error("CLIP embedding failed during PDF ingestion: %s", e)
                raise HTTPException(status_code=502, detail="Embedding service unavailable") from e

        try:
            db.insert_text_chunks(chunks_data)
            db.insert_figure_chunks(figures_data)
            graph_db.create_paper_node(paper_id, paper_title, paper_year, author_list)
        except Exception as e:
            logger.error("Failed to persist PDF ingestion for paper_id=%s: %s", paper_id, e)
            raise HTTPException(status_code=502, detail="Failed to store ingested data") from e

        lead_text = "\n\n".join(c["chunk_text"] for c in chunks_data if c.get("page", 0) <= 3)
        concept_data = extract_concepts(lead_text)
        concepts_linked = graph_db.add_concepts(paper_id, concept_data["concepts"])
        citations_linked = graph_db.add_citations(paper_id, concept_data["cited_titles"])

        return IngestPDFResponse(
            paper_id=paper_id,
            chunks_created=len(chunks_data),
            figures_extracted=len(figures_data),
            graph_nodes_created=1 + len(author_list) + concepts_linked + citations_linked,
            status="success"
        )
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


@router.post("/audio", response_model=IngestAudioResponse)
async def ingest_audio(
    file: UploadFile = File(...),
    title: str = Form(None),
    source_paper_id: str = Form(None)
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(status_code=422, detail=f"Unsupported audio extension: {ext or '(none)'}")

    content = await _read_upload_within_limit(file)

    audio_id = str(uuid.uuid4())
    audio_path = f"/tmp/{audio_id}{ext}"

    try:
        with open(audio_path, "wb") as f:
            f.write(content)

        audio_title = title if title else file.filename

        try:
            chunks_data, duration, num_segments = transcriber.transcribe(audio_path)
        except Exception as e:
            logger.error("Audio transcription failed for audio_id=%s: %s", audio_id, e)
            raise HTTPException(status_code=502, detail="Transcription service unavailable") from e

        if chunks_data:
            texts = [chunk["chunk_text"] for chunk in chunks_data]
            try:
                embeddings = get_text_embedding(texts)
            except Exception as e:
                logger.error("Text embedding failed during audio ingestion: %s", e)
                raise HTTPException(status_code=502, detail="Embedding service unavailable") from e
            for i, chunk in enumerate(chunks_data):
                chunk["audio_id"] = audio_id
                chunk["title"] = audio_title
                chunk["source_paper_id"] = source_paper_id if source_paper_id else ""
                chunk["vector"] = embeddings[i]

        try:
            db.insert_audio_chunks(chunks_data)
        except Exception as e:
            logger.error("Failed to persist audio ingestion for audio_id=%s: %s", audio_id, e)
            raise HTTPException(status_code=502, detail="Failed to store ingested data") from e

        return IngestAudioResponse(
            audio_id=audio_id,
            segments=num_segments,
            chunks_created=len(chunks_data),
            duration_seconds=float(duration),
            status="success"
        )
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)
