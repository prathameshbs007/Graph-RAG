import logging
import os
import uuid

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from config import settings
from models.ingest import IngestAcceptedResponse
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

# In-memory ingestion status store: id -> status dict. Fine for a single-process deployment.
_ingest_status: dict[str, dict] = {}


async def _read_upload_within_limit(file: UploadFile) -> bytes:
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 50 MB limit")
    if len(content) == 0:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")
    return content


@router.get("/status/{item_id}")
def get_ingest_status(item_id: str):
    status = _ingest_status.get(item_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Unknown ingest id")
    return status


def _process_pdf(paper_id: str, pdf_path: str, paper_title: str, author_list: list[str], paper_year):
    try:
        figures_dir = settings.FIGURES_DIR
        chunks_data, figures_data = extract_pdf_data(pdf_path, paper_id, figures_dir)

        if chunks_data:
            texts = [chunk["chunk_text"] for chunk in chunks_data]
            embeddings = get_text_embedding(texts)
            for i, chunk in enumerate(chunks_data):
                chunk["paper_id"] = paper_id
                chunk["paper_title"] = paper_title
                chunk["authors"] = author_list
                chunk["year"] = paper_year
                chunk["vector"] = embeddings[i]

        for fig in figures_data:
            fig["paper_id"] = paper_id
            fig["paper_title"] = paper_title
            fig["vector"] = clip_embedder.get_image_embedding(fig["file_path"])

        db.insert_text_chunks(chunks_data)
        db.insert_figure_chunks(figures_data)
        graph_db.create_paper_node(paper_id, paper_title, paper_year, author_list)

        lead_text = "\n\n".join(c["chunk_text"] for c in chunks_data if c.get("page", 0) <= 3)
        concept_data = extract_concepts(lead_text)
        concepts_linked = graph_db.add_concepts(paper_id, concept_data["concepts"])
        citations_linked = graph_db.add_citations(paper_id, concept_data["cited_titles"])

        _ingest_status[paper_id] = {
            "status": "done",
            "paper_id": paper_id,
            "chunks_created": len(chunks_data),
            "figures_extracted": len(figures_data),
            "graph_nodes_created": 1 + len(author_list) + concepts_linked + citations_linked,
        }
    except Exception as e:
        logger.error("PDF ingestion failed for paper_id=%s: %s", paper_id, e)
        _ingest_status[paper_id] = {"status": "error", "detail": str(e)}
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


@router.post("/pdf", response_model=IngestAcceptedResponse, status_code=202)
async def ingest_pdf(
    background_tasks: BackgroundTasks,
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
    with open(pdf_path, "wb") as f:
        f.write(content)

    paper_title = title if title else file.filename
    author_list = [a.strip() for a in authors.split(",")] if authors else []
    paper_year = year if year else None

    _ingest_status[paper_id] = {"status": "processing"}
    background_tasks.add_task(_process_pdf, paper_id, pdf_path, paper_title, author_list, paper_year)

    return IngestAcceptedResponse(id=paper_id)


def _process_audio(audio_id: str, audio_path: str, audio_title: str, source_paper_id: str):
    try:
        chunks_data, duration, num_segments = transcriber.transcribe(audio_path)

        if chunks_data:
            texts = [chunk["chunk_text"] for chunk in chunks_data]
            embeddings = get_text_embedding(texts)
            for i, chunk in enumerate(chunks_data):
                chunk["audio_id"] = audio_id
                chunk["title"] = audio_title
                chunk["source_paper_id"] = source_paper_id
                chunk["vector"] = embeddings[i]

        db.insert_audio_chunks(chunks_data)

        _ingest_status[audio_id] = {
            "status": "done",
            "audio_id": audio_id,
            "segments": num_segments,
            "chunks_created": len(chunks_data),
            "duration_seconds": float(duration),
        }
    except Exception as e:
        logger.error("Audio ingestion failed for audio_id=%s: %s", audio_id, e)
        _ingest_status[audio_id] = {"status": "error", "detail": str(e)}
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


@router.post("/audio", response_model=IngestAcceptedResponse, status_code=202)
async def ingest_audio(
    background_tasks: BackgroundTasks,
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
    with open(audio_path, "wb") as f:
        f.write(content)

    audio_title = title if title else file.filename

    _ingest_status[audio_id] = {"status": "processing"}
    background_tasks.add_task(_process_audio, audio_id, audio_path, audio_title, source_paper_id or "")

    return IngestAcceptedResponse(id=audio_id)
