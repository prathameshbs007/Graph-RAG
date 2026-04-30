from fastapi import APIRouter, UploadFile, File, Form
from models.ingest import IngestPDFResponse
from services.pdf_extractor import extract_pdf_data
from services.embedder import get_text_embedding
from services.clip_embedder import clip_embedder
from services.weaviate_client import db
from services.neo4j_client import graph_db
from config import settings
import uuid
import os

router = APIRouter(prefix="/ingest", tags=["ingest"])

@router.post("/pdf", response_model=IngestPDFResponse)
async def ingest_pdf(
    file: UploadFile = File(...),
    title: str = Form(None),
    authors: str = Form(None),
    year: int = Form(None)
):
    paper_id = str(uuid.uuid4())
    pdf_path = f"/tmp/{paper_id}.pdf"
    
    with open(pdf_path, "wb") as f:
        f.write(await file.read())
        
    paper_title = title if title else file.filename
    author_list = [a.strip() for a in authors.split(",")] if authors else []
    paper_year = year if year else 2024
    
    # Extract
    figures_dir = settings.FIGURES_DIR
    chunks_data, figures_data = extract_pdf_data(pdf_path, paper_id, figures_dir)
    
    # Process text chunks using batching for massive speedup
    if chunks_data:
        texts = [chunk["chunk_text"] for chunk in chunks_data]
        embeddings = get_text_embedding(texts)
        for i, chunk in enumerate(chunks_data):
            chunk["paper_id"] = paper_id
            chunk["paper_title"] = paper_title
            chunk["authors"] = author_list
            chunk["year"] = paper_year
            chunk["vector"] = embeddings[i] if i < len(embeddings) else []
        
    # Process figures
    for fig in figures_data:
        fig["paper_id"] = paper_id
        fig["paper_title"] = paper_title
        fig["vector"] = clip_embedder.get_image_embedding(fig["file_path"])
        
    # DB inserts
    try:
        db.insert_text_chunks(chunks_data)
        db.insert_figure_chunks(figures_data)
        graph_db.create_paper_node(paper_id, paper_title, paper_year, author_list)
    except Exception as e:
        print(f"Failed to ingest: {e}")
        return IngestPDFResponse(
            paper_id=paper_id,
            chunks_created=0,
            figures_extracted=0,
            graph_nodes_created=0,
            status=f"error: {str(e)}"
        )
        
    return IngestPDFResponse(
        paper_id=paper_id,
        chunks_created=len(chunks_data),
        figures_extracted=len(figures_data),
        graph_nodes_created=1 + len(author_list),
        status="success"
    )

from models.ingest import IngestAudioResponse
from services.audio_transcriber import transcriber

@router.post("/audio", response_model=IngestAudioResponse)
async def ingest_audio(
    file: UploadFile = File(...),
    title: str = Form(None),
    source_paper_id: str = Form(None)
):
    audio_id = str(uuid.uuid4())
    audio_path = f"/tmp/{audio_id}_{file.filename}"
    
    with open(audio_path, "wb") as f:
        f.write(await file.read())
        
    audio_title = title if title else file.filename
    
    # Transcribe
    chunks_data, duration, num_segments = transcriber.transcribe(audio_path)
    
    # Process text chunks
    if chunks_data:
        texts = [chunk["chunk_text"] for chunk in chunks_data]
        embeddings = get_text_embedding(texts)
        for i, chunk in enumerate(chunks_data):
            chunk["audio_id"] = audio_id
            chunk["title"] = audio_title
            chunk["source_paper_id"] = source_paper_id if source_paper_id else ""
            chunk["vector"] = embeddings[i] if i < len(embeddings) else []
        
    # DB insert
    try:
        db.insert_audio_chunks(chunks_data)
    except Exception as e:
        print(f"Failed to ingest audio: {e}")
        return IngestAudioResponse(
            audio_id=audio_id,
            segments=num_segments,
            chunks_created=0,
            duration_seconds=float(duration),
            status=f"error: {str(e)}"
        )
        
    return IngestAudioResponse(
        audio_id=audio_id,
        segments=num_segments,
        chunks_created=len(chunks_data),
        duration_seconds=float(duration),
        status="success"
    )
