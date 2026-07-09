from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from services.neo4j_client import graph_db

router = APIRouter(prefix="/graph", tags=["graph"])

VALID_NODE_TYPES = {"Paper", "Author", "Concept"}
VALID_EDGE_TYPES = {"WROTE", "CITES", "HAS_CONCEPT"}


@router.get("/nodes")
def get_nodes(limit: int = Query(200, ge=1, le=1000), node_type: Optional[str] = None):
    if node_type is not None and node_type not in VALID_NODE_TYPES:
        raise HTTPException(status_code=422, detail=f"node_type must be one of {sorted(VALID_NODE_TYPES)}")

    label_filter = f":{node_type}" if node_type else ""
    query = f"MATCH (n{label_filter}) RETURN n LIMIT $limit"
    nodes = []
    with graph_db.driver.session() as session:
        res = session.run(query, limit=limit)
        for record in res:
            n = record["n"]
            nodes.append({
                "id": n.get("id"),
                "label": list(n.labels)[0] if n.labels else "Unknown",
                "title": n.get("title", ""),
                "name": n.get("name", "")
            })
    return {"nodes": nodes}


@router.get("/edges")
def get_edges(limit: int = Query(500, ge=1, le=2000), edge_type: Optional[str] = None):
    if edge_type is not None and edge_type not in VALID_EDGE_TYPES:
        raise HTTPException(status_code=422, detail=f"edge_type must be one of {sorted(VALID_EDGE_TYPES)}")

    type_filter = f":{edge_type}" if edge_type else ""
    query = f"MATCH (n)-[r{type_filter}]->(m) RETURN n.id AS source, m.id AS target, type(r) AS type LIMIT $limit"
    edges = []
    with graph_db.driver.session() as session:
        res = session.run(query, limit=limit)
        for record in res:
            if record["source"] and record["target"]:
                edges.append({
                    "source": record["source"],
                    "target": record["target"],
                    "type": record["type"]
                })
    return {"edges": edges}
