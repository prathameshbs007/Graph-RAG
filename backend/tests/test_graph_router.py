from fastapi.testclient import TestClient

from main import app


def test_get_nodes_rejects_invalid_node_type():
    with TestClient(app) as client:
        response = client.get("/graph/nodes", params={"node_type": "Paper) DETACH DELETE n //"})
    assert response.status_code == 422


def test_get_nodes_rejects_out_of_range_limit():
    with TestClient(app) as client:
        response = client.get("/graph/nodes", params={"limit": 5000})
    assert response.status_code == 422


def test_get_edges_rejects_invalid_edge_type():
    with TestClient(app) as client:
        response = client.get("/graph/edges", params={"edge_type": "WROTE]-(m) DETACH DELETE m //"})
    assert response.status_code == 422


def test_get_edges_rejects_non_integer_limit():
    with TestClient(app) as client:
        response = client.get("/graph/edges", params={"limit": "5 MATCH (n) DETACH DELETE n"})
    assert response.status_code == 422
