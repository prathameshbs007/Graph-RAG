import cohere
from config import settings

class Reranker:
    def __init__(self):
        self.api_key = settings.COHERE_API_KEY
        if self.api_key and self.api_key != "your_cohere_api_key_here":
            self.client = cohere.Client(self.api_key)
        else:
            self.client = None

    def rerank(self, query: str, documents: list[str], top_n: int = 5) -> list[int]:
        if not self.client or not documents:
            return list(range(min(len(documents), top_n)))
            
        try:
            response = self.client.rerank(
                model=settings.COHERE_RERANK_MODEL,
                query=query,
                documents=documents,
                top_n=top_n
            )
            return [result.index for result in response.results]
        except Exception as e:
            print(f"Cohere rerank error: {e}")
            return list(range(min(len(documents), top_n)))

reranker = Reranker()
