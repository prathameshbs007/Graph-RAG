"""Cohere cross-encoder reranker.

Module 3 needs a relevance score for *every* candidate (low scores are the negative
feedback that prunes noisy edges), so unlike a plain top-n reranker this returns one
score per input document, aligned with the input order.
"""

from typing import Optional

from config import settings
from services.llm import with_retries


class Reranker:
    def __init__(self):
        self._client = None

    @property
    def available(self) -> bool:
        key = settings.COHERE_API_KEY
        return bool(key) and key != "your_cohere_api_key_here"

    def _get_client(self):
        if self._client is None:
            import cohere

            cls = getattr(cohere, "ClientV2", None) or cohere.Client
            self._client = cls(settings.COHERE_API_KEY)
        return self._client

    def score(self, query: str, documents: list[str]) -> Optional[list[float]]:
        """Relevance scores in [0, 1] aligned with ``documents``; ``None`` if unavailable."""
        if not documents:
            return []
        if not self.available:
            return None
        try:
            client = self._get_client()
            response = with_retries(
                lambda: client.rerank(
                    model=settings.COHERE_RERANK_MODEL,
                    query=query,
                    documents=documents,
                    top_n=len(documents),
                )
            )
        except Exception as exc:  # noqa: BLE001
            print(f"Cohere rerank error: {exc}")
            return None
        scores = [0.0] * len(documents)
        for r in response.results:
            scores[r.index] = float(r.relevance_score)
        return scores


reranker = Reranker()
