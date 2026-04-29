import requests
from config import settings
from typing import Union, List
import time

def get_text_embedding(text: Union[str, List[str]], retry=3) -> Union[list[float], List[list[float]]]:
    """Get embedding from local Ollama instance (supports single string or list of strings)"""
    for attempt in range(retry):
        try:
            response = requests.post(
                f"{settings.OLLAMA_URL}/api/embed",
                json={
                    "model": settings.EMBED_MODEL,
                    "input": text
                },
                timeout=120.0  # Increased timeout from 30s to 120s
            )
            response.raise_for_status()
            embeds = response.json().get("embeddings", [])
            
            if isinstance(text, str):
                return embeds[0] if embeds else []
            return embeds
        except requests.exceptions.Timeout:
            print(f"Embedding request timeout (attempt {attempt+1}/{retry}), retrying...")
            if attempt < retry - 1:
                time.sleep(5)  # Wait before retry
            else:
                print(f"Failed to get embedding after {retry} attempts: timeout")
                return [] if isinstance(text, str) else [[] for _ in text]
        except Exception as e:
            print(f"Failed to get embedding: {e}")
            return [] if isinstance(text, str) else [[] for _ in text]
