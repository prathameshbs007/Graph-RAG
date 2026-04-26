import os
from services.weaviate_client import db
from services.neo4j_client import graph_db
from services.embedder import get_text_embedding
from services.reranker import reranker
from config import settings

def retrieve_context(query_text: str):
    # 1. Embed Query
    query_vector = get_text_embedding(query_text)
    
    # 2. Weaviate Top-K
    weaviate_results = db.search_all_classes(query_vector, limit=settings.RETRIEVAL_TOP_K)
    
    if not weaviate_results:
        return [], [], {"related_papers": [], "concepts": []}
    
    # Extract unique paper IDs
    paper_ids = list(set([res["paper_id"] for res in weaviate_results if res.get("paper_id")]))
    
    # 3. Neo4j Graph Traversal
    graph_context = graph_db.get_related_graph_context(paper_ids)
    
    # 4. Cohere Rerank
    docs_for_rerank = [res.get("chunk_text", "") for res in weaviate_results]
    
    top_indices = reranker.rerank(query_text, docs_for_rerank, top_n=settings.COHERE_TOP_N)
    reranked_results = [weaviate_results[i] for i in top_indices]
    
    sources = []
    figures = []
    
    for res in reranked_results:
        if res["modality"] == "image":
            figures.append({
                "figure_id": res.get("figure_id", ""),
                "paper_id": res.get("paper_id", ""),
                "paper_title": res.get("paper_title", ""),
                "page": res.get("page", 0),
                "caption": res.get("caption", ""),
                "url": f"/figures/{os.path.basename(res.get('file_path', ''))}" if res.get("file_path") else "",
                "score": res.get("score", 0.0)
            })
        else:
            sources.append({
                "chunk_id": res.get("chunk_id", ""),
                "paper_id": res.get("paper_id", ""),
                "paper_title": res.get("paper_title", ""),
                "authors": res.get("authors", []),
                "year": res.get("year", None),
                "chunk_text": res.get("chunk_text", ""),
                "score": res.get("score", 0.0),
                "modality": res["modality"]
            })
            
    return sources, figures, graph_context
