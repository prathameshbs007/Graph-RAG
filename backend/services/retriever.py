import os
from services.weaviate_client import db
from services.neo4j_client import graph_db
from services.embedder import get_text_embedding
from services.reranker import reranker
from config import settings
from services.clip_embedder import clip_embedder

def retrieve_context(query_text: str):
    # 1. Embed Query
    query_vector = get_text_embedding(query_text)
    clip_vector = clip_embedder.get_text_embedding_for_clip(query_text)
    
    print(f"[DEBUG] Query text: {query_text}")
    print(f"[DEBUG] Query vector length: {len(query_vector) if query_vector else 'None'}")
    
    # 2. Weaviate Top-K
    weaviate_results = db.search_all_classes(query_vector, clip_vector=clip_vector, limit=settings.RETRIEVAL_TOP_K)
    
    print(f"[DEBUG] Weaviate results count: {len(weaviate_results)}")
    for i, res in enumerate(weaviate_results[:5]):
        print(f"[DEBUG]  [{i}] modality={res.get('modality')}, score={res.get('score')}, text_len={len(res.get('chunk_text', ''))}")
    
    if not weaviate_results:
        return [], [], {"related_papers": [], "concepts": []}
    
    # Extract unique paper IDs
    paper_ids = list(set([res["paper_id"] for res in weaviate_results if res.get("paper_id")]))
    
    # 3. Neo4j Graph Traversal
    graph_context = graph_db.get_related_graph_context(paper_ids)
    
    # 4. Cohere Rerank: Only rerank text/audio chunks. Protect figures.
    text_results = [res for res in weaviate_results if res["modality"] != "image"]
    image_results = [res for res in weaviate_results if res["modality"] == "image"]
    
    docs_for_rerank = [res.get("chunk_text", "") for res in text_results]
    
    top_indices = reranker.rerank(query_text, docs_for_rerank, top_n=settings.COHERE_TOP_N)
    
    reranked_results = [text_results[i] for i in top_indices] if text_results else []
    # Re-append images at the end of the ranked results
    reranked_results.extend(image_results)
    
    sources = []
    figures = []
    
    for res in reranked_results:
        if res["modality"] == "image":
            # Always include image caption in sources for LLM context
            caption = res.get("caption", "")
            if caption:  # Only add if caption exists
                sources.append({
                    "chunk_id": res.get("figure_id", ""),
                    "paper_id": res.get("paper_id", ""),
                    "paper_title": res.get("paper_title", ""),
                    "authors": [],
                    "year": None,
                    "chunk_text": f"[IMAGE: {caption}]",
                    "score": res.get("score", 0.0),
                    "modality": "image"
                })
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
