"""Scoring with Ragas (Module 5, step 4).

Six metrics, all from Ragas (version pinned in requirements-eval.txt), computed from the
question, the retrieved contexts, the generated answer and the reference answer:

    faithfulness            share of answer claims supported by the contexts
                            (Hallucination Rate = 1 - faithfulness)
    answer_relevancy        does the answer address the question
    context_precision       are the retrieved contexts relevant (rank aware)
    context_recall          do the contexts cover the reference answer
    context_entity_recall   do the contexts contain the reference's key entities
    noise_sensitivity       errors in the answer caused by imperfect context (lower is better)

Refusals. When a system answers "insufficient evidence", no claim is made, so faithfulness
is 1.0 and noise sensitivity 0.0, but the question is not answered, so answer relevancy is
0.0. The three context metrics are scored normally (an empty context scores 0).
"""

import asyncio
import json
import math
from pathlib import Path
from typing import Optional

from eval.testset import read_jsonl

METRICS = [
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
    "context_entity_recall",
    "noise_sensitivity",
]
LOWER_IS_BETTER = {"noise_sensitivity"}


def build_metrics(llm, embeddings) -> dict:
    from ragas.metrics.collections import (
        AnswerRelevancy,
        ContextEntityRecall,
        ContextPrecision,
        ContextRecall,
        Faithfulness,
        NoiseSensitivity,
    )

    return {
        "faithfulness": Faithfulness(llm=llm),
        "answer_relevancy": AnswerRelevancy(llm=llm, embeddings=embeddings),
        "context_precision": ContextPrecision(llm=llm),
        "context_recall": ContextRecall(llm=llm),
        "context_entity_recall": ContextEntityRecall(llm=llm),
        "noise_sensitivity": NoiseSensitivity(llm=llm),
    }


def metric_kwargs(name: str, question: dict, row: dict) -> dict:
    """Arguments for ``metric.ascore`` (names follow the Ragas collections API)."""
    q, ref, ctx, ans = question["question"], question["reference"], row["contexts"], row["answer"]
    return {
        "faithfulness": {"user_input": q, "response": ans, "retrieved_contexts": ctx},
        "answer_relevancy": {"user_input": q, "response": ans},
        "context_precision": {"user_input": q, "reference": ref, "retrieved_contexts": ctx},
        "context_recall": {"user_input": q, "reference": ref, "retrieved_contexts": ctx},
        "context_entity_recall": {"reference": ref, "retrieved_contexts": ctx},
        "noise_sensitivity": {"user_input": q, "response": ans, "reference": ref, "retrieved_contexts": ctx},
    }[name]


def fixed_score(name: str, row: dict) -> Optional[float]:
    """Scores that need no judge call (refusals and empty contexts); ``None`` = ask the judge."""
    if row.get("refused"):
        if name == "faithfulness":
            return 1.0
        if name in ("answer_relevancy", "noise_sensitivity"):
            return 0.0
    if not row["contexts"] and name in ("context_precision", "context_recall", "context_entity_recall"):
        return 0.0
    return None


async def _call(metric, kwargs: dict, sem: asyncio.Semaphore, retries: int = 3) -> Optional[float]:
    async with sem:
        for attempt in range(retries):
            try:
                value = (await metric.ascore(**kwargs)).value
                return None if value is None or (isinstance(value, float) and math.isnan(value)) else float(value)
            except Exception as exc:  # noqa: BLE001 - rate limits, malformed judge output
                if attempt == retries - 1:
                    print(f"[score] {getattr(metric, 'name', metric)} failed: {str(exc)[:120]}")
                    return None
                await asyncio.sleep(2**attempt)


async def _score_rows(rows: list[dict], questions: dict[str, dict], metrics: dict, concurrency: int, out) -> None:
    sem = asyncio.Semaphore(concurrency)

    async def one(row):
        q = questions[row["id"]]
        names = list(metrics)
        vals = await asyncio.gather(
            *(
                _const(fixed_score(n, row)) if fixed_score(n, row) is not None else _call(metrics[n], metric_kwargs(n, q, row), sem)
                for n in names
            )
        )
        rec = {"id": row["id"], "system": row["system"], "seed": row["seed"], **dict(zip(names, vals))}
        out.write(json.dumps(rec) + "\n")
        out.flush()

    await asyncio.gather(*(one(r) for r in rows))


async def _const(v):
    return v


def score_run(run_dir: Path, questions: list[dict], metrics: dict, systems=None, seeds=None, concurrency: int = 4) -> None:
    qmap = {q["id"]: q for q in questions}
    (run_dir / "scores").mkdir(exist_ok=True)
    for path in sorted((run_dir / "results").glob("*.jsonl")):
        stem = path.stem
        system, seed = stem.split("__seed")
        if (systems and system not in systems) or (seeds and int(seed) not in seeds):
            continue
        out_path = run_dir / "scores" / path.name
        done = {r["id"] for r in read_jsonl(out_path)}
        todo = [r for r in read_jsonl(path) if r["id"] not in done and r["id"] in qmap]
        print(f"[score] {stem}: {len(todo)} rows")
        if not todo:
            continue
        with open(out_path, "a", encoding="utf-8") as out:
            asyncio.run(_score_rows(todo, qmap, metrics, concurrency, out))
