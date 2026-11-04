"""Statistics for Section 4.2: mean with 95% bootstrap CI, paired significance tests,
ablation deltas, Cohen's kappa (judge vs human) and nDCG@k for the BEIR sanity check."""

import math
from typing import Sequence

import numpy as np


def _clean(values: Sequence[float]) -> np.ndarray:
    a = np.asarray([v for v in values if v is not None], dtype=float)
    return a[~np.isnan(a)]


def bootstrap_ci(values: Sequence[float], n_boot: int = 10000, alpha: float = 0.05, seed: int = 0) -> dict:
    """Mean and percentile bootstrap CI (resampling questions)."""
    a = _clean(values)
    if a.size == 0:
        return {"mean": float("nan"), "lo": float("nan"), "hi": float("nan"), "n": 0}
    rng = np.random.default_rng(seed)
    means = a[rng.integers(0, a.size, size=(n_boot, a.size))].mean(axis=1)
    lo, hi = np.percentile(means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return {"mean": float(a.mean()), "lo": float(lo), "hi": float(hi), "n": int(a.size)}


def paired_arrays(a: dict[str, float], b: dict[str, float]) -> tuple[np.ndarray, np.ndarray]:
    """Align two ``{question_id: score}`` maps on their common, non-missing questions."""
    ids = sorted(k for k in a.keys() & b.keys() if a[k] is not None and b[k] is not None
                 and not math.isnan(a[k]) and not math.isnan(b[k]))
    return np.array([a[i] for i in ids], dtype=float), np.array([b[i] for i in ids], dtype=float)


def paired_bootstrap(a: Sequence[float], b: Sequence[float], n_boot: int = 10000, seed: int = 0) -> dict:
    """Mean difference ``a - b`` over paired questions, its 95% CI, and a two-sided
    bootstrap p-value (how often the resampled mean difference crosses zero)."""
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    if d.size == 0:
        return {"diff": float("nan"), "lo": float("nan"), "hi": float("nan"), "p": float("nan"), "n": 0}
    rng = np.random.default_rng(seed)
    means = d[rng.integers(0, d.size, size=(n_boot, d.size))].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    p = 2 * min((means <= 0).mean(), (means >= 0).mean())
    return {"diff": float(d.mean()), "lo": float(lo), "hi": float(hi), "p": float(min(1.0, p)), "n": int(d.size)}


def wilcoxon_p(a: Sequence[float], b: Sequence[float]) -> float:
    """Wilcoxon signed-rank p-value; 1.0 when the two systems are identical."""
    from scipy.stats import wilcoxon

    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    if d.size == 0 or not np.any(d != 0):
        return 1.0
    return float(wilcoxon(d, zero_method="wilcox").pvalue)


def holm(pvalues: dict[str, float]) -> dict[str, float]:
    """Holm-Bonferroni adjusted p-values (several baselines are compared at once)."""
    items = sorted(pvalues.items(), key=lambda kv: kv[1])
    m = len(items)
    adjusted, running = {}, 0.0
    for rank, (name, p) in enumerate(items):
        running = max(running, min(1.0, (m - rank) * p))
        adjusted[name] = running
    return adjusted


def cohen_kappa(a: Sequence, b: Sequence) -> float:
    """Cohen's kappa for two raters on categorical labels."""
    a, b = list(a), list(b)
    if len(a) != len(b) or not a:
        raise ValueError("need two non-empty label lists of equal length")
    labels = sorted(set(a) | set(b), key=str)
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    expected = sum((a.count(l) / n) * (b.count(l) / n) for l in labels)
    if math.isclose(expected, 1.0):
        return 1.0 if math.isclose(observed, 1.0) else 0.0
    return (observed - expected) / (1 - expected)


def ndcg_at_k(ranked_ids: Sequence[str], relevance: dict[str, int], k: int = 10) -> float:
    """nDCG@k with graded relevance (BEIR convention: gain = rel, log2(rank + 1) discount)."""
    dcg = sum(relevance.get(doc, 0) / math.log2(i + 2) for i, doc in enumerate(ranked_ids[:k]))
    ideal = sorted(relevance.values(), reverse=True)[:k]
    idcg = sum(rel / math.log2(i + 2) for i, rel in enumerate(ideal))
    return dcg / idcg if idcg > 0 else 0.0
