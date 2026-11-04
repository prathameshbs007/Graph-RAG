"""Rank fusion for hybrid retrieval (Module 2).

Both functions take the two first-stage result lists as ``[(id, score), ...]``
ordered best-first and return ``[(id, fused_score), ...]`` ordered best-first.
"""

from typing import Iterable


# Present items are mapped into [_FLOOR, 1] rather than [0, 1]: otherwise the worst item
# of a list would score exactly like an item the retriever did not return at all, and
# alpha = 0 / 1 would no longer reduce to pure BM25 / pure dense ranking.
_FLOOR = 0.05


def _minmax(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    lo, hi = min(scores.values()), max(scores.values())
    if hi - lo < 1e-12:
        return {k: 1.0 for k in scores}
    return {k: _FLOOR + (1.0 - _FLOOR) * (v - lo) / (hi - lo) for k, v in scores.items()}


def fuse_alpha(
    bm25: Iterable[tuple[str, float]],
    dense: Iterable[tuple[str, float]],
    alpha: float,
) -> list[tuple[str, float]]:
    """alpha-weighted score fusion: ``alpha * dense + (1 - alpha) * bm25``.

    alpha = 0 is BM25 only, alpha = 1 is dense only (as in the report). Scores of
    each list are min-max normalised first because BM25 is unbounded while cosine
    similarity is not; an item missing from a list contributes 0 for that list.
    """
    alpha = min(1.0, max(0.0, alpha))
    b = _minmax(dict(bm25))
    d = _minmax(dict(dense))
    fused = {i: alpha * d.get(i, 0.0) + (1.0 - alpha) * b.get(i, 0.0) for i in set(b) | set(d)}
    return sorted(fused.items(), key=lambda kv: (-kv[1], kv[0]))


def fuse_rrf(
    bm25: Iterable[tuple[str, float]],
    dense: Iterable[tuple[str, float]],
    k: int = 60,
) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion: ``RRF(d) = sum_i 1 / (k + rank_i(d))`` (ranks start at 1)."""
    fused: dict[str, float] = {}
    for ranked in (bm25, dense):
        for rank, (item_id, _score) in enumerate(ranked, start=1):
            fused[item_id] = fused.get(item_id, 0.0) + 1.0 / (k + rank)
    return sorted(fused.items(), key=lambda kv: (-kv[1], kv[0]))
