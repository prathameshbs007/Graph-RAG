from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks
from models.ingest import IngestPDFResponse
from services.pdf_extractor import extract_pdf_data
from services.embedder import get_text_embedding
from services.clip_embedder import clip_embedder
from services.weaviate_client import db
from services.neo4j_client import graph_db
from services.processing_status import processing_tracker
from config import settings
import uuid
import os
import asyncio
import threading

router = APIRouter(prefix="/ingest", tags=["ingest"])

def process_pdf_background(paper_id, pdf_path, paper_title, author_list, paper_year, figures_dir):
    """Background task for PDF processing"""
    try:
        processing_tracker.start_processing(paper_id, "pdf", paper_title)
        print(f"[PDF] Starting PDF processing for {paper_id}")
        
        # Extract
        processing_tracker.update_progress(paper_id, 10, "Extracting PDF content...")
        chunks_data, figures_data = extract_pdf_data(pdf_path, paper_id, figures_dir)
        print(f"[PDF] Extracted {len(chunks_data)} chunks and {len(figures_data)} figures")
        
        # Process text chunks using batching
        if chunks_data:
            processing_tracker.update_progress(paper_id, 30, f"Embedding {len(chunks_data)} text chunks...")
            texts = [chunk["chunk_text"] for chunk in chunks_data]
            print(f"[PDF] Processing {len(texts)} text chunks for embeddings...")
            embeddings = get_text_embedding(texts)
            for i, chunk in enumerate(chunks_data):
                chunk["paper_id"] = paper_id
                chunk["paper_title"] = paper_title
                chunk["authors"] = author_list
                chunk["year"] = paper_year
                chunk["vector"] = embeddings[i] if i < len(embeddings) else []
        
        # Process figures
        if figures_data:
            processing_tracker.update_progress(paper_id, 60, f"Processing {len(figures_data)} figures...")
            for fig in figures_data:
                fig["paper_id"] = paper_id
                fig["paper_title"] = paper_title
                print(f"[PDF] Processing figure: {fig.get('file_path', 'unknown')}")
                fig["vector"] = clip_embedder.get_image_embedding(fig["file_path"])
        
        # DB inserts
        processing_tracker.update_progress(paper_id, 80, "Saving to database...")
        db.insert_text_chunks(chunks_data)
        db.insert_figure_chunks(figures_data)
        graph_db.create_paper_node(paper_id, paper_title, paper_year, author_list)
        print(f"[PDF] Successfully ingested: {len(chunks_data)} chunks, {len(figures_data)} figures, 1 paper node")
        
        # Mark as completed
        processing_tracker.complete_processing(paper_id, {
            "chunks_created": len(chunks_data),
            "figures_extracted": len(figures_data),
            "graph_nodes_created": 1 + len(author_list)
        })
        
        # Cleanup
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            print(f"[PDF] Cleaned up temporary file: {pdf_path}")
            
    except Exception as e:
        print(f"[PDF ERROR] Failed to ingest PDF {paper_id}: {e}")
        import traceback
        traceback.print_exc()
        processing_tracker.fail_processing(paper_id, str(e))

@router.post("/pdf", response_model=IngestPDFResponse)
async def ingest_pdf(
    file: UploadFile = File(...),
    title: str = Form(None),
    authors: str = Form(None),
    year: int = Form(None),
    background_tasks: BackgroundTasks = None
):
    paper_id = str(uuid.uuid4())
    pdf_path = f"/tmp/{paper_id}.pdf"
    
    file_bytes = await file.read()
    with open(pdf_path, "wb") as f:
        f.write(file_bytes)
    
    paper_title = title if title else file.filename
    author_list = [a.strip() for a in authors.split(",")] if authors else []
    paper_year = year if year else 2024
    figures_dir = settings.FIGURES_DIR
    
    print(f"[PDF] Received PDF file: {paper_title} (ID: {paper_id}, Size: {len(file_bytes)} bytes)")
    
    # Start background processing
    if background_tasks:
        background_tasks.add_task(process_pdf_background, paper_id, pdf_path, paper_title, author_list, paper_year, figures_dir)
    else:
        # Fallback: use thread
        thread = threading.Thread(target=process_pdf_background, args=(paper_id, pdf_path, paper_title, author_list, paper_year, figures_dir), daemon=True)
        thread.start()
    
    print(f"[PDF] Background processing started for {paper_id}")
    
    return IngestPDFResponse(
        paper_id=paper_id,
        chunks_created=0,
        figures_extracted=0,
        graph_nodes_created=0,
        status="processing"
    )

from models.ingest import IngestAudioResponse
from services.audio_transcriber import transcriber

def process_audio_background(audio_id, audio_path, audio_title, source_paper_id):
    """Background task for audio transcription and processing"""
    try:
        processing_tracker.start_processing(audio_id, "audio", audio_title)
        print(f"[Audio] Starting transcription for {audio_id}")
        
        # Transcribe
        processing_tracker.update_progress(audio_id, 20, "Transcribing audio...")
        chunks_data, duration, num_segments = transcriber.transcribe(audio_path)
        print(f"[Audio] Transcription complete: {num_segments} segments, {duration:.1f}s")
        
        # Process text chunks
        if chunks_data:
            processing_tracker.update_progress(audio_id, 50, f"Embedding {len(chunks_data)} text chunks...")
            texts = [chunk["chunk_text"] for chunk in chunks_data]
            print(f"[Audio] Processing {len(texts)} text chunks for embeddings...")
            embeddings = get_text_embedding(texts)
            for i, chunk in enumerate(chunks_data):
                chunk["audio_id"] = audio_id
                chunk["title"] = audio_title
                chunk["source_paper_id"] = source_paper_id if source_paper_id else ""
                chunk["vector"] = embeddings[i] if i < len(embeddings) else []
        
        # DB insert
        processing_tracker.update_progress(audio_id, 80, "Saving to database...")
        db.insert_audio_chunks(chunks_data)
        print(f"[Audio] Successfully stored {len(chunks_data)} chunks in database")
        
        # Mark as completed
        processing_tracker.complete_processing(audio_id, {
            "segments": num_segments,
            "chunks_created": len(chunks_data),
            "duration_seconds": float(duration)
        })
        
        # Cleanup
        if os.path.exists(audio_path):
            os.remove(audio_path)
            print(f"[Audio] Cleaned up temporary file: {audio_path}")
            
    except Exception as e:
        print(f"[Audio ERROR] Failed to ingest audio {audio_id}: {e}")
        import traceback
        traceback.print_exc()
        processing_tracker.fail_processing(audio_id, str(e))

@router.post("/audio", response_model=IngestAudioResponse)
async def ingest_audio(
    file: UploadFile = File(...),
    title: str = Form(None),
    source_paper_id: str = Form(None),
    background_tasks: BackgroundTasks = None
):
    audio_id = str(uuid.uuid4())
    audio_path = f"/tmp/{audio_id}_{file.filename}"
    
    # Save file
    file_bytes = await file.read()
    with open(audio_path, "wb") as f:
        f.write(file_bytes)
    
    audio_title = title if title else file.filename
    
    print(f"[Audio] Received audio file: {audio_title} (ID: {audio_id}, Size: {len(file_bytes)} bytes)")
    
    # Start background processing
    if background_tasks:
        background_tasks.add_task(process_audio_background, audio_id, audio_path, audio_title, source_paper_id)
    else:
        # Fallback: use thread if BackgroundTasks not available
        thread = threading.Thread(target=process_audio_background, args=(audio_id, audio_path, audio_title, source_paper_id), daemon=True)
        thread.start()
    
    print(f"[Audio] Background processing started for {audio_id}")
    
    # Return immediately
    return IngestAudioResponse(
        audio_id=audio_id,
        segments=0,
        chunks_created=0,
        duration_seconds=0.0,
        status="processing"
    )

from models.ingest import IngestImageResponse
from services.image_captioner import image_captioner
from PIL import Image
import io

@router.post("/image", response_model=IngestImageResponse)
async def ingest_image(
    file: UploadFile = File(...),
    title: str = Form(None),
    caption: str = Form(None),
    source_paper_id: str = Form(None)
):
    image_id = str(uuid.uuid4())
    
    # Save uploaded image
    figures_dir = settings.FIGURES_DIR
    os.makedirs(figures_dir, exist_ok=True)
    image_path = os.path.join(figures_dir, f"{image_id}_{file.filename}")
    
    file_bytes = await file.read()
    
    # Validate it's actually an image
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()
    except Exception:
        return IngestImageResponse(
            image_id=image_id,
            chunks_created=0,
            status="error: Invalid image file"
        )
    
    with open(image_path, "wb") as f:
        f.write(file_bytes)
    
    image_title = title if title else file.filename
    paper_id = source_paper_id if source_paper_id else image_id  # Use image_id as fallback
    
    # Auto-generate caption using vision model if not provided
    if caption and caption.strip():
        image_caption = caption.strip()
    else:
        print(f"Auto-captioning image: {file.filename}")
        try:
            image_caption = image_captioner.caption_image(image_path)
            if not image_caption or len(image_caption) < 5:
                # Fallback if captioning fails
                image_caption = f"Image: {file.filename}"
        except Exception as e:
            print(f"Image captioning failed, using fallback: {e}")
            image_caption = f"Image: {file.filename}"
        
        # Enhance short captions
        if len(image_caption) < 20:
            image_caption = f"{file.filename}: {image_caption}"
    
    print(f"Image caption: {image_caption}")
    
    # Generate CLIP embedding
    print(f"Generating CLIP embedding for {file.filename}...")
    vector = clip_embedder.get_image_embedding(image_path)
    print(f"CLIP vector generated, size: {len(vector) if vector else 0}")
    
    if not vector:
        print(f"WARNING: Empty CLIP embedding for {file.filename}")
        return IngestImageResponse(
            image_id=image_id,
            chunks_created=0,
            status="error: Failed to generate image embedding"
        )
    
    figure_data = [{
        "paper_id": paper_id,
        "paper_title": image_title,
        "figure_id": image_id,
        "caption": image_caption,
        "page": 0,
        "file_path": image_path,
        "vector": vector
    }]
    
    # DB insert
    try:
        db.insert_figure_chunks(figure_data)
    except Exception as e:
        print(f"Failed to ingest image: {e}")
        return IngestImageResponse(
            image_id=image_id,
            chunks_created=0,
            status=f"error: {str(e)}"
        )
    
    return IngestImageResponse(
        image_id=image_id,
        chunks_created=1,
        status="success"
    )
