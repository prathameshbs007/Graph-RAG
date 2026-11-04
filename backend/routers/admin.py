from typing import Optional

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from config import settings
from services.neo4j_client import graph_db
from services.weaviate_client import db

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/clear-db")
def clear_database():
    """Clear all data (vectors, graph, learned weights, audit log, alpha)."""
    try:
        db.reset()
        graph_db.clear()
        graph_db.ensure_schema()
        return {"status": "success", "message": "Database cleared successfully"}
    except Exception as e:  # noqa: BLE001
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e), "detail": f"Failed to clear database: {e}"},
        )


@router.get("/state")
def state():
    """Self-pruning memory at a glance: alpha, edge counts, pruned edges, store sizes."""
    return {
        "alpha": graph_db.get_alpha(),
        "edges": graph_db.edge_stats(),
        "nodes": graph_db.node_counts(),
        "vector_items": db.count(),
        "feedback_enabled": settings.FEEDBACK_ENABLED,
        "parameters": {
            "edge_lr": settings.EDGE_LR,
            "traverse_min": settings.EDGE_TRAVERSE_MIN,
            "explore_prob": settings.EXPLORE_PROB,
            "prune_below": settings.PRUNE_BELOW,
            "prune_min_visits": settings.PRUNE_MIN_VISITS,
            "relevance_cutoff": settings.RELEVANCE_CUTOFF,
            "context_size": settings.CONTEXT_SIZE,
            "alpha_rate": settings.ALPHA_RATE,
            "alpha_range": [settings.ALPHA_MIN, settings.ALPHA_MAX],
            "fusion": settings.FUSION,
        },
    }


@router.get("/audit")
def audit_log(limit: int = 100, kind: Optional[str] = None, query_id: Optional[str] = None):
    """Every weight change: query, edge, old and new weight (kind: edge | prune | alpha)."""
    rows = graph_db.list_events(limit=min(limit, 2000), kind=kind, query_id=query_id)
    return {"events": [r["e"] for r in rows]}


@router.post("/reset-feedback")
def reset_feedback(clear_log: bool = True):
    """Return all learned weights to 0.5 and alpha to its start value."""
    graph_db.reset_feedback(clear_log=clear_log)
    return {"status": "success", "alpha": graph_db.get_alpha()}


@router.post("/restore-pruned")
def restore_pruned(eid: Optional[str] = Body(default=None, embed=True)):
    """Un-prune one edge (by element id) or, with no id, all pruned edges."""
    return {"restored": graph_db.restore_pruned(eid)}


@router.get("/snapshot")
def export_snapshot():
    """Export learned edge weights + alpha (the 'frozen' memory used by the evaluation)."""
    return graph_db.export_state()


@router.post("/snapshot")
def import_snapshot(snapshot: dict = Body(...)):
    return {"edges_restored": graph_db.import_state(snapshot)}
