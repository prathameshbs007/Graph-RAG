"""The evaluation harness end to end on the live databases. Only the judge (Ragas metrics and
the relevance judge) is replaced by a deterministic stand-in, so everything that is *not* an
LLM call is the real code: splits, snapshots, frozen-memory runs, resume, scoring plumbing,
statistics and the report."""

import csv
import json
from types import SimpleNamespace

import pytest

from fakes import tokens
from test_e2e_integration import kb  # noqa: F401  (module-scoped fixture: ingested corpus)

pytestmark = pytest.mark.integration

QUESTIONS = [
    ("How are dense embeddings trained with contrastive learning?", "Dense embeddings are trained with contrastive learning on question passage pairs."),
    ("What does the reranker do in the retrieval pipeline?", "The reranker scores every candidate and the retrieval pipeline keeps the best passages."),
    ("How does approximate neighbor search help retrieval?", "Approximate neighbor search over the embeddings returns the closest passages quickly."),
    ("Why combine bm25 keyword matching with dense embeddings?", "Hybrid retrieval combines bm25 keyword matching with dense embeddings so exact terms and paraphrases are found."),
    ("How should cast iron skillets be seasoned?", "Cast iron skillets need seasoning with a thin layer of oil."),
    ("What keeps the seasoning intact on skillets?", "Heat the skillets slowly and avoid soaking so the seasoning stays intact."),
    ("Which passages does the retrieval pipeline keep?", "The retrieval pipeline keeps the best passages."),
    ("What are neural passage retrieval models trained on?", "Question passage pairs with contrastive learning."),
    ("Explain quantum chromodynamics lattice gauge theory", "Not covered by the corpus."),  # -> refusal
    ("Describe the migration of arctic terns", "Not covered by the corpus."),  # -> refusal
]


def _overlap(a: str, b: str) -> float:
    ta, tb = set(tokens(a)), set(tokens(b))
    return len(ta & tb) / len(ta) if ta else 0.0


def _fake_metrics(calls):
    def metric(name, fn):
        async def ascore(**kw):
            calls.append(name)
            return SimpleNamespace(value=fn(**kw))

        return SimpleNamespace(name=name, ascore=ascore)

    ctx = lambda kw: " ".join(kw["retrieved_contexts"])  # noqa: E731
    return {
        "faithfulness": metric("faithfulness", lambda **kw: _overlap(kw["response"], ctx(kw))),
        "answer_relevancy": metric("answer_relevancy", lambda **kw: _overlap(kw["user_input"], kw["response"])),
        "context_precision": metric("context_precision", lambda **kw: _overlap(kw["user_input"], ctx(kw))),
        "context_recall": metric("context_recall", lambda **kw: _overlap(kw["reference"], ctx(kw))),
        "context_entity_recall": metric("context_entity_recall", lambda **kw: _overlap(kw["reference"], ctx(kw))),
        "noise_sensitivity": metric("noise_sensitivity", lambda **kw: 1 - _overlap(kw["response"], ctx(kw))),
    }


def test_split_and_review_sheet(tmp_path):
    from eval import testset

    rows = [{"id": f"q{i:03d}", "question": f"question {i}?", "reference": "ref", "reference_contexts": [],
             "query_type": "multi_hop" if i % 3 == 0 else "single_hop"} for i in range(50)]
    testset.write_jsonl(tmp_path / "testset.jsonl", rows)
    sizes = testset.split_and_export(tmp_path)
    assert sizes == {"feedback": 20, "development": 10, "test": 20}
    with open(tmp_path / "review_sample.csv", newline="", encoding="utf-8") as f:
        sheet = list(csv.DictReader(f))
    assert len(sheet) == 10 and {"clear", "answerable", "reference_correct", "keep"} <= set(sheet[0])

    # a reviewer rejects a question: it is dropped on the next split, and ratings are never overwritten
    sheet[0]["keep"] = "0"
    with open(tmp_path / "review_sample.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(sheet[0]))
        w.writeheader()
        w.writerows(sheet)
    sizes2 = testset.split_and_export(tmp_path)
    assert sum(sizes2.values()) == 49
    assert testset.rejected_ids(tmp_path) == {sheet[0]["id"]}


def test_harness_end_to_end(kb, tmp_path, monkeypatch):  # noqa: F811
    from config import settings
    from eval import feedback_phase, judge, report, runner, scoring, testset

    graph = kb["graph"]
    run = tmp_path / "run"
    run.mkdir()
    rows = [{"id": f"q{i:03d}", "question": q, "reference": r, "reference_contexts": [],
             "query_type": "single_hop" if i % 3 else "multi_hop"} for i, (q, r) in enumerate(QUESTIONS)]
    testset.write_jsonl(run / "testset.jsonl", rows)
    ids = [r["id"] for r in rows]
    (run / "splits.json").write_text(json.dumps({"feedback": ids[:5], "development": ids[5:6], "test": ids[6:]}))

    # ---- learning phase (the relevance judge is a lexical stand-in)
    async def fake_relevance(llm, question, reference, passage):
        return _overlap(question + " " + reference, passage) >= 0.2

    monkeypatch.setattr(judge, "build_ragas_llm", lambda cfg: object())
    monkeypatch.setattr(judge, "judge_relevance", fake_relevance)
    rounds = feedback_phase.run_feedback(run, testset.load_split(run, "feedback"), None, rounds=2,
                                         noise_questions=5, noise_per_question=6)
    assert [r["round"] for r in rounds] == [0, 1, 2]
    assert all(r["noise"] is None or 0 <= r["noise"] <= 1 for r in rounds)
    initial = json.loads((run / "snapshots" / "initial.json").read_text())
    learned = json.loads((run / "snapshots" / "learned.json").read_text())
    assert {e["weight"] for e in initial["edges"]} == {0.5} and initial["alpha"] == 0.5
    assert any(e["weight"] != 0.5 for e in learned["edges"]), "feedback rounds should have changed some weights"
    assert (run / "feedback_rounds.json").exists()
    key = lambda e: (e["type"], e["src"], e["dst"])  # noqa: E731

    # ---- running systems: each starts from the memory it is defined to have, and never changes it
    systems, seeds = ["full", "b1_bm25", "b4_static_graph", "abl_no_graph"], [0, 1]
    runner.run_systems(run, systems, seeds, split="test")
    test_ids = ids[6:]
    for s in systems:
        for seed in seeds:
            got = testset.read_jsonl(runner.result_path(run, s, seed))
            assert [r["id"] for r in got] == test_ids
    after = graph.export_state()  # last system run was abl_no_graph (learned state)
    assert sorted(after["edges"], key=key) == sorted(learned["edges"], key=key), "test-time runs must not update memory"
    from services.pipeline import get_system

    runner.ensure_state(run, get_system("b4_static_graph"))
    assert {e["weight"] for e in graph.export_state()["edges"]} == {0.5}
    full_rows = testset.read_jsonl(runner.result_path(run, "full", 0))
    assert full_rows[0]["alpha"] == pytest.approx(learned["alpha"])
    assert [r["refused"] for r in full_rows][-2:] == [True, True]  # the two off-topic questions
    assert not any(r["refused"] for r in full_rows[:-2])

    before = {p.name: len(p.read_text().splitlines()) for p in (run / "results").glob("*.jsonl")}
    runner.run_systems(run, systems, seeds, split="test")  # resumable: nothing is recomputed
    assert before == {p.name: len(p.read_text().splitlines()) for p in (run / "results").glob("*.jsonl")}

    # ---- scoring: refusals need no judge call, and are scored by the documented convention
    calls = []
    scoring.score_run(run, testset.load_split(run, "test"), _fake_metrics(calls), concurrency=2)
    scores = {(r["system"], r["seed"], r["id"]): r for p in (run / "scores").glob("*.jsonl") for r in testset.read_jsonl(p)}
    assert len(scores) == len(systems) * len(seeds) * len(test_ids)
    refused = scores[("full", 0, test_ids[-1])]
    assert (refused["faithfulness"], refused["answer_relevancy"], refused["noise_sensitivity"]) == (1.0, 0.0, 0.0)
    assert len(calls) < len(scores) * 6  # judge not called where the score is fixed
    assert all(0 <= v <= 1 for r in scores.values() for k, v in r.items() if k in scoring.METRICS and v is not None)

    # ---- report
    md = report.build_report(run, n_boot=300)
    for needle in ("ResearchOS (Full)", "B1 BM25 only", "B4 Static Graph RAG", "Full - graph", "hallucination_rate",
                   "Graph Noise Reduction", "Seed variability", "p (bootstrap, Holm)"):
        assert needle in md, needle
    assert (run / "report" / "report.md").exists() and (run / "report" / "results.csv").exists()

    # ---- judge-human agreement
    path = report.write_human_rating_template(run, n=4)
    with open(path, newline="", encoding="utf-8") as f:
        rows_h = list(csv.DictReader(f))
    for i, r in enumerate(rows_h):
        r["human_faithful"] = "1" if i % 2 == 0 else "0"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_h[0]))
        w.writeheader()
        w.writerows(rows_h)
    assert "Cohen's κ" in report.build_report(run, n_boot=100)
    assert settings.FEEDBACK_ENABLED
