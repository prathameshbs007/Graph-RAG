import logging

from fastapi import APIRouter, HTTPException
from models.query import QueryRequest, QueryResponse, SourceChunk, FigureReference, GraphContext
from services.retriever import retrieve_context
from services.generator import generator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])

@router.post("", response_model=QueryResponse)
async def query_endpoint(req: QueryRequest):
    try:
        sources, figures, graph_data = retrieve_context(req.text)
    except RuntimeError as e:
        logger.error("Retrieval failed for query: %s", e)
        raise HTTPException(status_code=502, detail="Embedding service unavailable") from e

    answer = generator.generate_answer(req.text, sources, graph_data)

    return QueryResponse(
        answer=answer,
        sources=sources,
        figures=figures,
        graph_context=graph_data
    )
