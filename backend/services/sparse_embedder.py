import logging
from typing import List, Union

from fastembed import SparseTextEmbedding
from fastembed.sparse.sparse_embedding_base import SparseEmbedding

logger = logging.getLogger(__name__)

FASTEMBED_CACHE_DIR = "/app/.fastembed_cache"
SPARSE_MODEL_NAME = "Qdrant/bm25"

_model: Union[SparseTextEmbedding, None] = None


def _get_model() -> SparseTextEmbedding:
    global _model
    if _model is None:
        logger.info("Loading fastembed sparse embedding model %s...", SPARSE_MODEL_NAME)
        _model = SparseTextEmbedding(model_name=SPARSE_MODEL_NAME, cache_dir=FASTEMBED_CACHE_DIR)
    return _model


def get_sparse_embedding(text: Union[str, List[str]]) -> Union[SparseEmbedding, List[SparseEmbedding]]:
    """Get BM25 sparse embedding(s) via fastembed. Raises RuntimeError on failure."""
    try:
        model = _get_model()
        if isinstance(text, str):
            embeddings = list(model.embed([text]))
            return embeddings[0]
        return list(model.embed(text))
    except Exception as e:
        logger.error("Failed to get sparse embedding: %s", e)
        raise RuntimeError("Sparse embedding request failed") from e
