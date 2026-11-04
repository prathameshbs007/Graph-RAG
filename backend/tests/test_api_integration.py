"""The real FastAPI app over live Weaviate + Neo4j (only Ollama / Groq / Cohere are faked)."""

import pytest
from fastapi.testclient import TestClient

from config import settings
from conftest import assert_disposable
from fakes import FakeLLM, fake_embed, fake_rerank_score
from synth import make_paper

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    assert_disposable(settings)
    from services import embedder
    from services.llm import llm
    from services.reranker import reranker

    mp = pytest.MonkeyPatch()
    mp.setattr(embedder, "_embed", fake_embed)
    mp.setattr(settings, "GROQ_API_KEY", "test-key")
    mp.setattr(llm, "chat", FakeLLM())
    mp.setattr(reranker, "score", fake_rerank_score)
    mp.setattr(settings, "FIGURES_DIR", str(tmp_path_factory.mktemp("figs")))
    mp.setattr(settings, "SEED_K", 2)

    import main

    with TestClient(main.app) as c:  # runs the lifespan: schema creation in both stores
        c.post("/admin/clear-db")
        yield c
        c.post("/admin/clear-db")
    mp.undo()


@pytest.fixture(scope="module")
def pdfs(tmp_path_factory):
    d = tmp_path_factory.mktemp("pdfs")
    body_a = "Hybrid retrieval combines bm25 keyword matching with dense embeddings and a reranker. " * 8
    body_b = "Dense embeddings are trained with contrastive learning for passage retrieval systems. " * 8
    make_paper(str(d / "a.pdf"), "Hybrid Retrieval With Reranker Feedback For Papers",
               [("Introduction", body_a), ("Method", body_a)],
               ["[1] X. Author. Neural Passage Retrieval With Dense Embeddings. SIGIR 2021."],
               "Figure 1: Architecture of the hybrid retriever.")
    make_paper(str(d / "b.pdf"), "Neural Passage Retrieval With Dense Embeddings",
               [("Introduction", body_b), ("Method", body_b)], ["[1] Z. Third. An unrelated padding reference entry. 2018."], None)
    return d


def test_health_and_systems(client):
    assert client.get("/health").json() == {"status": "healthy"}
    systems = {s["name"] for s in client.get("/query/systems").json()["systems"]}
    assert {"full", "b1_bm25", "b2_dense", "b3_static_hybrid", "b4_static_graph", "b5_flat_rerank"} <= systems


def test_ingest_upload_status_and_query(client, pdfs):
    ids = []
    for name in ("a.pdf", "b.pdf"):
        with open(pdfs / name, "rb") as f:
            r = client.post("/ingest/pdf", files={"file": (name, f, "application/pdf")},
                            data={"title": name, "authors": "Some Author, Other Person", "year": "2024"})
        assert r.status_code == 200 and r.json()["status"].startswith("queued")
        ids.append(r.json()["paper_id"])
    for pid in ids:  # TestClient runs background tasks before returning
        st = client.get(f"/ingest/status/{pid}").json()
        assert st["status"] == "done", st
        # the form title was just the filename, so the title found inside the PDF is used
        assert st["detail"]["title"] in ("Hybrid Retrieval With Reranker Feedback For Papers",
                                         "Neural Passage Retrieval With Dense Embeddings")
    assert client.get("/ingest/status/nope").status_code == 404
    assert len(client.get("/ingest/jobs").json()["jobs"]) >= 2

    r = client.post("/query", json={"text": "How are dense embeddings trained with contrastive learning?", "seed": 1})
    assert r.status_code == 200
    body = r.json()  # validated against QueryResponse
    assert body["sources"][0]["evidence_id"] == "E1" and "[E1]" in body["answer"]
    assert body["diagnostics"]["system"] == "full" and body["diagnostics"]["feedback"]["applied"]
    assert body["claim_stats"]["verified"] is True
    assert client.post("/query", json={"text": "x", "system": "bogus"}).status_code == 400


def test_graph_endpoint_is_consistent_and_exposes_weights(client):
    g = client.get("/graph").json()
    ids = {n["id"] for n in g["nodes"]}
    assert g["links"] and all(l["source"] in ids and l["target"] in ids for l in g["links"])
    learned = [l for l in g["links"] if l["type"] in ("CITES", "RELATED_TO", "MENTIONS")]
    assert learned and all("weight" in l and "pruned" in l for l in learned)
    assert client.get("/graph/nodes").json()["nodes"] and client.get("/graph/edges").json()["edges"]
    with_items = client.get("/graph", params={"include_items": True}).json()
    assert {n["label"] for n in with_items["nodes"]} & {"Chunk", "Figure"}


def test_admin_state_audit_snapshot_and_reset(client):
    state = client.get("/admin/state").json()
    assert 0.2 <= state["alpha"] <= 0.9 and state["vector_items"] > 0 and state["edges"]["MENTIONS"]["total"] > 0
    assert state["parameters"]["prune_below"] == 0.2

    events = client.get("/admin/audit", params={"limit": 50}).json()["events"]
    assert events and {"query_id", "old_weight", "new_weight", "kind"} <= set(events[0])
    assert client.get("/admin/audit", params={"kind": "prune"}).status_code == 200

    snap = client.get("/admin/snapshot").json()
    assert snap["edges"]
    assert client.post("/admin/reset-feedback").json()["alpha"] == 0.5
    assert client.get("/admin/audit").json()["events"] == []
    restored = client.post("/admin/snapshot", json=snap).json()["edges_restored"]
    assert restored == len(snap["edges"])
    assert client.post("/admin/restore-pruned", json={}).json() == {"restored": 0}


def test_clear_db_empties_everything(client):
    assert client.post("/admin/clear-db").json()["status"] == "success"
    state = client.get("/admin/state").json()
    assert state["vector_items"] == 0 and state["edges"] == {}
    r = client.post("/query", json={"text": "anything at all"})
    assert r.status_code == 200 and r.json()["sources"] == []
