from fastapi import APIRouter
from models.query import QueryRequest, QueryResponse, SourceChunk, FigureReference, GraphContext
from services.retriever import retrieve_context
from services.generator import generator

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
