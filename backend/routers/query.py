import logging

from fastapi import APIRouter, HTTPException

from models.query import QueryRequest, QueryResponse
from services.generator import generator
from services.retriever import retrieve_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])

@router.post("", response_model=QueryResponse)
async def query_endpoint(req: QueryRequest):
    try:
        sources, figures, graph_data = retrieve_context(req.text, top_k=req.top_k, rerank_top_n=req.rerank_top_n)
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
