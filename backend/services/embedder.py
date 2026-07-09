import logging
from typing import List, Union

from fastembed import TextEmbedding

logger = logging.getLogger(__name__)

FASTEMBED_CACHE_DIR = "/app/.fastembed_cache"
TEXT_MODEL_NAME = "BAAI/bge-small-en-v1.5"

_model: Union[TextEmbedding, None] = None


def _get_model() -> TextEmbedding:
    global _model
    if _model is None:
        logger.info("Loading fastembed text embedding model %s...", TEXT_MODEL_NAME)
        _model = TextEmbedding(model_name=TEXT_MODEL_NAME, cache_dir=FASTEMBED_CACHE_DIR)
    return _model


def get_text_embedding(text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
    """Get embedding(s) via fastembed (in-process ONNX). Raises RuntimeError on failure."""
    try:
        model = _get_model()
        if isinstance(text, str):
            embeddings = list(model.embed([text]))
            return embeddings[0].tolist()
        embeddings = list(model.embed(text))
        return [e.tolist() for e in embeddings]
    except Exception as e:
        logger.error("Failed to get fastembed text embedding: %s", e)
        raise RuntimeError("Embedding request failed") from e
