"""Test-set generation with Ragas (Module 5, step 1).

Ragas builds a knowledge graph over the corpus and writes single-hop and multi-hop
questions with reference answers and reference contexts. The corpus is whatever is
ingested in ResearchOS, so the questions come from the project's own papers.

After generation a 20% sample is exported for human review (clarity, answerability,
correct reference), and the questions are split 40 / 20 / 40 by type.
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

from eval.splits import query_type, review_sample, stratified_split
from services.weaviate_client import db

REVIEW_COLUMNS = ["id", "question", "reference", "query_type", "clear", "answerable", "reference_correct", "keep", "notes"]


def load_corpus_documents(min_words: int = 60) -> list[dict]:
    """One document per (paper, section) built from the stored text chunks, in reading order."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for c in db.iterate_chunks():
        if c.get("modality") == "text" and c.get("paper_id"):
            groups[(c["paper_id"], c.get("section") or "")].append(c)
    docs = []
    for (paper_id, section), chunks in groups.items():
        chunks.sort(key=lambda c: c.get("chunk_index") or 0)
        text = "\n".join(c["chunk_text"] for c in chunks)
        if len(text.split()) >= min_words:
            docs.append(
                {"text": text, "metadata": {"paper_id": paper_id, "paper_title": chunks[0].get("paper_title"), "section": section}}
            )
    return docs


def generate(run_dir: Path, size: int, judge_cfg) -> list[dict]:
    """Generate ``size`` questions with Ragas and write ``testset.jsonl``."""
    from langchain_core.documents import Document
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.testset import TestsetGenerator

    from eval import judge

    docs = load_corpus_documents()
    if not docs:
        raise RuntimeError("The knowledge base is empty: ingest the paper corpus first.")
    lc_docs = [Document(page_content=d["text"], metadata=d["metadata"]) for d in docs]
    print(f"[testset] {len(lc_docs)} corpus documents -> generating {size} questions")

    generator = TestsetGenerator(
        llm=LangchainLLMWrapper(judge.build_langchain_chat(judge_cfg)),
        embedding_model=LangchainEmbeddingsWrapper(judge.build_langchain_embeddings()),
    )
    df = generator.generate_with_langchain_docs(lc_docs, testset_size=size).to_pandas()

    rows = []
    for i, rec in enumerate(df.to_dict("records")):
        rows.append(
            {
                "id": f"q{i:04d}",
                "question": rec["user_input"],
                "reference": rec["reference"],
                "reference_contexts": list(rec.get("reference_contexts") or []),
                "query_type": query_type(str(rec.get("synthesizer_name", ""))),
                "synthesizer": str(rec.get("synthesizer_name", "")),
            }
        )
    write_jsonl(run_dir / "testset.jsonl", rows)
    print(f"[testset] wrote {len(rows)} questions to {run_dir / 'testset.jsonl'}")
    return rows


def split_and_export(run_dir: Path, seed: int = 13) -> dict:
    """Write ``splits.json`` and the human-review sheet ``review_sample.csv``."""
    rows = read_jsonl(run_dir / "testset.jsonl")
    # questions a reviewer marked keep=0 in review_sample.csv are dropped before splitting
    removed = rejected_ids(run_dir)
    rows = [r for r in rows if r["id"] not in removed]
    splits = stratified_split(rows, seed=seed)
    (run_dir / "splits.json").write_text(
        json.dumps({k: [r["id"] for r in v] for k, v in splits.items()}, indent=2), encoding="utf-8"
    )
    sheet = run_dir / "review_sample.csv"
    if not sheet.exists():  # never overwrite ratings a human already entered
        with open(sheet, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=REVIEW_COLUMNS)
            w.writeheader()
            for r in review_sample(read_jsonl(run_dir / "testset.jsonl"), seed=seed):
                w.writerow({k: r.get(k, "") for k in REVIEW_COLUMNS})
    return {k: len(v) for k, v in splits.items()}


def rejected_ids(run_dir: Path) -> set[str]:
    sheet = run_dir / "review_sample.csv"
    if not sheet.exists():
        return set()
    with open(sheet, newline="", encoding="utf-8") as f:
        return {r["id"] for r in csv.DictReader(f) if str(r.get("keep", "")).strip() in ("0", "no", "n", "false")}


def load_split(run_dir: Path, name: str) -> list[dict]:
    ids = json.loads((run_dir / "splits.json").read_text(encoding="utf-8"))[name]
    by_id = {r["id"]: r for r in read_jsonl(run_dir / "testset.jsonl")}
    return [by_id[i] for i in ids if i in by_id]


def write_jsonl(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
