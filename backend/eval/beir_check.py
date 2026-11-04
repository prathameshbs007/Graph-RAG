"""BEIR SciFact sanity check (Objective 1).

Confirms that the retrieval stack (BM25, dense, hybrid fusion) behaves like published
systems on a standard scientific retrieval collection with human relevance labels.
nDCG@10 is computed here only; the main evaluation uses Ragas.

SciFact is indexed in its own temporary Weaviate class so the paper corpus is untouched.
"""

import time
from typing import Optional

from weaviate.util import generate_uuid5

from config import settings
from services.embedder import embed_documents, embed_query
from services.fusion import fuse_alpha
from services.weaviate_client import db

from eval.stats import ndcg_at_k

CLASS = "BeirScifact"
# BM25 nDCG@10 on SciFact reported in the BEIR paper (Thakur et al., 2021); compare, do not assume.
PUBLISHED_BM25 = 0.665


def _schema():
    return {
        "class": CLASS,
        "vectorizer": "none",
        "vectorIndexConfig": {"distance": "cosine"},
        "properties": [
            {"name": "doc_id", "dataType": ["text"], "tokenization": "field", "indexSearchable": False},
            {"name": "chunk_text", "dataType": ["text"]},
        ],
    }


def load_scifact():
    from datasets import load_dataset

    corpus = load_dataset("BeIR/scifact", "corpus", split="corpus")
    queries = load_dataset("BeIR/scifact", "queries", split="queries")
    qrels = load_dataset("BeIR/scifact-qrels", split="test")
    docs = {str(r["_id"]): f"{r['title']}. {r['text']}".strip() for r in corpus}
    qtext = {str(r["_id"]): r["text"] for r in queries}
    rel: dict[str, dict[str, int]] = {}
    for r in qrels:
        rel.setdefault(str(r["query-id"]), {})[str(r["corpus-id"])] = int(r["score"])
    return docs, {q: qtext[q] for q in rel if q in qtext}, rel


def index(docs: dict[str, str], batch: int = 64):
    client = db.client
    if client.schema.exists(CLASS):
        client.schema.delete_class(CLASS)
    client.schema.create_class(_schema())
    ids = list(docs)
    for i in range(0, len(ids), batch):
        part = ids[i : i + batch]
        vectors = embed_documents([docs[d] for d in part])
        with client.batch as b:
            b.batch_size = 100
            for d, v in zip(part, vectors):
                b.add_data_object({"doc_id": d, "chunk_text": docs[d]}, CLASS, uuid=generate_uuid5(d), vector=v)
        print(f"[beir] indexed {min(i + batch, len(ids))}/{len(ids)}")


def _search(builder):
    res = builder.do()
    if res.get("errors"):
        raise RuntimeError(str(res["errors"]))
    return res["data"]["Get"][CLASS] or []


def bm25(query: str, k: int):
    q = db.client.query.get(CLASS, ["doc_id"]).with_bm25(query=query, properties=["chunk_text"]).with_additional(["score"]).with_limit(k)
    return [(h["doc_id"], float(h["_additional"]["score"])) for h in _search(q)]


def dense(vector, k: int):
    q = db.client.query.get(CLASS, ["doc_id"]).with_near_vector({"vector": vector}).with_additional(["certainty"]).with_limit(k)
    return [(h["doc_id"], float(h["_additional"]["certainty"])) for h in _search(q)]


def evaluate(queries: dict[str, str], rel: dict[str, dict[str, int]], k: int = 10, alpha: float = 0.5, depth: Optional[int] = None) -> dict:
    depth = depth or settings.RETRIEVAL_TOP_K
    totals = {"bm25": [], "dense": [], "hybrid": []}
    for qid, text in queries.items():
        b = bm25(text, depth)
        d = dense(embed_query(text), depth)
        h = fuse_alpha(b, d, alpha)
        for name, ranked in (("bm25", b), ("dense", d), ("hybrid", h)):
            totals[name].append(ndcg_at_k([doc for doc, _ in ranked], rel[qid], k))
    return {name: sum(v) / len(v) for name, v in totals.items()}


def run(keep: bool = False) -> dict:
    t0 = time.time()
    docs, queries, rel = load_scifact()
    print(f"[beir] SciFact: {len(docs)} documents, {len(queries)} test queries")
    index(docs)
    try:
        result = evaluate(queries, rel)
    finally:
        if not keep:
            db.client.schema.delete_class(CLASS)
    result["seconds"] = round(time.time() - t0)
    result["published_bm25"] = PUBLISHED_BM25
    return result
