import torch
from PIL import Image
import open_clip
from config import settings

class ClipEmbedder:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        model_name = settings.CLIP_MODEL
        # Use a pretrained weight associated with ViT-B/32, standard is openai
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            model_name, pretrained='openai', device=self.device
        )
        self.tokenizer = open_clip.get_tokenizer(model_name)
    
    def get_image_embedding(self, image_path: str) -> list[float]:
        try:
            image = Image.open(image_path).convert("RGB")
            # Convert to RGB and resize to 224x224 as required, then transform
            image = image.resize((224, 224))
            image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                image_features = self.model.encode_image(image_tensor)
                image_features /= image_features.norm(dim=-1, keepdim=True)
            
            return image_features.cpu().numpy()[0].tolist()
        except Exception as e:
            print(f"Failed to get image embedding: {e}")
            return []

clip_embedder = ClipEmbedder()
