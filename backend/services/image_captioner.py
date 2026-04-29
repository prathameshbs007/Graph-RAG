import base64
import requests
from config import settings

class ImageCaptioner:
    """Auto-generates detailed text descriptions of images using local Ollama with llava model."""
    
    def __init__(self):
        self.ollama_url = settings.OLLAMA_URL
        self.model = "llava"  # Vision model in Ollama
    
    def caption_image(self, image_path: str) -> str:
        """Generate a detailed text description of an image using Ollama llava."""
        try:
            # Read and encode image
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            
            base64_image = base64.b64encode(image_bytes).decode("utf-8")
            
            prompt = (
                "Describe this image in detail for a knowledge retrieval system. "
                "Include: what the image shows, all text/labels visible, "
                "any diagrams/flowcharts/architecture and their components, "
                "relationships between elements, and key concepts. "
                "Be thorough and factual. Keep response concise."
            )
            
            print(f"Sending image to Ollama ({self.model}) for captioning...")
            
            # Use Ollama's generate endpoint with vision support
            payload = {
                "model": self.model,
                "prompt": prompt,
                "images": [base64_image],
                "stream": False
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=120.0  # Increased timeout for vision model
            )
            response.raise_for_status()
            data = response.json()
            
            description = data.get("response", "").strip()
            
            if description:
                print(f"Auto-generated caption ({len(description)} chars): {description[:100]}...")
            else:
                print("Warning: Empty caption generated from Ollama")
            
            return description
            
        except requests.exceptions.ConnectionError:
            print("Ollama not reachable, using filename as caption")
            return ""
        except requests.exceptions.Timeout:
            print("Ollama vision request timed out, using filename as caption")
            return ""
        except Exception as e:
            print(f"Image captioning with Ollama failed: {e}")
            return ""

image_captioner = ImageCaptioner()
