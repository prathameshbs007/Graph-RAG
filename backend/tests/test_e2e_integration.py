"""End-to-end: ingest real (synthetic) PDFs and audio into live Weaviate + Neo4j and run
queries through the actual pipeline. Only Ollama / Groq / Cohere are faked."""

import pytest

from config import settings
from conftest import assert_disposable
from fakes import FakeLLM, fake_embed, fake_rerank_score
from synth import make_paper

pytestmark = pytest.mark.integration

A_TITLE = "Hybrid Retrieval With Reranker Feedback For Scientific Papers"
B_TITLE = "Neural Passage Retrieval With Dense Embeddings"
C_TITLE = "Seasoning And Caring For Cast Iron Skillets At Home"

A_BODY = (
    "Hybrid retrieval combines bm25 keyword matching with dense embeddings so exact terms and paraphrases are "
    "both found. The reranker scores every candidate and the retrieval pipeline keeps the best passages. " * 5
)
B_BODY = (
    "Dense embeddings are trained with contrastive learning on question passage pairs. Approximate neighbor "
    "search over the embeddings returns the closest passages quickly for retrieval. " * 5
)
C_BODY = (
    "Cast iron skillets need seasoning with a thin layer of oil. Heat the skillets slowly and avoid soaking "
    "so the seasoning stays intact on the cooking surface. " * 5
)


@pytest.fixture(scope="module")
def kb(tmp_path_factory):
    assert_disposable(settings)
    from services import embedder, ingestion
    from services.llm import llm
    from services.neo4j_client import graph_db
    from services.reranker import reranker
    from services.weaviate_client import db

    mp = pytest.MonkeyPatch()
    fake_llm = FakeLLM()
    mp.setattr(embedder, "_embed", fake_embed)
    mp.setattr(settings, "GROQ_API_KEY", "test-key")
    mp.setattr(llm, "chat", fake_llm)
    mp.setattr(reranker, "score", fake_rerank_score)
    mp.setattr(settings, "CONCEPT_BATCH_SIZE", 2)
    mp.setattr(settings, "SEED_K", 2)  # the test corpus has 9 items; with 10 seeds the graph would have nothing left to reach

    db.reset()
    graph_db.clear()
    graph_db.ensure_schema()

    tmp = tmp_path_factory.mktemp("kb")
    figs = str(tmp / "figures")
    ids = {}
    specs = [
        ("A", A_TITLE, A_BODY, [f"[1] X. Author. {B_TITLE}. SIGIR 2021.", "[2] Y. Other. Some earlier long-winded unrelated reference title. 2019."],
         "Figure 1: Architecture of the hybrid retriever with a reranker feedback loop."),
        ("B", B_TITLE, B_BODY, ["[1] Z. Third. A sufficiently long and unrelated reference entry for padding. 2018."], None),
        ("C", C_TITLE, C_BODY, ["[1] Q. Cook. A cookbook about iron pans and kitchens in general. 2010."], None),
    ]
    jobs = {}
    for key, title, body, refs, caption in specs:
        pdf = str(tmp / f"{key}.pdf")
        make_paper(pdf, title, [("Introduction", body), ("Discussion", body)], refs, caption)
        ids[key] = f"paper-{key}"
        job = ingestion.new_job(ids[key], "pdf", title)
        ingestion.ingest_pdf(pdf, ids[key], title, ["Some Author"], 2024, figs, job)
        jobs[key] = job

    # a talk about paper B
    windows = [
        {"chunk_text": "In this talk we explain how contrastive learning trains dense embeddings for retrieval.",
         "start_time": 0.0, "end_time": 28.0},
        {"chunk_text": "Then we show approximate neighbor search over the embeddings at scale.",
         "start_time": 28.0, "end_time": 55.0},
    ]
    ajob = ingestion.new_job("talk-1", "audio", "Embeddings Talk")
    ingestion.ingest_audio("unused.wav", "talk-1", "Embeddings Talk", ids["B"],
                           transcribe=lambda p: (windows, 55.0, 2), job=ajob)
    yield {"ids": ids, "jobs": jobs, "audio_job": ajob, "llm": fake_llm, "db": db, "graph": graph_db}
    mp.undo()
    graph_db.clear()
    db.reset()


def test_ingestion_completed_everywhere(kb):
    for key, job in kb["jobs"].items():
        assert job.status == "done", job.error
        assert job.detail["chunks"] > 0 and job.detail["concept_mentions"] > 0
    assert kb["jobs"]["A"].detail["figures"] == 1
    # A cites B by title; A was ingested first, so the edge appears when B arrives (order independent)
    assert [j.detail["citation_edges"] for j in kb["jobs"].values()] == [0, 1, 0]
    assert kb["audio_job"].status == "done", kb["audio_job"].error

    g = kb["graph"]
    assert g.node_counts()["Paper"] == 3 and g.node_counts()["Talk"] == 1
    cites = g.run("MATCH (a:Paper)-[r:CITES]->(b:Paper) RETURN a.id AS a, b.id AS b, r.weight AS w")
    assert cites == [{"a": "paper-A", "b": "paper-B", "w": 0.5}]
    assert {r["w"] for r in g.run("MATCH ()-[r:MENTIONS|RELATED_TO|CITES]->() RETURN DISTINCT r.weight AS w")} == {0.5}
    # all three stores agree on the number of items
    n_items = g.run("MATCH (i:Item) RETURN count(i) AS n")[0]["n"]
    assert kb["db"].count() == n_items


def test_bm25_and_dense_are_separate_ranked_lists(kb):
    bm25 = kb["db"].bm25("contrastive learning embeddings", 5)
    assert bm25 and bm25[0]["paper_title"] in (B_TITLE, "Embeddings Talk")
    assert all(bm25[i]["score"] >= bm25[i + 1]["score"] for i in range(len(bm25) - 1))
    from services.embedder import embed_query

    dense = kb["db"].dense(embed_query("cast iron seasoning skillets"), 3)
    assert dense[0]["paper_title"] == C_TITLE and 0 <= dense[0]["score"] <= 1


def test_full_system_answers_cites_and_learns(kb):
    from services.pipeline import pipeline

    out = pipeline.answer("How are dense embeddings trained with contrastive learning?", system="full", learn=True, seed=1)
    d = out["diagnostics"]
    assert d["bm25_hits"] > 0 and d["dense_hits"] > 0 and d["seeds"] > 0
    assert d["reranked"] and d["fusion"] == "alpha"
    assert d["graph_reached"] > 0, "graph expansion should add candidates beyond the seeds"
    assert out["sources"] and out["sources"][0]["evidence_id"] == "E1"
    assert out["sources"][0]["score"] >= settings.RELEVANCE_CUTOFF
    assert "[E1]" in out["answer"] and out["sources"][0]["cited"]
    assert out["claim_stats"]["verified"] and out["claim_stats"]["supported"] >= 1
    # feedback was applied and is auditable
    assert d["feedback"]["applied"] and d["feedback"]["edges_updated"] > 0
    events = kb["graph"].list_events(limit=500, query_id=out["query_id"])
    assert len(events) >= d["feedback"]["edges_updated"]
    assert all(e["e"]["old_weight"] != e["e"]["new_weight"] for e in events if e["e"]["kind"] == "edge")
    assert settings.ALPHA_MIN <= kb["graph"].get_alpha() <= settings.ALPHA_MAX


def test_learn_false_freezes_the_memory(kb):
    from services.pipeline import pipeline

    before = kb["graph"].export_state()
    pipeline.answer("How are dense embeddings trained with contrastive learning?", system="full", learn=False, seed=1)
    after = kb["graph"].export_state()
    key = lambda e: (e["type"], e["src"], e["dst"])  # noqa: E731
    assert sorted(before["edges"], key=key) == sorted(after["edges"], key=key)
    assert before["alpha"] == after["alpha"]


def test_irrelevant_query_yields_insufficient_evidence_without_calling_llm(kb):
    from services.pipeline import pipeline

    calls_before = list(kb["llm"].calls)
    out = pipeline.answer("quantum chromodynamics lattice gauge", system="full", learn=False)
    assert out["sources"] == [] and out["answer"].lower().startswith("insufficient evidence")
    assert kb["llm"].calls == calls_before


def test_baselines_are_the_same_pipeline_with_parts_switched_off(kb):
    from services.pipeline import pipeline

    q = "contrastive learning dense embeddings"
    b1 = pipeline.answer(q, system="b1_bm25")["diagnostics"]
    assert (b1["dense_hits"], b1["graph_reached"], b1["reranked"]) == (0, 0, False) and b1["bm25_hits"] > 0
    b2 = pipeline.answer(q, system="b2_dense")["diagnostics"]
    assert (b2["bm25_hits"], b2["graph_reached"], b2["reranked"]) == (0, 0, False) and b2["dense_hits"] > 0
    b3 = pipeline.answer(q, system="b3_static_hybrid")["diagnostics"]
    assert b3["alpha"] == 0.5 and not b3["reranked"] and b3["graph_reached"] == 0
    b4 = pipeline.answer(q, system="b4_static_graph", seed=3)["diagnostics"]
    assert b4["graph_reached"] > 0 and b4["reranked"] and not b4["feedback"]["applied"]
    b5 = pipeline.answer(q, system="b5_flat_rerank")["diagnostics"]
    assert b5["reranked"] and b5["graph_reached"] == 0 and not b5["feedback"]["applied"]
    with pytest.raises(ValueError):
        pipeline.answer(q, system="nope")


def test_figure_citation_carries_bbox_and_crop_url(kb):
    from services.pipeline import pipeline

    out = pipeline.answer("architecture of the hybrid retriever with reranker feedback loop figure", learn=False)
    figs = out["figures"]
    assert figs, "the captioned figure should be retrieved"
    f = figs[0]
    assert f["caption"].startswith("Figure 1") and len(f["bbox"]) == 4 and f["url"].startswith("/figures/")
    assert f["page"] == 1 and f["evidence_id"].startswith("E")


def test_audio_citation_has_timestamps(kb):
    from services.pipeline import pipeline

    out = pipeline.answer("talk about contrastive learning of dense embeddings", learn=False)
    audio = [s for s in out["sources"] if s["modality"] == "audio"]
    assert audio and audio[0]["start_time"] == 0.0 and audio[0]["end_time"] == 28.0
    assert "00:00-00:28" in audio[0]["location"]


def test_unsupported_claims_are_flagged_then_removed(kb, monkeypatch):
    from services.pipeline import pipeline

    q = "FABRICATE: how are dense embeddings trained with contrastive learning?"
    out = pipeline.answer(q, learn=False)
    assert out["claim_stats"]["supported"] == 1 and out["claim_stats"]["unsupported"] == 1
    assert "cheese" in out["answer"]  # flag mode keeps the text but marks it
    assert [c["verdict"] for c in out["claims"]] == ["supported", "unsupported"]

    monkeypatch.setattr(settings, "VERIFY_MODE", "remove")
    out = pipeline.answer(q, learn=False)
    assert "cheese" not in out["answer"] and "[E1]" in out["answer"]


def test_repeated_feedback_moves_weights_both_ways_and_keeps_alpha_bounded(kb):
    from services.pipeline import pipeline

    g = kb["graph"]
    g.reset_feedback()
    queries = ["dense embeddings contrastive learning", "reranker retrieval pipeline passages", "approximate neighbor search embeddings"]
    for i in range(24):
        pipeline.answer(queries[i % 3], system="full", learn=True, seed=i, verify=False)
    weights = [e["weight"] for e in g.export_state()["edges"]]
    assert any(w < 0.5 for w in weights), "irrelevant graph paths should lose weight"
    assert any(w > 0.5 for w in weights), "paths to relevant passages should gain weight"
    assert settings.ALPHA_MIN <= g.get_alpha() <= settings.ALPHA_MAX
    stats = g.edge_stats()
    assert sum(s["visits"] for s in stats.values()) > 0
    # a pruned edge is soft-deleted: flagged, never walked again, and restorable
    pruned = sum(s["pruned"] for s in stats.values())
    if pruned:
        assert g.restore_pruned() == pruned
    # the audit log explains every change
    assert len(g.list_events(limit=5000)) > 0
