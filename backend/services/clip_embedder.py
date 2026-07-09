import logging

from fastembed import ImageEmbedding, TextEmbedding

logger = logging.getLogger(__name__)

FASTEMBED_CACHE_DIR = "/app/.fastembed_cache"
CLIP_VISION_MODEL_NAME = "Qdrant/clip-ViT-B-32-vision"
CLIP_TEXT_MODEL_NAME = "Qdrant/clip-ViT-B-32-text"


class ClipEmbedder:
    def __init__(self):
        self._image_model = None
        self._text_model = None

    def _lazy_init_image(self):
        if self._image_model is None:
            logger.info("Loading fastembed CLIP vision model %s...", CLIP_VISION_MODEL_NAME)
            self._image_model = ImageEmbedding(model_name=CLIP_VISION_MODEL_NAME, cache_dir=FASTEMBED_CACHE_DIR)

    def _lazy_init_text(self):
        if self._text_model is None:
            logger.info("Loading fastembed CLIP text model %s...", CLIP_TEXT_MODEL_NAME)
            self._text_model = TextEmbedding(model_name=CLIP_TEXT_MODEL_NAME, cache_dir=FASTEMBED_CACHE_DIR)

    def get_image_embedding(self, image_path: str) -> list[float]:
        self._lazy_init_image()
        try:
            embeddings = list(self._image_model.embed([image_path]))
            return embeddings[0].tolist()
        except Exception as e:
            logger.error("Failed to get image embedding for %s: %s", image_path, e)
            raise RuntimeError("Image embedding failed") from e

    def get_text_embedding_for_clip(self, text: str) -> list[float]:
        self._lazy_init_text()
        try:
            embeddings = list(self._text_model.embed([text]))
            return embeddings[0].tolist()
        except Exception as e:
            logger.error("Failed to get CLIP text embedding: %s", e)
            raise RuntimeError("CLIP text embedding failed") from e


clip_embedder = ClipEmbedder()
