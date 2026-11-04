import math

import pytest

from eval.splits import review_sample, stratified_split
from eval.stats import (
    bootstrap_ci,
    cohen_kappa,
    holm,
    ndcg_at_k,
    paired_arrays,
    paired_bootstrap,
    wilcoxon_p,
)


# ------------------------------------------------------------------- splits
def _rows(n_single=60, n_multi=40):
    rows = [{"id": f"s{i:03d}", "query_type": "single_hop"} for i in range(n_single)]
    return rows + [{"id": f"m{i:03d}", "query_type": "multi_hop"} for i in range(n_multi)]


def test_split_is_40_20_40_stratified_disjoint_and_deterministic():
    rows = _rows()
    sp = stratified_split(rows, seed=1)
    assert [len(sp[k]) for k in ("feedback", "development", "test")] == [40, 20, 40]
    ids = [r["id"] for k in sp for r in sp[k]]
    assert len(ids) == len(set(ids)) == 100  # disjoint and complete
    for name, singles in (("feedback", 24), ("development", 12), ("test", 24)):
        assert sum(r["query_type"] == "single_hop" for r in sp[name]) == singles
    assert stratified_split(rows, seed=1) == sp
    assert stratified_split(rows, seed=2) != sp


@pytest.mark.parametrize("n", [1, 2, 3, 7, 11, 199])
def test_split_sizes_always_sum_to_n(n):
    rows = [{"id": f"q{i}", "query_type": "single_hop" if i % 3 else "multi_hop"} for i in range(n)]
    sp = stratified_split(rows)
    assert sum(len(v) for v in sp.values()) == n


def test_review_sample_is_20_percent():
    rows = _rows()
    sample = review_sample(rows)
    assert len(sample) == 20 and len({r["id"] for r in sample}) == 20


# --------------------------------------------------------------- statistics
def test_bootstrap_ci_contains_mean_and_shrinks_with_n():
    small = bootstrap_ci([0.2, 0.9, 0.5, 0.7, 0.4], seed=3)
    big = bootstrap_ci([0.2, 0.9, 0.5, 0.7, 0.4] * 40, seed=3)
    assert small["lo"] <= small["mean"] <= small["hi"]
    assert (big["hi"] - big["lo"]) < (small["hi"] - small["lo"])
    assert bootstrap_ci([0.5] * 10)["lo"] == bootstrap_ci([0.5] * 10)["hi"] == 0.5
    assert bootstrap_ci([None, float("nan")])["n"] == 0


def test_paired_tests_detect_a_real_difference_and_not_a_null_one():
    base = [0.4 + 0.01 * (i % 7) for i in range(60)]
    better = [b + 0.15 + 0.01 * (i % 3) for i, b in enumerate(base)]
    res = paired_bootstrap(better, base, seed=1)
    assert res["lo"] > 0 and res["p"] < 0.01 and res["n"] == 60
    assert wilcoxon_p(better, base) < 0.001
    same = paired_bootstrap(base, base)
    assert same["diff"] == 0 and same["p"] == 1.0 and wilcoxon_p(base, base) == 1.0


def test_paired_arrays_align_on_common_questions_and_drop_missing():
    a = {"q1": 0.1, "q2": 0.2, "q3": None, "q4": float("nan")}
    b = {"q2": 0.5, "q1": 0.3, "q3": 0.9, "q5": 1.0}
    xa, xb = paired_arrays(a, b)
    assert list(xa) == [0.1, 0.2] and list(xb) == [0.3, 0.5]


def test_holm_adjustment():
    adj = holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adj == pytest.approx({"a": 0.03, "c": 0.06, "b": 0.06})


def test_cohen_kappa_textbook_example_and_edges():
    a = [1] * 25 + [0] * 25  # rater A: 25 yes
    b = [1] * 20 + [0] * 5 + [1] * 10 + [0] * 15  # both yes 20, A yes/B no 5, A no/B yes 10, both no 15
    assert cohen_kappa(a, b) == pytest.approx(0.4)
    assert cohen_kappa([1, 0, 1, 0], [1, 0, 1, 0]) == 1.0
    assert cohen_kappa([1, 1], [1, 1]) == 1.0
    assert cohen_kappa([1, 0, 1, 0], [0, 1, 0, 1]) == -1.0
    with pytest.raises(ValueError):
        cohen_kappa([1], [1, 0])


def test_ndcg_at_k():
    rel = {"a": 1, "c": 2}
    assert ndcg_at_k(["a", "b", "c"], rel, 10) == pytest.approx((1 + 2 / math.log2(4)) / (2 + 1 / math.log2(3)))
    assert ndcg_at_k(["c", "a"], rel, 10) == pytest.approx(1.0)
    assert ndcg_at_k(["x", "y"], rel, 10) == 0.0
    assert ndcg_at_k(["a"], {}, 10) == 0.0
    assert ndcg_at_k(["x", "a"], rel, 1) == 0.0  # cut-off respected
