from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app


@patch("main.graph_db")
@patch("main.qdrant_db")
def test_health_healthy_when_all_services_ok(mock_qdrant_db, mock_graph_db):
    mock_qdrant_db.client.get_collections.return_value = MagicMock()
    mock_graph_db.driver.verify_connectivity.return_value = None

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["qdrant"] == "ok"
    assert body["neo4j"] == "ok"
    assert body["groq_api_key_configured"] is True


@patch("main.graph_db")
@patch("main.qdrant_db")
def test_health_degraded_when_qdrant_down(mock_qdrant_db, mock_graph_db):
    mock_qdrant_db.client.get_collections.side_effect = RuntimeError("connection refused")
    mock_graph_db.driver.verify_connectivity.return_value = None

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["qdrant"] == "unavailable"
    assert body["neo4j"] == "ok"


@patch("routers.query.generator")
@patch("routers.query.retrieve_context")
def test_query_endpoint_returns_generated_answer(mock_retrieve_context, mock_generator):
    mock_retrieve_context.return_value = (
        [{
            "chunk_id": "c1", "paper_id": "p1", "paper_title": "Paper", "authors": [],
            "year": None, "chunk_text": "text", "score": 0.9, "modality": "text",
            "start_time": None, "end_time": None,
        }],
        [],
        {"related_papers": [], "concepts": []},
    )
    mock_generator.generate_answer.return_value = "The answer is 42."

    with TestClient(app) as client:
        response = client.post("/query", json={"text": "what is the answer?"})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "The answer is 42."
    assert len(body["sources"]) == 1
    assert body["sources"][0]["chunk_id"] == "c1"


@patch("routers.query.retrieve_context")
def test_query_endpoint_returns_502_on_runtime_error(mock_retrieve_context):
    mock_retrieve_context.side_effect = RuntimeError("embedding service down")

    with TestClient(app) as client:
        response = client.post("/query", json={"text": "test"})

    assert response.status_code == 502


@patch("routers.query.generator")
@patch("routers.query.retrieve_context")
def test_query_endpoint_passes_use_graph_through(mock_retrieve_context, mock_generator):
    mock_retrieve_context.return_value = ([], [], {"related_papers": [], "concepts": []})
    mock_generator.generate_answer.return_value = "answer"

    with TestClient(app) as client:
        client.post("/query", json={"text": "q", "use_graph": False})

    assert mock_retrieve_context.call_args.kwargs["use_graph"] is False


@patch("routers.query.generator")
@patch("routers.query.retrieve_context")
def test_compare_endpoint_runs_both_variants(mock_retrieve_context, mock_generator):
    def fake_retrieve(text, top_k=None, rerank_top_n=None, use_graph=True):
        graph_context = {"related_papers": ["Other Paper"], "concepts": ["X"]} if use_graph else {"related_papers": [], "concepts": []}
        return [], [], graph_context

    mock_retrieve_context.side_effect = fake_retrieve
    mock_generator.generate_answer.return_value = "answer"

    with TestClient(app) as client:
        response = client.post("/query/compare", json={"text": "q"})

    assert response.status_code == 200
    body = response.json()
    assert body["with_graph"]["graph_context"]["related_papers"] == ["Other Paper"]
    assert body["without_graph"]["graph_context"]["related_papers"] == []
