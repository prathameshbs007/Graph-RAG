# Module 5: RAG evaluation with Ragas

Implements Sections 2.5, 4.1 and 4.2 of the Phase 3 report: a Ragas-generated test set, a
40 / 20 / 40 split, one feedback phase, five baselines and four ablations run on the held-out
split with three seeds, Ragas scoring, confidence intervals, paired significance tests,
ablation deltas, Graph Noise Reduction, review pass rate and judge-human agreement.

Every system runs through the **same service code as the live app** (`services/pipeline.py`);
baselines and ablations are switches on that pipeline (`GET /query/systems`), not separate code.

## What you need

* The paper corpus ingested (30-50 papers; the report plans open-access arXiv papers on
  retrieval, RAG and graph retrieval) plus 2-3 talks for the citation check.
* A **judge model** that is stronger than, and different from, the generator, set in `.env`:
  `JUDGE_PROVIDER` (`openai`-compatible or `anthropic`), `JUDGE_MODEL`, `JUDGE_API_KEY`,
  optionally `JUDGE_BASE_URL` and `JUDGE_MODEL_DATE`. The code refuses a judge equal to the generator
  or to the Cohere reranker. The judge only ever sees questions, answers and passages.
* `COHERE_API_KEY` (the reranker is part of the system under test) and an LLM for the generator.

## Run it

```bash
# once: build the eval image (adds ragas, langchain<1.0, scipy, matplotlib; the main image stays small)
docker compose --profile eval build eval
E="docker compose --profile eval run --rm eval --run run1"      # all state lives in the eval_data volume

$E testset --size 200          # Ragas builds questions + references from the ingested corpus; also splits 40/20/40
#   -> open eval_runs/run1/review_sample.csv, fill clear/answerable/reference_correct/keep (20% sample, ~40 questions)
$E split                       # re-split after review: questions with keep=0 are dropped, your ratings are kept
$E learn                       # 3 feedback rounds on the feedback split, Graph Noise Reduction per round, then freeze
$E learn --system abl_no_bm25  # ablations that keep a feedback loop learn their OWN memory without the removed part
$E learn --system abl_no_dense
$E learn --system abl_no_graph
$E run                         # 10 systems x 3 seeds on the held-out test split (frozen memory, resumable)
$E score                       # Ragas: Faithfulness, Answer Relevancy, Context Precision/Recall/Entity Recall, Noise Sensitivity
$E ratings                     # writes human_ratings.csv: rate ~30 answers, then re-run report for Cohen's kappa
$E report                      # tables, paired tests, plots -> eval_runs/run1/report/
$E beir                        # BEIR SciFact nDCG@10 sanity check for Objective 1
```

Outside Docker: `pip install -r requirements.txt -r requirements-eval.txt` then `python -m eval --run run1 <command>`
from `backend/` with `EVAL_DIR` pointing where results should go.

## What each stage does

| Stage | Output (in `eval_runs/<run>/`) | Notes |
|---|---|---|
| `testset` | `testset.jsonl`, `splits.json`, `review_sample.csv` | Ragas knowledge-graph + single/multi-hop synthesizers over one document per paper section. Types come from the synthesizer name. |
| `split` | `splits.json` | Stratified by question type so every split has the same single/multi-hop mix. |
| `learn` | `snapshots/initial.json`, `snapshots/learned*.json`, `feedback_rounds*.json` | Resets the memory to weight 0.5 / alpha 0.5, learns on the **feedback split only**, measures Graph Noise Reduction at round 0..3 on frozen weights (same exploration seed each time), then freezes. |
| `run` | `results/<system>__seed<k>.jsonl` | Systems without feedback use the *initial* graph; systems with feedback use their frozen *learned* graph. `learn=False` at test time: nothing leaks from the test split. Resumable. |
| `score` | `scores/*.jsonl` | Ragas 0.4 `ragas.metrics.collections`. Refusals ("insufficient evidence") score faithfulness 1, noise sensitivity 0, answer relevancy 0 without a judge call; empty contexts score 0 on the context metrics. |
| `report` | `report/report.md`, `results.csv`, `metrics.png`, `noise_reduction.png` | Mean + 95% bootstrap CI over questions; Full vs each baseline with paired bootstrap and Wilcoxon, Holm-corrected; ablation deltas; seed std; noise by round; review pass rate; kappa. |
| `manifest.json` | | Ragas version, judge model and date, generator, embedding model, reranker, every hyper-parameter, git commit. |

## The systems (Section 4.2)

| Name | What it is | Memory state |
|---|---|---|
| `full` | hybrid (adaptive alpha) + graph + reranker feedback + pruning | learned |
| `b1_bm25` / `b2_dense` | one retriever, top-5 straight to the generator | initial |
| `b3_static_hybrid` | alpha fixed at 0.5, no graph, no reranker | initial |
| `b4_static_graph` | hybrid + graph + reranker, weights never updated | initial |
| `b5_flat_rerank` | dense + reranker, no graph | initial |
| `abl_no_bm25` / `abl_no_dense` / `abl_no_graph` | Full with one part removed (learns its own memory) | own learned |
| `abl_no_feedback` | Full without the feedback loop (equals B4's configuration) | initial |

All systems share the same chunks, generator (temperature 0), context size k = 5 and claim verification setting.

## Things to know

* **Three seeds only vary what is random**: the 5% edge exploration. Systems without a graph walk are
  deterministic at temperature 0, so their seed variance will be ~0 (the report shows this honestly).
* **Cost.** `learn` makes ~240 reranker calls per system plus ~160 judge calls per measurement (cached across rounds);
  `run` makes up to 10 systems x 3 seeds x ~80 questions generator + verification calls; `score` makes ~6 judge calls
  per answer. Use `--limit` on `run` for a dry run. Cohere trial keys are rate limited (calls retry with backoff).
* **Nothing here has been run against a real judge yet.** The plumbing (splits, snapshots, frozen runs, resume,
  scoring conventions, statistics, report) is covered by `tests/test_eval_*.py` with a deterministic stand-in for the
  judge. The Ragas calls themselves need your judge key; run a small `--limit` first.
* `ragas` needs `langchain < 1.0` (see `requirements-eval.txt`).
