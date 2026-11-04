import pytest

from services.chunking import chunk_words, words_per_chunk
from services.fusion import fuse_alpha, fuse_rrf
from services.feedback import (
    EdgeRef,
    FeedbackEngine,
    aggregate_edge_scores,
    mean_exclusive_scores,
    should_prune,
    update_alpha,
    update_weight,
)


# ------------------------------------------------------------------ chunking
def test_chunking_size_and_overlap():
    text = " ".join(f"w{i}" for i in range(1000))
    chunks = chunk_words(text, 300, 0.15)
    win = words_per_chunk(300)
    assert all(len(c.split()) <= win for c in chunks)
    assert len(chunks[0].split()) == win
    # 15% overlap: tail of chunk i == head of chunk i+1
    overlap = int(win * 0.15)
    assert chunks[0].split()[-overlap:] == chunks[1].split()[:overlap]
    # every word is covered
    covered = set(" ".join(chunks).split())
    assert covered == set(text.split())


def test_chunking_no_tail_duplicate_and_empty():
    assert chunk_words("   ", 300, 0.15) == []
    short = "a b c"
    assert chunk_words(short) == ["a b c"]
    win = words_per_chunk(300)
    exact = " ".join(["x"] * win)
    assert len(chunk_words(exact)) == 1


# ------------------------------------------------------------------- fusion
def test_alpha_extremes_match_single_retrievers():
    bm25 = [("a", 9.0), ("b", 5.0), ("c", 1.0)]
    dense = [("c", 0.9), ("b", 0.8), ("d", 0.5)]
    assert [i for i, _ in fuse_alpha(bm25, dense, 0.0)][:3] == ["a", "b", "c"]
    assert [i for i, _ in fuse_alpha(bm25, dense, 1.0)][:3] == ["c", "b", "d"]


def test_alpha_is_clamped_and_midpoint_blends():
    bm25 = [("a", 10.0), ("b", 0.0)]
    dense = [("b", 1.0), ("a", 0.0)]
    out = dict(fuse_alpha(bm25, dense, 0.5))
    assert out["a"] == pytest.approx(out["b"])  # symmetric inputs, alpha = 0.5
    assert fuse_alpha(bm25, dense, 5.0) == fuse_alpha(bm25, dense, 1.0)


def test_rrf_formula():
    bm25 = [("a", 3), ("b", 2)]
    dense = [("b", 0.9), ("c", 0.8)]
    out = dict(fuse_rrf(bm25, dense, k=60))
    assert out["a"] == pytest.approx(1 / 61)
    assert out["b"] == pytest.approx(1 / 62 + 1 / 61)
    assert out["c"] == pytest.approx(1 / 62)
    assert list(dict(fuse_rrf(bm25, dense)))[0] == "b"


# ---------------------------------------------------------------- feedback
def test_update_weight_is_moving_average():
    w, v = update_weight(0.5, 0.0, 0)
    assert (round(w, 6), v) == (0.45, 1)
    w, v = update_weight(0.5, 1.0, 3)
    assert (round(w, 6), v) == (0.55, 4)


def test_one_bad_query_cannot_prune_but_repeated_ones_do():
    w, v = 0.5, 0
    pruned_at = None
    for n in range(1, 30):
        w, v = update_weight(w, 0.0, v)
        if should_prune(w, v):
            pruned_at = n
            break
    assert pruned_at == 9  # 0.5 * 0.9**9 = 0.1937 < 0.2 is the first time below 0.2
    # weak but too few visits -> not pruned
    assert not should_prune(0.05, 4)
    # many visits but healthy -> not pruned
    assert not should_prune(0.6, 50)


def test_good_scores_keep_edge_alive_and_raise_it():
    w, v = 0.5, 0
    for _ in range(20):
        w, v = update_weight(w, 0.9, v)
    assert w > 0.8 and not should_prune(w, v)


def test_update_alpha_direction_clipping_and_no_evidence():
    assert update_alpha(0.5, 0.8, 0.2) == pytest.approx(0.5 + 0.05 * 0.6)
    assert update_alpha(0.5, 0.2, 0.8) == pytest.approx(0.5 - 0.05 * 0.6)
    assert update_alpha(0.89, 1.0, 0.0) == 0.9  # clipped at hi
    assert update_alpha(0.21, 0.0, 1.0) == 0.2  # clipped at lo
    assert update_alpha(0.5, None, None) == 0.5
    # one-sided evidence: missing side counts as 0
    assert update_alpha(0.5, 0.6, None) == pytest.approx(0.5 + 0.05 * 0.6)


def test_mean_exclusive_scores_ignores_shared_items():
    scored = [
        (frozenset({"dense"}), 0.8),
        (frozenset({"dense"}), 0.4),
        (frozenset({"bm25"}), 0.1),
        (frozenset({"bm25", "dense"}), 0.99),
        (frozenset({"graph"}), 0.7),
    ]
    s_d, s_b = mean_exclusive_scores(scored)
    assert s_d == pytest.approx(0.6) and s_b == pytest.approx(0.1)
    assert mean_exclusive_scores([]) == (None, None)


def test_aggregate_edge_scores_counts_a_shared_edge_once_with_mean():
    shared = EdgeRef("e1", "MENTIONS", "x", "c", 0.5)
    own_a = EdgeRef("e2", "MENTIONS", "a", "c", 0.5)
    own_b = EdgeRef("e3", "MENTIONS", "b", "c", 0.5)
    agg = aggregate_edge_scores([([shared, own_a], 0.8), ([shared, own_b], 0.2)])
    assert agg["e1"][1] == pytest.approx(0.5)
    assert agg["e2"][1] == pytest.approx(0.8) and agg["e3"][1] == pytest.approx(0.2)
    assert len(agg) == 3


class FakeGraph:
    def __init__(self):
        self.edges = {"e1": dict(weight=0.5, visits=0, pruned=False, type="MENTIONS", src="a", dst="c")}
        self.alpha = 0.5
        self.events = []

    def get_edge_states(self, eids):
        return {e: dict(self.edges[e]) for e in eids if e in self.edges}

    def write_edge_states(self, updates):
        for u in updates:
            self.edges[u["eid"]].update(weight=u["weight"], visits=u["visits"], pruned=u["pruned"])

    def set_alpha(self, a):
        self.alpha = a

    def log_events(self, events):
        self.events.extend(events)


def test_engine_updates_prunes_logs_and_moves_alpha():
    g = FakeGraph()
    eng = FeedbackEngine(g)
    ref = EdgeRef("e1", "MENTIONS", "a", "c", 0.5)
    last = None
    for i in range(9):
        last = eng.apply(
            f"q{i}", "question", [([ref], 0.0)], g.alpha, [(frozenset({"bm25"}), 0.9), (frozenset({"dense"}), 0.1)]
        )
    assert g.edges["e1"]["pruned"] is True and g.edges["e1"]["visits"] == 9
    assert last.edges_pruned == 1
    assert g.alpha < 0.5  # BM25-only results scored higher -> shift toward BM25
    kinds = [e["kind"] for e in g.events]
    # alpha falls 0.04 per query and clips at 0.2 on the 8th, so the 9th logs no change
    assert kinds.count("prune") == 1 and kinds.count("edge") == 8 and kinds.count("alpha") == 8
    assert g.alpha == pytest.approx(0.2)
    first = next(e for e in g.events if e["kind"] == "edge")
    assert first["old_weight"] == 0.5 and first["new_weight"] == pytest.approx(0.45)
    # a pruned edge is never touched again
    eng.apply("qx", "question", [([ref], 1.0)], g.alpha, [])
    assert g.edges["e1"]["visits"] == 9


def test_engine_can_freeze_alpha():
    g = FakeGraph()
    eng = FeedbackEngine(g)
    rep = eng.apply("q", "q", [], 0.5, [(frozenset({"dense"}), 1.0)], adapt_alpha=False)
    assert g.alpha == 0.5 and rep.alpha_after == 0.5
