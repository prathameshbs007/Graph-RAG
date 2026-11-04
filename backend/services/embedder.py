"""Dense embeddings from the local Ollama instance.

Failures raise ``EmbeddingError`` instead of returning empty vectors: silently
storing a chunk with no vector makes it invisible to dense search forever.
"""

from typing import List

import requests

from config import settings
from services.llm import with_retries


class EmbeddingError(RuntimeError):
    pass


def _embed(inputs: List[str]) -> List[list]:
    def call():
        r = requests.post(
            f"{settings.OLLAMA_URL}/api/embed",
            json={"model": settings.EMBED_MODEL, "input": inputs},
            timeout=120.0,  # cold model loads on slow machines
        )
        r.raise_for_status()
        return r.json().get("embeddings", [])

    try:
        vectors = with_retries(call, retries=2, base_delay=2.0)
    except Exception as exc:  # noqa: BLE001
        raise EmbeddingError(f"embedding request failed: {exc}") from exc
    if len(vectors) != len(inputs) or any(not v for v in vectors):
        raise EmbeddingError(f"expected {len(inputs)} embeddings, got {len(vectors)} (some empty)")
    return vectors


def embed_query(text: str) -> list:
    return _embed([settings.EMBED_QUERY_PREFIX + text])[0]


def embed_documents(texts: List[str]) -> List[list]:
    """Embed passages in batches (keeps request size and latency bounded)."""
    out: List[list] = []
    step = max(1, settings.EMBED_BATCH_SIZE)
    for i in range(0, len(texts), step):
        batch = [settings.EMBED_DOC_PREFIX + t for t in texts[i : i + step]]
        out.extend(_embed(batch))
    return out
