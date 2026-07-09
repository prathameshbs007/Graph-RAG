import logging
from typing import Union, List

import requests
from config import settings

logger = logging.getLogger(__name__)


def get_text_embedding(text: Union[str, List[str]]) -> Union[list[float], List[list[float]]]:
    """Get embedding(s) from local Ollama instance. Raises RuntimeError on failure."""
    try:
        response = requests.post(
            f"{settings.OLLAMA_URL}/api/embed",
            json={
                "model": settings.EMBED_MODEL,
                "input": text
            },
            timeout=30.0
        )
        response.raise_for_status()
        embeds = response.json().get("embeddings", [])
    except Exception as e:
        logger.error("Failed to get embedding from Ollama: %s", e)
        raise RuntimeError("Embedding request failed") from e

    if isinstance(text, str):
        if not embeds:
            raise RuntimeError("Ollama returned no embedding")
        return embeds[0]

    if len(embeds) != len(text):
        raise RuntimeError("Ollama returned mismatched number of embeddings")
    return embeds
