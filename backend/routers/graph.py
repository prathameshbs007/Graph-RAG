from fastapi import APIRouter
from services.neo4j_client import graph_db

router = APIRouter(prefix="/graph", tags=["graph"])

@router.get("/nodes")
def get_nodes(limit: int = 200, node_type: str = None):
    query = f"MATCH (n{':' + node_type if node_type else ''}) RETURN n LIMIT {limit}"
    nodes = []
    with graph_db.driver.session() as session:
        res = session.run(query)
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
def get_edges(limit: int = 500, edge_type: str = None):
    type_filter = f":{edge_type}" if edge_type else ""
    query = f"MATCH (n)-[r{type_filter}]->(m) RETURN n.id AS source, m.id AS target, type(r) AS type LIMIT {limit}"
    edges = []
    with graph_db.driver.session() as session:
        res = session.run(query)
        for record in res:
            if record["source"] and record["target"]:
                edges.append({
                    "source": record["source"],
                    "target": record["target"],
                    "type": record["type"]
                })
    return {"edges": edges}
