import requests
from config import settings

def get_text_embedding(text: str) -> list[float]:
    """Get embedding from local Ollama instance"""
    try:
        response = requests.post(
            f"{settings.OLLAMA_URL}/api/embeddings",
            json={
                "model": settings.EMBED_MODEL,
                "prompt": text
            },
            timeout=30.0
        )
        response.raise_for_status()
        return response.json().get("embedding", [])
    except Exception as e:
        print(f"Failed to get embedding: {e}")
        return []
