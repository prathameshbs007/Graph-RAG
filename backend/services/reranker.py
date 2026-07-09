import logging
from typing import Optional

from fastembed.rerank.cross_encoder import TextCrossEncoder

from config import settings

logger = logging.getLogger(__name__)

FASTEMBED_CACHE_DIR = "/app/.fastembed_cache"
RERANK_MODEL_NAME = "Xenova/ms-marco-MiniLM-L-6-v2"


class Reranker:
    def __init__(self):
        self._model = None

    def _lazy_init(self):
        if self._model is None:
            logger.info("Loading fastembed cross-encoder reranker %s...", RERANK_MODEL_NAME)
            self._model = TextCrossEncoder(model_name=RERANK_MODEL_NAME, cache_dir=FASTEMBED_CACHE_DIR)

    def rerank(self, query: str, documents: list[str], top_n: Optional[int] = None) -> list[int]:
        top_n = top_n if top_n is not None else settings.RERANK_TOP_N
        if not documents:
            return []
        try:
            self._lazy_init()
            scores = list(self._model.rerank(query, documents))
            ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
            return ranked[:top_n]
        except Exception as e:
            logger.error("Reranker error: %s", e)
            return list(range(min(len(documents), top_n)))


reranker = Reranker()
