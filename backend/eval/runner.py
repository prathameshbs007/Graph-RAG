"""Running the systems on a question split (Module 5, step 3).

Every system runs through the *same* service code as the live application
(``services.pipeline``), against the memory state it is defined to have:

* systems without feedback (B1-B5, "no feedback" ablation) use the **initial** graph,
  all edges at weight 0.5, alpha 0.5;
* systems with feedback use the **frozen learned** graph from ``eval learn`` and, at test
  time, never update it (``learn=False``), so nothing leaks from the test split.
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Optional

from config import settings
from eval.testset import load_split, read_jsonl
from services.generator import is_refusal
from services.neo4j_client import graph_db
from services.pipeline import get_system, pipeline


def snapshot_path(run_dir: Path, which: str) -> Path:
    return run_dir / "snapshots" / f"{which}.json"


def learned_name(system_name: str) -> str:
    return "learned" if system_name == "full" else f"learned__{system_name}"


def ensure_state(run_dir: Path, system) -> str:
    """Load the initial or the frozen-learned memory into Neo4j for ``system``.

    An ablation that keeps the feedback loop (e.g. "Full - BM25") must have learned its own
    memory without the removed component (``learn --system abl_no_bm25``); if that snapshot
    is missing the Full system's memory is used and a warning is printed.
    """
    if system.state == "initial":
        which = "initial"
    elif snapshot_path(run_dir, learned_name(system.name)).exists():
        which = learned_name(system.name)
    else:
        which = "learned"
        if system.name != "full":
            print(f"[run] WARNING: no memory learned for '{system.name}', using Full's learned memory")
    path = snapshot_path(run_dir, which)
    if not path.exists():
        raise RuntimeError(f"missing {path}; run 'learn' first")
    graph_db.import_state(json.loads(path.read_text(encoding="utf-8")))
    return which


def result_path(run_dir: Path, system: str, seed: int) -> Path:
    return run_dir / "results" / f"{system}__seed{seed}.jsonl"


def run_systems(
    run_dir: Path,
    systems: list[str],
    seeds: list[int],
    split: str = "test",
    verify: Optional[bool] = None,
    limit: Optional[int] = None,
) -> None:
    questions = load_split(run_dir, split)[:limit]
    if not questions:
        raise RuntimeError(f"no questions in split '{split}'")
    for name in systems:
        cfg = get_system(name)
        state = ensure_state(run_dir, cfg)
        for seed in seeds:
            path = result_path(run_dir, name, seed)
            path.parent.mkdir(parents=True, exist_ok=True)
            done = {r["id"] for r in read_jsonl(path)}  # resume an interrupted run
            todo = [q for q in questions if q["id"] not in done]
            print(f"[run] {name} seed={seed} state={state}: {len(todo)} of {len(questions)} questions")
            with open(path, "a", encoding="utf-8") as f:
                for q in todo:
                    out = pipeline.answer(q["question"], system=name, learn=False, seed=seed, verify=verify)
                    d = out["diagnostics"]
                    row = {
                        "id": q["id"],
                        "system": name,
                        "seed": seed,
                        "answer": out["answer"],
                        "refused": is_refusal(out["answer"]) or not out["_context_texts"],
                        "contexts": out["_context_texts"],
                        "claim_stats": out["claim_stats"],
                        "alpha": d["alpha"],
                        "graph_reached": d["graph_reached"],
                        "ms": d["timings"].get("total_ms"),
                    }
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    f.flush()


def write_manifest(run_dir: Path, extra: dict) -> None:
    """Everything needed to reproduce the run: versions, parameters, judge model and date."""
    path = run_dir / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    try:
        import ragas

        ragas_version = ragas.__version__
    except Exception:  # noqa: BLE001
        ragas_version = None
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:  # noqa: BLE001
        commit = ""
    manifest.update(
        {
            "updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "git_commit": commit,
            "ragas": ragas_version,
            "generator": settings.OLLAMA_LLM_MODEL if settings.LLM_PROVIDER == "ollama" else settings.GROQ_MODEL,
            "embedding_model": settings.EMBED_MODEL,
            "reranker": settings.COHERE_RERANK_MODEL,
            "parameters": {
                k: getattr(settings, k)
                for k in (
                    "CHUNK_SIZE", "CHUNK_OVERLAP_RATIO", "RETRIEVAL_TOP_K", "SEED_K", "RRF_K", "FUSION",
                    "EDGE_INIT_WEIGHT", "EDGE_TRAVERSE_MIN", "EXPLORE_PROB", "EDGE_LR", "PRUNE_MIN_VISITS",
                    "PRUNE_BELOW", "RELEVANCE_CUTOFF", "CONTEXT_SIZE", "ALPHA_INIT", "ALPHA_RATE", "ALPHA_MIN",
                    "ALPHA_MAX", "VERIFY_CLAIMS", "VERIFY_MODE", "GENERATION_TEMPERATURE",
                )
            },
            **extra,
        }
    )
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
