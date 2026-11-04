from fastapi import APIRouter

from services.neo4j_client import graph_db

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("")
def get_graph(include_items: bool = False, concepts: int = 150):
    """Nodes and links together, so every link is guaranteed to have both endpoints.

    Learned edges (MENTIONS / RELATED_TO / CITES) carry ``weight``, ``visits`` and
    ``pruned`` so the explorer can show what the self-pruning memory has learned.
    """
    return graph_db.viz_graph(include_items=include_items, concept_limit=min(concepts, 1000))


@router.get("/nodes")
def get_nodes(include_items: bool = False):
    return {"nodes": graph_db.viz_graph(include_items=include_items)["nodes"]}


@router.get("/edges")
def get_edges(include_items: bool = False):
    return {"edges": graph_db.viz_graph(include_items=include_items)["links"]}
