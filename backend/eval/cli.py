"""Command line for the evaluation: ``python -m eval <command> --run NAME``.

Typical order (see eval/README.md):
    testset -> split -> (review) -> learn -> run -> score -> report
"""

import argparse
import json
import os
from pathlib import Path

from eval.testset import load_split

ALL_SYSTEMS = [
    "full", "b1_bm25", "b2_dense", "b3_static_hybrid", "b4_static_graph", "b5_flat_rerank",
    "abl_no_bm25", "abl_no_dense", "abl_no_graph", "abl_no_feedback",
]
LEARNING_ABLATIONS = ["abl_no_bm25", "abl_no_dense", "abl_no_graph"]  # these keep a feedback loop


def run_dir(name: str) -> Path:
    d = Path(os.environ.get("EVAL_DIR", "eval_runs")) / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def _ints(text: str) -> list[int]:
    return [int(x) for x in text.split(",") if x.strip() != ""]


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="eval", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", default="run1", help="name of the run directory under $EVAL_DIR (default eval_runs/)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("testset", help="generate the Ragas test set from the ingested corpus")
    p.add_argument("--size", type=int, default=200)
    p = sub.add_parser("split", help="split 40/20/40 by question type and export the 20%% review sheet")
    p.add_argument("--seed", type=int, default=13)
    p = sub.add_parser("learn", help="feedback rounds on the feedback split, then freeze the memory")
    p.add_argument("--system", default="full", help="full, or an ablation that keeps feedback: " + ", ".join(LEARNING_ABLATIONS))
    p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--noise-questions", type=int, default=40)
    p.add_argument("--noise-per-question", type=int, default=10)
    p = sub.add_parser("run", help="run systems on a split (frozen memory, 3 seeds)")
    p.add_argument("--systems", default="all", help="comma list or 'all'")
    p.add_argument("--seeds", default="0,1,2")
    p.add_argument("--split", default="test", choices=["test", "development", "feedback"])
    p.add_argument("--limit", type=int, default=None)
    p = sub.add_parser("score", help="score the results with Ragas")
    p.add_argument("--systems", default="all")
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--split", default="test")
    sub.add_parser("report", help="tables, significance tests and plots")
    p = sub.add_parser("ratings", help="write human_ratings.csv for the judge-human kappa")
    p.add_argument("--n", type=int, default=30)
    p = sub.add_parser("beir", help="BEIR SciFact nDCG@10 sanity check")
    p.add_argument("--keep", action="store_true", help="keep the temporary SciFact index")

    args = ap.parse_args(argv)
    d = run_dir(args.run)

    if args.cmd == "testset":
        from eval import judge, testset
        from eval.runner import write_manifest

        cfg = judge.JudgeConfig.from_env()
        testset.generate(d, args.size, cfg)
        write_manifest(d, {"judge": cfg.manifest(), "testset_size": args.size})
        print(testset.split_and_export(d))
    elif args.cmd == "split":
        from eval import testset

        print(testset.split_and_export(d, args.seed))
    elif args.cmd == "learn":
        from eval import feedback_phase, judge
        from eval.runner import write_manifest

        cfg = judge.JudgeConfig.from_env()
        questions = load_split(d, "feedback")
        res = feedback_phase.run_feedback(
            d, questions, cfg, rounds=args.rounds, noise_questions=args.noise_questions,
            noise_per_question=args.noise_per_question, system_name=args.system,
        )
        write_manifest(d, {"judge": cfg.manifest()})
        print(json.dumps({"noise_by_round": [r["noise"] for r in res], "relative_reduction": feedback_phase.noise_reduction(res)}))
    elif args.cmd == "run":
        from eval.runner import run_systems, write_manifest

        systems = ALL_SYSTEMS if args.systems == "all" else args.systems.split(",")
        run_systems(d, systems, _ints(args.seeds), split=args.split, limit=args.limit)
        write_manifest(d, {"seeds": _ints(args.seeds), "systems": systems})
    elif args.cmd == "score":
        from eval import judge, scoring
        from eval.runner import write_manifest

        cfg = judge.JudgeConfig.from_env()
        metrics = scoring.build_metrics(judge.build_ragas_llm(cfg), judge.build_ragas_embeddings())
        systems = None if args.systems == "all" else args.systems.split(",")
        scoring.score_run(d, load_split(d, args.split), metrics, systems=systems, concurrency=args.concurrency)
        write_manifest(d, {"judge": cfg.manifest()})
    elif args.cmd == "report":
        from eval import report

        print(report.build_report(d))
        print(f"\nwritten to {d / 'report'}")
    elif args.cmd == "ratings":
        from eval import report

        print(report.write_human_rating_template(d, args.n))
    elif args.cmd == "beir":
        from eval import beir_check

        print(json.dumps(beir_check.run(keep=args.keep), indent=2))


if __name__ == "__main__":
    main()
