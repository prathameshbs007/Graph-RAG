import random

import pytest

from services.feedback import FeedbackEngine
from services.neo4j_client import Neo4jDB

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def g():
    db = Neo4jDB()
    db.ensure_schema()
    yield db
    db.clear()
    db.close()


@pytest.fixture(autouse=True)
def fresh(g):
    g.clear()
    g.ensure_schema()
    # P1 "Graph retrieval for science papers" cites P2 "Attention is all you need"
    g.upsert_paper("P2", "Attention Is All You Need", 2017, ["Vaswani"], [])
    g.upsert_paper("P1", "Graph Retrieval For Science", 2024, ["Alice", "Bob"],
                   ["[1] A. Vaswani et al. Attention is all you need. NeurIPS 2017."])
    g.add_items("Paper", "P1", "Chunk", [
        {"id": f"P1:t{i}", "modality": "text", "page": 1, "chunk_index": i, "section": "Intro"} for i in range(3)])
    g.add_items("Paper", "P2", "Chunk", [
        {"id": f"P2:t{i}", "modality": "text", "page": 1, "chunk_index": i, "section": "Intro"} for i in range(2)])
    g.add_items("Paper", "P1", "Figure", [
        {"id": "P1_p2_f0", "modality": "image", "page": 2, "chunk_index": None, "section": None}])
    g.add_concepts(
        mentions=[
            ("P1:t0", "bm25", "BM25"), ("P1:t0", "dense retrieval", "dense retrieval"),
            ("P1:t1", "bm25", "BM25"),
            ("P1:t2", "reranking", "reranking"),
            ("P2:t0", "reranking", "reranking"),
            ("P1_p2_f0", "dense retrieval", "dense retrieval"),
        ],
        relations=[("bm25", "reranking", "feeds")],
    )
    g.link_citations("P1")


def test_schema_and_citation_edges(g):
    rows = g.run("MATCH (a:Paper)-[r:CITES]->(b:Paper) RETURN a.id AS a, b.id AS b, r.weight AS w, r.visits AS v, r.pruned AS p")
    assert rows == [{"a": "P1", "b": "P2", "w": 0.5, "v": 0, "p": False}]
    # all learned edges start at 0.5
    ws = g.run("MATCH ()-[r:MENTIONS|RELATED_TO|CITES]->() RETURN DISTINCT r.weight AS w")
    assert ws == [{"w": 0.5}]
    # re-linking is idempotent
    g.link_citations("P2")
    assert g.run("MATCH ()-[r:CITES]->() RETURN count(r) AS n")[0]["n"] == 1


def test_traversal_reaches_all_three_path_kinds(g):
    reached = g.traverse(["P1:t0"], rng=random.Random(0), explore_prob=0.0)
    # co-mention (bm25 -> P1:t1, dense retrieval -> figure), relatedness (bm25~reranking -> P1:t2, P2:t0),
    # citation (P1 cites P2 -> P2:t0 and P2:t1)
    assert set(reached) == {"P1:t1", "P1_p2_f0", "P1:t2", "P2:t0", "P2:t1"}
    assert [e.type for e in reached["P1:t1"].paths[0]] == ["MENTIONS", "MENTIONS"]
    kinds = {tuple(e.type for e in p) for p in reached["P1:t2"].paths}
    assert ("MENTIONS", "RELATED_TO", "MENTIONS") in kinds
    assert ("CITES",) in {tuple(e.type for e in p) for p in reached["P2:t1"].paths}
    assert "BM25" in reached["P1:t1"].concepts
    assert "Attention Is All You Need" in reached["P2:t1"].papers
    assert "P1:t0" not in reached  # seeds are not returned


def test_weak_edges_skipped_unless_explored_and_pruned_never(g):
    reached = g.traverse(["P1:t0"], rng=random.Random(0), explore_prob=0.0)
    bm25_edge = reached["P1:t1"].paths[0][0]  # P1:t0 -MENTIONS-> bm25
    g.write_edge_states([{"eid": bm25_edge.eid, "weight": 0.1, "visits": 2, "pruned": False}])

    weak = g.traverse(["P1:t0"], rng=random.Random(0), explore_prob=0.0)
    assert "P1:t1" not in weak  # path through the weak edge is cut
    assert "P1_p2_f0" in weak  # other paths unaffected

    explored = g.traverse(["P1:t0"], rng=random.Random(0), explore_prob=1.0)
    assert "P1:t1" in explored  # exploration re-admits a weak (un-pruned) edge

    g.write_edge_states([{"eid": bm25_edge.eid, "weight": 0.1, "visits": 9, "pruned": True}])
    pruned = g.traverse(["P1:t0"], rng=random.Random(0), explore_prob=1.0)
    assert "P1:t1" not in pruned  # a pruned edge is never followed, even when exploring


def test_exploration_rate_is_about_five_percent(g):
    reached = g.traverse(["P1:t0"], rng=random.Random(0), explore_prob=0.0)
    eid = reached["P1:t1"].paths[0][0].eid
    g.write_edge_states([{"eid": eid, "weight": 0.1, "visits": 1, "pruned": False}])
    hits = sum("P1:t1" in g.traverse(["P1:t0"], rng=random.Random(i), explore_prob=0.05) for i in range(200))
    # P1:t1 also has a second path edge (P1:t1 -MENTIONS-> bm25 is r2, strong) so only r1 gates it
    assert 1 <= hits <= 30


def test_feedback_engine_roundtrip_on_real_graph(g):
    reached = g.traverse(["P1:t0"], rng=random.Random(0), explore_prob=0.0)
    path = reached["P2:t1"].paths[0]  # the CITES edge
    eng = FeedbackEngine(g)
    for i in range(9):  # irrelevant every time -> eventually pruned
        eng.apply(f"q{i}", "attention?", [(path, 0.0)], g.get_alpha(), [])
    st = g.get_edge_states([path[0].eid])[path[0].eid]
    assert st["pruned"] is True and st["visits"] == 9 and st["weight"] < 0.2
    assert "P2:t1" not in g.traverse(["P1:t0"], rng=random.Random(0), explore_prob=1.0)

    events = g.list_events(limit=50, kind="prune")
    assert len(events) == 1 and events[0]["e"]["edge_type"] == "CITES"
    assert len(g.list_events(limit=100)) == 9
    stats = g.edge_stats()
    assert stats["CITES"]["pruned"] == 1

    assert g.restore_pruned() == 1
    assert "P2:t1" in g.traverse(["P1:t0"], rng=random.Random(0), explore_prob=0.0)


def test_alpha_state_and_snapshot_roundtrip(g):
    assert g.get_alpha() == 0.5
    g.set_alpha(0.73)
    assert g.get_alpha() == pytest.approx(0.73)

    reached = g.traverse(["P1:t0"], rng=random.Random(0), explore_prob=0.0)
    e = reached["P1:t1"].paths[0][0]
    g.write_edge_states([{"eid": e.eid, "weight": 0.9, "visits": 4, "pruned": False}])
    snap = g.export_state()
    assert snap["alpha"] == pytest.approx(0.73)

    g.reset_feedback()
    assert g.get_alpha() == 0.5
    assert g.get_edge_states([e.eid])[e.eid]["weight"] == 0.5
    n = g.import_state(snap)
    assert n == len(snap["edges"]) > 0
    assert g.get_alpha() == pytest.approx(0.73)
    assert g.get_edge_states([e.eid])[e.eid]["weight"] == pytest.approx(0.9)


def test_viz_graph_is_consistent(g):
    viz = g.viz_graph(include_items=True)
    ids = {n["id"] for n in viz["nodes"]}
    assert viz["links"] and all(l["source"] in ids and l["target"] in ids for l in viz["links"])
    labels = {n["label"] for n in viz["nodes"]}
    assert {"Paper", "Author", "Concept", "Chunk", "Figure"} <= labels
    assert "FeedbackEvent" not in labels and "SystemState" not in labels
    assert any(l["type"] == "CITES" and l["weight"] == 0.5 for l in viz["links"])
