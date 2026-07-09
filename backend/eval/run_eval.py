"""Small retrieval evaluation harness.

Ingests a synthetic sample paper with known facts, then runs a fixed set of
hand-written Q/A pairs against the live API (assumes the stack is already
running via docker compose, with a real GROQ_API_KEY configured). For each
question, checks:

  - hit: whether at least one retrieved source's chunk_text contains the
    expected keyword for that question (a crude proxy for "did retrieval
    find the right passage")
  - citation_present: whether the generated answer contains at least one
    [n]-style citation marker

Prints per-question results and summary metrics (retrieval hit-rate,
citation presence rate).

Usage (from repo root, with the stack running):
    docker compose exec backend python eval/run_eval.py
"""
import re
import time

import httpx

BASE_URL = "http://localhost:8000"

SAMPLE_PAPER_TEXT = {
    1: """GraphRAG: Combining Knowledge Graphs with Retrieval-Augmented Generation

Abstract: We present GraphRAG, a retrieval-augmented generation system that
enriches standard vector retrieval with knowledge graph traversal. Unlike
prior RAG systems that treat each document chunk independently, GraphRAG
extracts concepts and citation relationships at ingestion time and uses
graph traversal to surface related papers that share concepts with the
retrieved results, even if those papers were not directly retrieved by the
vector search.""",
    2: """2 Retrieval Architecture

GraphRAG stores text chunks, figure crops, and audio transcript segments in
three separate Qdrant collections. Text and audio chunks are embedded with
the fastembed BAAI/bge-small-en-v1.5 model, which produces 384-dimensional
vectors. Figure crops are embedded separately in CLIP space using
Qdrant/clip-ViT-B-32-vision, at 512 dimensions, so that image and text
scores are never compared directly.""",
    3: """3 Concept Extraction

At ingestion time, a single Groq language model call over the first three
pages of each paper extracts a list of key concepts and any cited paper
titles found in the text. Concepts become Concept nodes in Neo4j connected
to the paper via a HAS_CONCEPT edge. Cited titles are fuzzy-matched
case-insensitively against existing Paper titles to create CITES edges
between papers already in the system.""",
    4: """4 Reranking

Retrieved text and audio chunks are reranked using the fastembed
cross-encoder Xenova/ms-marco-MiniLM-L-6-v2 before being passed to the
language model. Figure results are never included in this reranking step,
since CLIP similarity scores and cross-encoder text scores are not on a
comparable scale.""",
    5: """5 Experiments

On a held-out set of 40 queries against a 12-paper corpus, adding graph
context enrichment improved recall at 10 from 61 percent to 78 percent
compared to vector-only retrieval. Reranking with the cross-encoder further
reduced the average rank of the gold passage from 4.2 to 1.8.""",
    6: """6 Conclusion

We showed that combining lightweight LLM-based concept extraction with
graph traversal at query time meaningfully improves retrieval quality over
vector search alone, without requiring a separate graph neural network or
manual annotation.""",
}

QA_PAIRS = [
    ("What model is used to embed text chunks in GraphRAG?", "bge-small"),
    ("How many dimensions does the text embedding have?", "384"),
    ("What vector database does GraphRAG use to store chunks?", "Qdrant"),
    ("How many separate collections are used to store chunks?", "three"),
    ("What CLIP model embeds figure crops?", "clip-vit-b-32-vision"),
    ("How many dimensions does the figure embedding have?", "512"),
    ("What creates the HAS_CONCEPT edges in the graph?", "concept extraction"),
    ("How are cited titles matched to existing papers?", "fuzzy-matched"),
    ("What model reranks retrieved chunks?", "ms-marco-minilm"),
    ("Are figure results included in reranking?", "never"),
    ("What was the recall at 10 improvement from graph context?", "61"),
    ("What was the average rank of the gold passage after reranking?", "1.8"),
    ("How many queries were used in the held-out evaluation set?", "40"),
    ("How many papers were in the evaluation corpus?", "12"),
]


def wait_for_health(client: httpx.Client, timeout: int = 60):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = client.get(f"{BASE_URL}/health", timeout=5)
            if r.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(2)
    raise RuntimeError("Backend did not become healthy in time")


def build_sample_pdf(path: str):
    import fitz
    doc = fitz.open()
    for text in SAMPLE_PAPER_TEXT.values():
        page = doc.new_page()
        page.insert_text((72, 72), text, fontsize=10)
    doc.save(path)


def ingest_sample_paper(client: httpx.Client, path: str) -> str:
    with open(path, "rb") as f:
        resp = client.post(
            f"{BASE_URL}/ingest/pdf",
            files={"file": ("eval_sample.pdf", f, "application/pdf")},
            data={"title": "GraphRAG: Combining Knowledge Graphs with Retrieval-Augmented Generation"},
        )
    resp.raise_for_status()
    paper_id = resp.json()["id"]

    for _ in range(30):
        status = client.get(f"{BASE_URL}/ingest/status/{paper_id}").json()
        if status.get("status") == "done":
            return paper_id
        if status.get("status") == "error":
            raise RuntimeError(f"Ingestion failed: {status.get('detail')}")
        time.sleep(1)
    raise RuntimeError("Ingestion did not complete in time")


def run_eval(client: httpx.Client):
    hits = 0
    citations = 0
    print(f"{'Question':<65} {'Hit':<5} {'Cited':<5}")
    print("-" * 80)
    for question, expected_keyword in QA_PAIRS:
        resp = client.post(f"{BASE_URL}/query", json={"text": question}, timeout=60)
        resp.raise_for_status()
        body = resp.json()

        source_text = " ".join(s["chunk_text"] for s in body.get("sources", [])).lower()
        hit = expected_keyword.lower() in source_text
        cited = bool(re.search(r"\[\d+\]", body.get("answer", "")))

        hits += hit
        citations += cited
        print(f"{question:<65} {'Y' if hit else 'N':<5} {'Y' if cited else 'N':<5}")

    n = len(QA_PAIRS)
    print("-" * 80)
    print(f"Retrieval hit-rate:     {hits}/{n} ({100 * hits / n:.0f}%)")
    print(f"Citation presence rate: {citations}/{n} ({100 * citations / n:.0f}%)")


if __name__ == "__main__":
    with httpx.Client() as client:
        wait_for_health(client)
        pdf_path = "/tmp/eval_sample.pdf"
        build_sample_pdf(pdf_path)
        ingest_sample_paper(client, pdf_path)
        run_eval(client)
