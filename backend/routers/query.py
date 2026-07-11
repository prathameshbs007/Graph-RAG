import asyncio
import logging

from fastapi import APIRouter, HTTPException

from models.query import QueryCompareResponse, QueryRequest, QueryResponse
from services.generator import generator
from services.retriever import retrieve_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])


def _run_query(text: str, top_k: int, rerank_top_n: int, use_graph: bool) -> QueryResponse:
    sources, figures, graph_data = retrieve_context(text, top_k=top_k, rerank_top_n=rerank_top_n, use_graph=use_graph)
    answer = generator.generate_answer(text, sources, graph_data)
    return QueryResponse(answer=answer, sources=sources, figures=figures, graph_context=graph_data)


@router.post("", response_model=QueryResponse)
async def query_endpoint(req: QueryRequest):
    try:
        return await asyncio.to_thread(_run_query, req.text, req.top_k, req.rerank_top_n, req.use_graph)
    except RuntimeError as e:
        logger.error("Retrieval failed for query: %s", e)
        raise HTTPException(status_code=502, detail="Embedding service unavailable") from e


@router.post("/compare", response_model=QueryCompareResponse)
async def query_compare_endpoint(req: QueryRequest):
    """Run the same query with and without graph context concurrently, so the
    frontend can render a side-by-side comparison of the graph's actual impact."""
    try:
        with_graph, without_graph = await asyncio.gather(
            asyncio.to_thread(_run_query, req.text, req.top_k, req.rerank_top_n, True),
            asyncio.to_thread(_run_query, req.text, req.top_k, req.rerank_top_n, False),
        )
    except RuntimeError as e:
        logger.error("Retrieval failed for compare query: %s", e)
        raise HTTPException(status_code=502, detail="Embedding service unavailable") from e
    return QueryCompareResponse(with_graph=with_graph, without_graph=without_graph)
