from fastapi import APIRouter
from models.query import QueryRequest, QueryResponse, SourceChunk, FigureReference, GraphContext
from services.retriever import retrieve_context
from services.generator import generator
from services.processing_status import processing_tracker

router = APIRouter(prefix="/query", tags=["query"])

@router.post("", response_model=QueryResponse)
async def query_endpoint(req: QueryRequest):
    sources, figures, graph_data = retrieve_context(req.text)
    
    answer = generator.generate_answer(req.text, sources, graph_data, figures=figures)
    
    return QueryResponse(
        answer=answer,
        sources=sources,
        figures=figures,
        graph_context=graph_data
    )

@router.get("/status/{file_id}")
async def get_processing_status(file_id: str):
    """Get the processing status of an ingested file"""
    return processing_tracker.get_status(file_id)

@router.get("/status")
async def get_all_processing_status():
    """Get all processing statuses"""
    return processing_tracker.get_all_statuses()
