import os
import tempfile
import uuid

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from config import settings
from models.ingest import IngestAudioResponse, IngestPDFResponse
from services import ingestion

router = APIRouter(prefix="/ingest", tags=["ingest"])


def _save_upload(data: bytes, suffix: str) -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return path


def _run_pdf(pdf_path, paper_id, title, authors, year, figures_dir, job):
    # plain function: Starlette runs it in a worker thread, so it never blocks the event loop
    try:
        ingestion.ingest_pdf(pdf_path, paper_id, title, authors, year, figures_dir, job)
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


def _run_audio(audio_path, audio_id, title, source_paper_id, job):
    try:
        ingestion.ingest_audio(audio_path, audio_id, title, source_paper_id, job=job)
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


@router.post("/pdf", response_model=IngestPDFResponse)
async def ingest_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(None),
    authors: str = Form(None),
    year: int = Form(None),
):
    paper_id = str(uuid.uuid4())
    pdf_path = _save_upload(await file.read(), ".pdf")
    author_list = [a.strip() for a in authors.split(",") if a.strip()] if authors else []
    job = ingestion.new_job(paper_id, "pdf", title or file.filename)
    background_tasks.add_task(
        _run_pdf, pdf_path, paper_id, title or file.filename, author_list, year, settings.FIGURES_DIR, job
    )
    return IngestPDFResponse(
        paper_id=paper_id,
        chunks_created=0,
        figures_extracted=0,
        graph_nodes_created=0,
        status="queued - processing in background",
    )


@router.post("/audio", response_model=IngestAudioResponse)
async def ingest_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(None),
    source_paper_id: str = Form(None),
):
    audio_id = str(uuid.uuid4())
    suffix = os.path.splitext(file.filename or "")[1] or ".audio"
    audio_path = _save_upload(await file.read(), suffix)
    job = ingestion.new_job(audio_id, "audio", title or file.filename)
    background_tasks.add_task(_run_audio, audio_path, audio_id, title or file.filename, source_paper_id, job)
    return IngestAudioResponse(
        audio_id=audio_id,
        segments=0,
        chunks_created=0,
        duration_seconds=0.0,
        status="queued - processing in background",
    )


@router.get("/status/{job_id}")
def ingest_status(job_id: str):
    job = ingestion.JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="unknown job id (the server may have restarted)")
    return job.as_dict()


@router.get("/jobs")
def ingest_jobs():
    return {"jobs": [j.as_dict() for j in reversed(list(ingestion.JOBS.values()))]}
