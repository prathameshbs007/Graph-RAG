"""Module 3: reranker feedback, self-pruning and alpha adaptation.

The reranker's relevance score ``s`` (0..1) is the learning signal. This module has
two layers:

* pure functions implementing the exact update rules of the report, and
* ``FeedbackEngine`` which applies them to a graph store and writes the audit log.
"""

from dataclasses import dataclass, field
from typing import Iterable, Optional
import time

from config import settings


# ---------------------------------------------------------------- pure rules
def update_weight(weight: float, score: float, visits: int, lr: float = 0.1) -> tuple[float, int]:
    """``w = (1 - lr) * w + lr * s`` and ``visits += 1`` (an exponential moving average).

    One poor score can only move a weight by ``lr * (w - s)`` so a single bad query
    cannot destroy a good edge, while repeated poor scores drive it down.
    """
    return (1.0 - lr) * weight + lr * score, visits + 1


def should_prune(weight: float, visits: int, min_visits: int = 5, below: float = 0.2) -> bool:
    """Soft-delete rule: enough evidence (``visits``) and still a weak edge."""
    return visits >= min_visits and weight < below


def update_alpha(
    alpha: float,
    s_dense: Optional[float],
    s_bm25: Optional[float],
    rate: float = 0.05,
    lo: float = 0.2,
    hi: float = 0.9,
) -> float:
    """``alpha = clip(alpha + rate * (S_d - S_b), lo, hi)``.

    ``S_d`` / ``S_b`` are the mean reranker scores of top results found *only* by
    dense / BM25 search. ``None`` means no such result exists in this query, which is
    treated as a score of 0 (the retriever contributed nothing unique); if neither
    side has a result there is no evidence and alpha is returned unchanged.
    """
    if s_dense is None and s_bm25 is None:
        return alpha
    delta = rate * ((s_dense or 0.0) - (s_bm25 or 0.0))
    return min(hi, max(lo, alpha + delta))


def mean_exclusive_scores(
    scored: Iterable[tuple[frozenset, float]],
) -> tuple[Optional[float], Optional[float]]:
    """From ``(retrievers_that_found_it, score)`` return ``(S_d, S_b)``.

    Only items found by exactly one first-stage retriever count.
    """
    dense_only: list[float] = []
    bm25_only: list[float] = []
    for retrievers, score in scored:
        if retrievers == frozenset({"dense"}):
            dense_only.append(score)
        elif retrievers == frozenset({"bm25"}):
            bm25_only.append(score)
    mean = lambda xs: (sum(xs) / len(xs)) if xs else None  # noqa: E731
    return mean(dense_only), mean(bm25_only)


@dataclass
class EdgeRef:
    """An edge on a graph path. ``eid`` is the database element id."""

    eid: str
    type: str
    src: str
    dst: str
    weight: float  # weight at traversal time


def aggregate_edge_scores(
    path_scores: Iterable[tuple[Iterable[EdgeRef], float]],
) -> dict[str, tuple[EdgeRef, float]]:
    """Collapse "path -> candidate score" into one score per edge.

    An edge shared by several candidates in the same query (e.g. a concept that
    leads to five chunks) is visited once, with the *mean* score of the candidates
    it led to. Counting it five times would let a single query satisfy the
    ``visits >= 5`` pruning condition on its own.
    """
    bucket: dict[str, tuple[EdgeRef, list[float]]] = {}
    for edges, score in path_scores:
        for e in edges:
            if e.eid not in bucket:
                bucket[e.eid] = (e, [])
            bucket[e.eid][1].append(score)
    return {eid: (e, sum(v) / len(v)) for eid, (e, v) in bucket.items()}


# ------------------------------------------------------------------- engine
@dataclass
class FeedbackReport:
    edges_updated: int = 0
    edges_pruned: int = 0
    alpha_before: float = 0.5
    alpha_after: float = 0.5
    applied: bool = False
    events: list[dict] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "applied": self.applied,
            "edges_updated": self.edges_updated,
            "edges_pruned": self.edges_pruned,
            "alpha_before": round(self.alpha_before, 4),
            "alpha_after": round(self.alpha_after, 4),
        }


class FeedbackEngine:
    """Applies reranker scores to the graph store and alpha, logging every change."""

    def __init__(self, graph, cfg=settings):
        self.graph = graph
        self.cfg = cfg

    def apply(
        self,
        query_id: str,
        query: str,
        path_scores: list[tuple[list[EdgeRef], float]],
        alpha: float,
        retriever_scores: list[tuple[frozenset, float]],
        adapt_alpha: bool = True,
    ) -> FeedbackReport:
        c = self.cfg
        report = FeedbackReport(alpha_before=alpha, alpha_after=alpha, applied=True)
        now = time.time()

        # ---- edge weights + pruning
        per_edge = aggregate_edge_scores(path_scores)
        if per_edge:
            states = self.graph.get_edge_states(list(per_edge))
            updates, events = [], []
            for eid, (ref, score) in per_edge.items():
                st = states.get(eid)
                if st is None or st.get("pruned"):
                    continue  # edge vanished or was pruned meanwhile
                old_w, old_v = st["weight"], st["visits"]
                new_w, new_v = update_weight(old_w, score, old_v, c.EDGE_LR)
                pruned = should_prune(new_w, new_v, c.PRUNE_MIN_VISITS, c.PRUNE_BELOW)
                updates.append({"eid": eid, "weight": new_w, "visits": new_v, "pruned": pruned})
                events.append(
                    {
                        "ts": now,
                        "query_id": query_id,
                        "query": query,
                        "kind": "prune" if pruned else "edge",
                        "edge_type": st["type"],
                        "src": st["src"],
                        "dst": st["dst"],
                        "old_weight": old_w,
                        "new_weight": new_w,
                        "visits": new_v,
                        "score": score,
                    }
                )
                report.edges_updated += 1
                report.edges_pruned += int(pruned)
            if updates:
                self.graph.write_edge_states(updates)
            report.events.extend(events)

        # ---- alpha
        if adapt_alpha:
            s_d, s_b = mean_exclusive_scores(retriever_scores)
            new_alpha = update_alpha(alpha, s_d, s_b, c.ALPHA_RATE, c.ALPHA_MIN, c.ALPHA_MAX)
            if new_alpha != alpha:
                self.graph.set_alpha(new_alpha)
                report.events.append(
                    {
                        "ts": now,
                        "query_id": query_id,
                        "query": query,
                        "kind": "alpha",
                        "edge_type": "alpha",
                        "src": "bm25",
                        "dst": "dense",
                        "old_weight": alpha,
                        "new_weight": new_alpha,
                        "visits": 0,
                        "score": (s_d or 0.0) - (s_b or 0.0),
                    }
                )
            report.alpha_after = new_alpha

        if report.events:
            self.graph.log_events(report.events)
        return report
