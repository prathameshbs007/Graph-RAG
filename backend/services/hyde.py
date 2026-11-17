"""HyDE – Hypothetical Document Embeddings (pre-retrieval query augmentation).

Instead of embedding the raw user query for dense search, HyDE asks the LLM to
*hallucinate* a plausible expert answer to the query.  The hallucinated text is
then embedded with the **document** prefix so that its vector lives in the same
subspace as real stored passages.  BM25 always keeps the original query.

Usage inside the pipeline::

    from services.hyde import hyde

    hyde_vector = hyde.generate(raw_query)   # None when disabled / LLM unavailable
    # pass raw_query to bm25(), hyde_vector (or embed_query) to dense()

The feature is controlled by two env vars:

  HYDE_ENABLED=true          # set to false to bypass entirely (default: true)
  HYDE_TEMPERATURE=0.7       # temperature for the hallucination step (default: 0.7)
  HYDE_MAX_TOKENS=256        # keep the hallucination short (default: 256)
"""

import logging
from typing import Optional

import requests

from config import settings
from services.embedder import EmbeddingError, _embed

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------
_SYSTEM = (
    "You are an expert researcher. "
    "Write a concise, technically precise paragraph (3–5 sentences) that directly "
    "answers the question as if it appeared in a peer-reviewed paper or textbook. "
    "Do NOT hedge or say 'I don't know' – produce the most plausible factual answer."
)


def _hyde_prompt(query: str) -> list[dict]:
    return [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": query},
    ]


# ---------------------------------------------------------------------------
# HyDE generator
# ---------------------------------------------------------------------------
class HyDEGenerator:
    """Generate a dense vector from a hallucinated expert answer."""

    def _call_ollama(self, query: str) -> str:
        """Always uses Ollama/llama3.1:8b regardless of LLM_PROVIDER setting."""
        payload = {
            "model": settings.OLLAMA_LLM_MODEL,
            "messages": _hyde_prompt(query),
            "stream": False,
            "options": {
                "temperature": settings.HYDE_TEMPERATURE,
                "num_predict": settings.HYDE_MAX_TOKENS,
            },
        }
        r = requests.post(
            f"{settings.OLLAMA_URL}/api/chat",
            json=payload,
            timeout=120,
        )
        r.raise_for_status()
        return r.json().get("message", {}).get("content", "").strip()

    def _call_groq(self, query: str) -> str:
        """Fallback: use Groq if Ollama is unavailable."""
        from groq import Groq

        client = Groq(api_key=settings.GROQ_API_KEY)
        res = client.chat.completions.create(
            messages=_hyde_prompt(query),
            model=settings.GROQ_MODEL,
            temperature=settings.HYDE_TEMPERATURE,
            max_tokens=settings.HYDE_MAX_TOKENS,
        )
        return (res.choices[0].message.content or "").strip()

    def _hallucinate(self, query: str) -> str:
        """Return hallucinated expert answer; prefer local Ollama, fall back to Groq."""
        try:
            text = self._call_ollama(query)
            if text:
                return text
        except Exception as exc:  # noqa: BLE001
            logger.warning("HyDE: Ollama call failed (%s), trying Groq fallback", exc)

        # Groq fallback (only if key is configured)
        if settings.GROQ_API_KEY and settings.GROQ_API_KEY != "your_groq_api_key_here":
            try:
                return self._call_groq(query)
            except Exception as exc:  # noqa: BLE001
                logger.warning("HyDE: Groq fallback also failed (%s)", exc)

        return ""

    def generate(self, query: str) -> Optional[list[float]]:
        """Return a dense vector from the hallucinated answer, or ``None`` on failure.

        Returns ``None`` (instead of raising) so the pipeline can degrade gracefully
        to a plain query embedding for the dense leg.
        """
        if not settings.HYDE_ENABLED:
            return None

        hypo = self._hallucinate(query)
        if not hypo:
            logger.warning("HyDE: empty hallucination for query %r – falling back to query embedding", query[:80])
            return None

        logger.debug("HyDE hallucination (first 120 chars): %s", hypo[:120])

        # Embed with the *document* prefix so the vector lives in the same
        # subspace as stored passages (critical for nomic-embed-text).
        try:
            vectors = _embed([settings.EMBED_DOC_PREFIX + hypo])
            return vectors[0]
        except EmbeddingError as exc:
            logger.warning("HyDE: embedding failed (%s) – falling back to query embedding", exc)
            return None


# module-level singleton
hyde = HyDEGenerator()

