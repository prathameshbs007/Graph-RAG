"""Learning phase (Module 5, step 2) and Graph Noise Reduction (Section 4.2).

1. Reset the memory to its freshly-ingested state and save it as the *initial* snapshot.
2. Run the feedback split through the full system for ``rounds`` rounds with learning on.
   Only the feedback split is used, so the memory never sees development or test questions.
3. After every round (and before round 1) measure **Graph Noise Reduction**: of the
   candidates the graph walk adds, the share the judge marks irrelevant. The measurement
   runs the walk on frozen weights with the same exploration seed each time, so changes
   come from the learned weights only.
4. Freeze: save the *learned* snapshot. Test-time runs load it and never update it.
"""

import asyncio
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Optional

from eval import judge
from eval.runner import learned_name, snapshot_path
from services.neo4j_client import graph_db
from services.pipeline import get_system, pipeline


def _key(qid: str, chunk_id: str) -> str:
    return hashlib.sha1(f"{qid}|{chunk_id}".encode()).hexdigest()


class JudgeCache:
    """Judge verdicts are paid for once and reused when a candidate re-appears in a later round."""

    def __init__(self, path: Path):
        self.path = path
        self.data: dict[str, bool] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def save(self):
        self.path.write_text(json.dumps(self.data), encoding="utf-8")


async def _judge_all(llm, items: list[tuple[dict, str, str]], cache: JudgeCache, concurrency: int = 4):
    sem = asyncio.Semaphore(concurrency)

    async def one(q, cid, text):
        k = _key(q["id"], cid)
        if k in cache.data:
            return
        async with sem:
            cache.data[k] = await judge.judge_relevance(llm, q["question"], q["reference"], text)

    await asyncio.gather(*(one(q, cid, text) for q, cid, text in items))


def graph_noise(questions: list[dict], llm, cache: JudgeCache, label, per_question: int, system_name: str = "full") -> dict:
    """Share of graph-added candidates the judge calls irrelevant, on the current (frozen) weights."""
    walk_only = replace(get_system(system_name), use_reranker=False, feedback=False)  # traversal, no learning
    items: list[tuple[dict, str, str]] = []
    for q in questions:
        res = pipeline.retrieve(q["question"], walk_only, learn=False, seed=0)
        reached = [c for c in res.candidates if not c.is_seed]
        reached.sort(key=lambda c: -max((min(e.weight for e in p) for p in c.paths), default=0.0))
        items += [(q, c.id, c.text) for c in reached[:per_question]]
    asyncio.run(_judge_all(llm, items, cache))
    cache.save()
    irrelevant = sum(1 for q, cid, _ in items if not cache.data[_key(q["id"], cid)])
    return {
        "round": label,
        "traversed": len(items),
        "irrelevant": irrelevant,
        "noise": (irrelevant / len(items)) if items else None,
        "edges": graph_db.edge_stats(),
        "alpha": graph_db.get_alpha(),
    }


def run_feedback(
    run_dir: Path,
    feedback_questions: list[dict],
    judge_cfg,
    rounds: int = 3,
    noise_questions: int = 40,
    noise_per_question: int = 10,
    reset: bool = True,
    system_name: str = "full",
) -> list[dict]:
    llm = judge.build_ragas_llm(judge_cfg)
    cache = JudgeCache(run_dir / "judge_cache.json")
    sample = feedback_questions[:noise_questions]
    (run_dir / "snapshots").mkdir(parents=True, exist_ok=True)

    if reset:
        graph_db.reset_feedback(clear_log=True)
    if system_name == "full" or not snapshot_path(run_dir, "initial").exists():
        snapshot_path(run_dir, "initial").write_text(json.dumps(graph_db.export_state()), encoding="utf-8")

    results = [graph_noise(sample, llm, cache, 0, noise_per_question, system_name)]
    print(f"[learn] round 0 (initial): noise={results[0]['noise']}")
    system = get_system(system_name)
    for r in range(1, rounds + 1):
        for i, q in enumerate(feedback_questions):
            pipeline.retrieve(q["question"], system, learn=True, seed=r * 100_000 + i)
        results.append(graph_noise(sample, llm, cache, r, noise_per_question, system_name))
        print(f"[learn] round {r}: noise={results[-1]['noise']} edges={ {k: v['pruned'] for k, v in results[-1]['edges'].items()} }")

    snapshot_path(run_dir, learned_name(system_name)).write_text(json.dumps(graph_db.export_state()), encoding="utf-8")
    suffix = "" if system_name == "full" else f"__{system_name}"
    (run_dir / f"feedback_rounds{suffix}.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


def noise_reduction(results: list[dict]) -> Optional[float]:
    """Relative drop in the irrelevant share from round 0 to the last round."""
    first, last = results[0]["noise"], results[-1]["noise"]
    if first in (None, 0) or last is None:
        return None
    return (first - last) / first
