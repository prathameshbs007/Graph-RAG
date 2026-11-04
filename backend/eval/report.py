"""Result tables and plots (Module 5, step 5).

Reads ``scores/*.jsonl`` and writes ``report/report.md``, ``report/results.csv`` and plots:
means with 95% bootstrap CIs, Full vs every baseline with paired tests, ablation deltas,
seed variability, Graph Noise Reduction per round, review pass rate, judge-human kappa.
"""

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Optional

import numpy as np

from eval.scoring import LOWER_IS_BETTER, METRICS
from eval.stats import bootstrap_ci, cohen_kappa, holm, paired_arrays, paired_bootstrap, wilcoxon_p
from eval.testset import read_jsonl

BASELINES = ["b1_bm25", "b2_dense", "b3_static_hybrid", "b4_static_graph", "b5_flat_rerank"]
ABLATIONS = ["abl_no_bm25", "abl_no_dense", "abl_no_graph", "abl_no_feedback"]
LABELS = {
    "full": "ResearchOS (Full)",
    "b1_bm25": "B1 BM25 only",
    "b2_dense": "B2 Dense only",
    "b3_static_hybrid": "B3 Static hybrid",
    "b4_static_graph": "B4 Static Graph RAG",
    "b5_flat_rerank": "B5 Flat + reranker",
    "abl_no_bm25": "Full - BM25",
    "abl_no_dense": "Full - dense",
    "abl_no_graph": "Full - graph",
    "abl_no_feedback": "Full - feedback",
}
JUDGE_FAITHFUL_THRESHOLD = 0.5


def load_scores(run_dir: Path) -> dict[str, dict[int, dict[str, dict]]]:
    """``{system: {seed: {question_id: row}}}``"""
    out: dict = defaultdict(lambda: defaultdict(dict))
    for path in sorted((run_dir / "scores").glob("*.jsonl")):
        for r in read_jsonl(path):
            out[r["system"]][r["seed"]][r["id"]] = r
    return out


def per_question(scores, system: str, metric: str) -> dict[str, float]:
    """Mean over seeds of one metric, per question."""
    acc: dict[str, list[float]] = defaultdict(list)
    for seed_rows in scores.get(system, {}).values():
        for qid, r in seed_rows.items():
            v = r.get(metric)
            if v is not None:
                acc[qid].append(v)
    return {q: float(np.mean(v)) for q, v in acc.items()}


def seed_means(scores, system: str, metric: str) -> list[float]:
    out = []
    for seed_rows in scores.get(system, {}).values():
        vals = [r[metric] for r in seed_rows.values() if r.get(metric) is not None]
        if vals:
            out.append(float(np.mean(vals)))
    return out


def _fmt(ci: dict, digits: int = 3) -> str:
    if ci["n"] == 0:
        return "—"
    return f"{ci['mean']:.{digits}f} [{ci['lo']:.{digits}f}, {ci['hi']:.{digits}f}]"


def build_report(run_dir: Path, n_boot: int = 10000) -> str:
    scores = load_scores(run_dir)
    if not scores:
        raise RuntimeError("no scores found; run 'score' first")
    systems = [s for s in ["full", *BASELINES, *ABLATIONS] if s in scores]
    lines: list[str] = []
    csv_rows: list[dict] = []

    manifest_path = run_dir / "manifest.json"
    if manifest_path.exists():
        m = json.loads(manifest_path.read_text(encoding="utf-8"))
        lines += [
            "# ResearchOS evaluation report",
            "",
            f"- Ragas: `{m.get('ragas')}` · judge: `{(m.get('judge') or {}).get('model')}` "
            f"({(m.get('judge') or {}).get('date') or 'date not recorded'}) · generator: `{m.get('generator')}`",
            f"- embeddings: `{m.get('embedding_model')}` · reranker: `{m.get('reranker')}` · commit: `{(m.get('git_commit') or '')[:10]}`",
            "",
        ]
    else:
        lines += ["# ResearchOS evaluation report", ""]
    n_q = {s: len(per_question(scores, s, "faithfulness")) for s in systems}
    seeds = {s: len(scores[s]) for s in systems}
    lines += [f"Questions scored per system: {n_q}  ·  seeds per system: {seeds}", ""]

    # ---- 1. headline table
    lines += ["## 1. Ragas scores (mean over seeds; 95% bootstrap CI over questions)", ""]
    cols = ["hallucination_rate"] + [m for m in METRICS if m != "faithfulness"] + ["faithfulness"]
    header = "| System | " + " | ".join(c + (" ↓" if c in LOWER_IS_BETTER or c == "hallucination_rate" else " ↑") for c in cols) + " |"
    lines += [header, "|" + "---|" * (len(cols) + 1)]
    for s in systems:
        cells = []
        for c in cols:
            vals = per_question(scores, s, "faithfulness" if c == "hallucination_rate" else c)
            arr = [1 - v for v in vals.values()] if c == "hallucination_rate" else list(vals.values())
            ci = bootstrap_ci(arr, n_boot=n_boot)
            cells.append(_fmt(ci))
            csv_rows.append({"system": s, "metric": c, **ci})
        lines.append(f"| {LABELS.get(s, s)} | " + " | ".join(cells) + " |")
    lines.append("")

    # ---- 2. Full vs baselines
    if "full" in scores:
        lines += [
            "## 2. ResearchOS vs baselines (paired over questions)",
            "",
            "Δ = Full − baseline (for hallucination rate and noise sensitivity a *negative* Δ is better). "
            "p-values: paired bootstrap and Wilcoxon signed-rank, each Holm-corrected across the baselines.",
            "",
            "| Baseline | Metric | Δ [95% CI] | relative gain | p (bootstrap, Holm) | p (Wilcoxon, Holm) |",
            "|---|---|---|---|---|---|",
        ]
        for metric in [m for m in METRICS]:
            boot_p, wil_p, rows = {}, {}, {}
            for b in [b for b in BASELINES if b in scores]:
                a_, b_ = paired_arrays(per_question(scores, "full", metric), per_question(scores, b, metric))
                if a_.size == 0:
                    continue
                res = paired_bootstrap(a_, b_, n_boot=n_boot)
                rows[b] = (res, a_, b_)
                boot_p[b], wil_p[b] = res["p"], wilcoxon_p(a_, b_)
            hb, hw = holm(boot_p), holm(wil_p)
            for b, (res, a_, b_) in rows.items():
                rel = f"{100 * res['diff'] / b_.mean():+.1f}%" if b_.mean() else "n/a"
                lines.append(
                    f"| {LABELS[b]} | {metric} | {res['diff']:+.3f} [{res['lo']:+.3f}, {res['hi']:+.3f}] | {rel} "
                    f"| {hb[b]:.4f} | {hw[b]:.4f} |"
                )
                csv_rows.append({"system": f"full_vs_{b}", "metric": metric, "mean": res["diff"], "lo": res["lo"], "hi": res["hi"], "n": res["n"], "p_boot_holm": hb[b], "p_wilcoxon_holm": hw[b]})
        lines.append("")

        # ---- 3. ablations
        abl = [a for a in ABLATIONS if a in scores]
        if abl:
            lines += ["## 3. Ablation deltas (Full − ablation; positive = the component helps, except ↓ metrics)", "",
                      "| Removed component | " + " | ".join(METRICS) + " |", "|" + "---|" * (len(METRICS) + 1)]
            for a in abl:
                cells = []
                for metric in METRICS:
                    x, y = paired_arrays(per_question(scores, "full", metric), per_question(scores, a, metric))
                    if x.size == 0:
                        cells.append("—")
                        continue
                    res = paired_bootstrap(x, y, n_boot=n_boot)
                    cells.append(f"{res['diff']:+.3f} [{res['lo']:+.3f}, {res['hi']:+.3f}]")
                    csv_rows.append({"system": f"full_minus_{a}", "metric": metric, "mean": res["diff"], "lo": res["lo"], "hi": res["hi"], "n": res["n"]})
                lines.append(f"| {LABELS[a]} | " + " | ".join(cells) + " |")
            lines.append("")

    # ---- 4. seed variability
    lines += ["## 4. Seed variability (std of the system mean across seeds)", "", "| System | " + " | ".join(METRICS) + " |", "|" + "---|" * (len(METRICS) + 1)]
    for s in systems:
        cells = []
        for metric in METRICS:
            sm = seed_means(scores, s, metric)
            cells.append(f"{np.std(sm, ddof=1):.4f}" if len(sm) > 1 else "—")
        lines.append(f"| {LABELS.get(s, s)} | " + " | ".join(cells) + " |")
    lines.append("")

    # ---- 5. graph noise reduction
    fb = run_dir / "feedback_rounds.json"
    if fb.exists():
        rounds = json.loads(fb.read_text(encoding="utf-8"))
        lines += ["## 5. Graph Noise Reduction (share of graph-added candidates the judge marks irrelevant)", "",
                  "| Round | Traversed candidates | Irrelevant | Noise | α | Pruned edges |", "|---|---|---|---|---|---|"]
        for r in rounds:
            pruned = sum(e["pruned"] for e in r["edges"].values())
            noise = "—" if r["noise"] is None else f"{r['noise']:.3f}"
            lines.append(f"| {r['round']} | {r['traversed']} | {r['irrelevant']} | {noise} | {r['alpha']:.3f} | {pruned} |")
        first, last = rounds[0]["noise"], rounds[-1]["noise"]
        if first and last is not None:
            lines.append(f"\nNoise fell from {first:.3f} to {last:.3f} ({100 * (first - last) / first:+.1f}% relative reduction).")
        lines.append("")

    # ---- 6. human review + judge agreement
    review = _review_pass_rate(run_dir)
    kappa = _judge_human_kappa(run_dir, scores)
    if review or kappa:
        lines += ["## 6. Quality controls", ""]
        if review:
            lines.append(f"- Test-set review: {review['kept']} of {review['rated']} reviewed questions kept "
                         f"(pass rate {review['rate']:.0%}).")
        if kappa:
            lines.append(f"- Judge–human agreement on {kappa['n']} answers: Cohen's κ = {kappa['kappa']:.3f} "
                         f"(judge 'faithful' = faithfulness ≥ {JUDGE_FAITHFUL_THRESHOLD}).")
        lines.append("")

    out = run_dir / "report"
    out.mkdir(exist_ok=True)
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    with open(out / "results.csv", "w", newline="", encoding="utf-8") as f:
        fields = ["system", "metric", "mean", "lo", "hi", "n", "p_boot_holm", "p_wilcoxon_holm"]
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(csv_rows)
    _plots(out, scores, systems, run_dir, n_boot)
    return "\n".join(lines)


def _review_pass_rate(run_dir: Path) -> Optional[dict]:
    sheet = run_dir / "review_sample.csv"
    if not sheet.exists():
        return None
    with open(sheet, newline="", encoding="utf-8") as f:
        rated = [r for r in csv.DictReader(f) if str(r.get("keep", "")).strip()]
    if not rated:
        return None
    kept = sum(str(r["keep"]).strip().lower() in ("1", "yes", "y", "true") for r in rated)
    return {"kept": kept, "rated": len(rated), "rate": kept / len(rated)}


def _judge_human_kappa(run_dir: Path, scores) -> Optional[dict]:
    """``human_ratings.csv``: columns id, system, seed, human_faithful (1 = every claim supported)."""
    path = run_dir / "human_ratings.csv"
    if not path.exists():
        return None
    human, judge = [], []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if str(r.get("human_faithful", "")).strip() == "":
                continue
            row = scores.get(r["system"], {}).get(int(r.get("seed") or 0), {}).get(r["id"])
            if row is None or row.get("faithfulness") is None:
                continue
            human.append(int(float(r["human_faithful"])))
            judge.append(int(row["faithfulness"] >= JUDGE_FAITHFUL_THRESHOLD))
    if len(human) < 2:
        return None
    return {"n": len(human), "kappa": cohen_kappa(human, judge)}


def write_human_rating_template(run_dir: Path, n: int = 30, seed: int = 13, system: str = "full") -> Path:
    """Pick ``n`` Full-system answers for the team to rate against the judge."""
    import random

    rows = read_jsonl(run_dir / "results" / f"{system}__seed0.jsonl")
    questions = {q["id"]: q for q in read_jsonl(run_dir / "testset.jsonl")}
    pick = random.Random(seed).sample(rows, min(n, len(rows)))
    path = run_dir / "human_ratings.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "system", "seed", "question", "answer", "contexts", "human_faithful"])
        for r in sorted(pick, key=lambda r: r["id"]):
            w.writerow([r["id"], r["system"], r["seed"], questions[r["id"]]["question"], r["answer"],
                        " || ".join(r["contexts"]), ""])
    return path


def _plots(out: Path, scores, systems, run_dir: Path, n_boot: int) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:  # noqa: BLE001
        return
    metrics = ["faithfulness", "answer_relevancy", "context_precision", "context_recall", "context_entity_recall", "noise_sensitivity"]
    fig, axes = plt.subplots(2, 3, figsize=(15, 7))
    for ax, metric in zip(axes.flat, metrics):
        means, errs = [], []
        for s in systems:
            ci = bootstrap_ci(list(per_question(scores, s, metric).values()), n_boot=n_boot)
            means.append(ci["mean"])
            errs.append([ci["mean"] - ci["lo"], ci["hi"] - ci["mean"]])
        ax.bar(range(len(systems)), means, yerr=np.array(errs).T, color=["#4f46e5" if s == "full" else "#9ca3af" for s in systems], capsize=3)
        ax.set_xticks(range(len(systems)))
        ax.set_xticklabels([LABELS.get(s, s) for s in systems], rotation=60, ha="right", fontsize=7)
        ax.set_title(metric + (" (lower is better)" if metric in LOWER_IS_BETTER else ""), fontsize=10)
        ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(out / "metrics.png", dpi=150)
    plt.close(fig)

    fb = run_dir / "feedback_rounds.json"
    if fb.exists():
        rounds = json.loads(fb.read_text(encoding="utf-8"))
        xs = [r["round"] for r in rounds if r["noise"] is not None]
        ys = [r["noise"] for r in rounds if r["noise"] is not None]
        if xs:
            fig, ax = plt.subplots(figsize=(5, 3.5))
            ax.plot(xs, ys, marker="o", color="#4f46e5")
            ax.set_xlabel("feedback round")
            ax.set_ylabel("irrelevant share of graph-added candidates")
            ax.set_xticks(xs)
            ax.set_ylim(0, 1)
            fig.tight_layout()
            fig.savefig(out / "noise_reduction.png", dpi=150)
            plt.close(fig)
