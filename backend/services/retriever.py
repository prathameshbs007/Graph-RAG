import logging
from typing import Optional

from qdrant_client.models import SparseVector

from config import settings
from services.clip_embedder import clip_embedder
from services.embedder import get_text_embedding
from services.neo4j_client import graph_db
from services.qdrant_client import db
from services.reranker import reranker
from services.sparse_embedder import get_sparse_embedding

logger = logging.getLogger(__name__)


def _sparse_query_vector(query_text: str) -> Optional[SparseVector]:
    if not settings.HYBRID_SEARCH:
        return None
    try:
        se = get_sparse_embedding(query_text)
        return SparseVector(indices=se.indices.tolist(), values=se.values.tolist())
    except Exception as e:
        logger.error("Sparse query embedding failed, falling back to dense-only search: %s", e)
        return None


def retrieve_context(query_text: str, top_k: Optional[int] = None, rerank_top_n: Optional[int] = None):
    top_k = top_k if top_k is not None else settings.RETRIEVAL_TOP_K
    rerank_top_n = rerank_top_n if rerank_top_n is not None else settings.RERANK_TOP_N

    # 1. Embed Query
    query_vector = get_text_embedding(query_text)
    clip_vector = clip_embedder.get_text_embedding_for_clip(query_text)
    sparse_query = _sparse_query_vector(query_text)

    # 2. Qdrant Top-K, kept as separate text-space and CLIP-space result sets
    text_results, image_results = db.search_all_classes(
        query_vector, clip_vector=clip_vector, sparse_query=sparse_query, limit=top_k
    )

    if not text_results and not image_results:
        return [], [], {"related_papers": [], "concepts": []}

    # Extract unique paper IDs
    all_results = text_results + image_results
    paper_ids = list(set([res["paper_id"] for res in all_results if res.get("paper_id")]))

    # 3. Neo4j Graph Traversal
    graph_context = graph_db.get_related_graph_context(paper_ids)

    # 4. Rerank: text/audio chunks only. Figures are never mixed into this ranking.
    docs_for_rerank = [res.get("chunk_text", "") for res in text_results]
    top_indices = reranker.rerank(query_text, docs_for_rerank, top_n=rerank_top_n)
    reranked_text_results = [text_results[i] for i in top_indices] if text_results else []

    sources = []
    for res in reranked_text_results:
        sources.append({
            "chunk_id": res.get("chunk_id", ""),
            "paper_id": res.get("paper_id", ""),
            "paper_title": res.get("paper_title", ""),
            "authors": res.get("authors", []),
            "year": res.get("year", None),
            "chunk_text": res.get("chunk_text", ""),
            "score": res.get("score", 0.0),
            "modality": res["modality"],
            "start_time": res.get("start_time"),
            "end_time": res.get("end_time"),
        })

    figures = []
    for res in image_results:
        figures.append({
            "figure_id": res.get("figure_id", ""),
            "paper_id": res.get("paper_id", ""),
            "paper_title": res.get("paper_title", ""),
            "page": res.get("page", 0),
            "caption": res.get("caption", ""),
            "url": f"/figures/{res.get('figure_id')}" if res.get("figure_id") else "",
            "score": res.get("score", 0.0)
        })

    return sources, figures, graph_context
