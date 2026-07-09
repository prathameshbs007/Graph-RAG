import logging

import torch
from PIL import Image
import open_clip
from config import settings

logger = logging.getLogger(__name__)


class ClipEmbedder:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model = None
        self._preprocess = None

    def _lazy_init(self):
        if self._model is None:
            logger.info("Downloading/Loading CLIP model...")
            self._model, _, self._preprocess = open_clip.create_model_and_transforms(
                settings.CLIP_MODEL, pretrained='openai', device=self.device
            )

    def get_image_embedding(self, image_path: str) -> list[float]:
        self._lazy_init()
        try:
            image = Image.open(image_path).convert("RGB")
            image = image.resize((224, 224))
            image_tensor = self._preprocess(image).unsqueeze(0).to(self.device)

            with torch.no_grad():
                image_features = self._model.encode_image(image_tensor)
                image_features /= image_features.norm(dim=-1, keepdim=True)

            return image_features.cpu().numpy()[0].tolist()
        except Exception as e:
            logger.error("Failed to get image embedding for %s: %s", image_path, e)
            raise RuntimeError("Image embedding failed") from e

    def get_text_embedding_for_clip(self, text: str) -> list[float]:
        self._lazy_init()
        try:
            tokenizer = open_clip.get_tokenizer(settings.CLIP_MODEL)
            text_tokens = tokenizer([text]).to(self.device)
            with torch.no_grad():
                text_features = self._model.encode_text(text_tokens)
                text_features /= text_features.norm(dim=-1, keepdim=True)
            return text_features.cpu().numpy()[0].tolist()
        except Exception as e:
            logger.error("Failed to get CLIP text embedding: %s", e)
            raise RuntimeError("CLIP text embedding failed") from e

clip_embedder = ClipEmbedder()
