from fastapi import APIRouter, HTTPException

from models.query import QueryRequest, QueryResponse
from services.pipeline import SYSTEMS, pipeline

router = APIRouter(prefix="/query", tags=["query"])


# Plain ``def`` handlers run in FastAPI's thread pool; the pipeline does blocking network
# and database I/O and must not stall the event loop (other users, ingestion polling).
@router.post("", response_model=QueryResponse)
def query_endpoint(req: QueryRequest):
    try:
        return pipeline.answer(req.text, system=req.system, learn=req.learn, seed=req.seed, verify=req.verify)
    except ValueError as exc:  # unknown system name
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/systems")
def list_systems():
    return {
        "systems": [
            {
                "name": s.name,
                "description": s.description,
                "retriever": s.retriever,
                "graph": s.use_graph,
                "reranker": s.use_reranker,
                "feedback": s.feedback,
                "adaptive_alpha": s.adaptive_alpha,
            }
            for s in SYSTEMS.values()
        ]
    }
