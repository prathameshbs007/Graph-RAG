import requests
from config import settings
from typing import Union, List

def get_text_embedding(text: Union[str, List[str]]) -> Union[list[float], List[list[float]]]:
    """Get embedding from local Ollama instance (supports single string or list of strings)"""
    try:
        response = requests.post(
            f"{settings.OLLAMA_URL}/api/embed",
            json={
                "model": settings.EMBED_MODEL,
                "input": text
            },
            timeout=120.0  # Increased to 120 seconds for slow machines or cold starts
        )
        response.raise_for_status()
        embeds = response.json().get("embeddings", [])
        
        if isinstance(text, str):
            return embeds[0] if embeds else []
        return embeds
    except Exception as e:
        print(f"Failed to get embedding: {e}")
        return [] if isinstance(text, str) else [[] for _ in text]
