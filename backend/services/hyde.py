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
import time
from dataclasses import dataclass, field
from typing import Optional

import requests

from config import settings
from services.embedder import EmbeddingError, _embed

logger = logging.getLogger(__name__)


@dataclass
class HyDEResult:
    """Full live trace of a HyDE pre-retrieval pass (used for UI observability)."""

    enabled: bool
    used: bool = False
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.7
    hypothetical_doc: Optional[str] = None
    embed_model: str = ""
    vector: Optional[list[float]] = None
    vector_dim: int = 0
    vector_preview: list[float] = field(default_factory=list)
    latency_ms: int = 0
    fallback_reason: Optional[str] = None

    def trace_dict(self, raw_query: str) -> dict:
        return {
            "enabled": self.enabled,
            "used": self.used,
            "provider": self.provider,
            "model": self.model,
            "temperature": self.temperature,
            "bm25_query": raw_query,
            "hypothetical_doc": self.hypothetical_doc,
            "embed_model": self.embed_model,
            "vector_dim": self.vector_dim,
            "vector_preview": self.vector_preview,
            "latency_ms": self.latency_ms,
            "fallback_reason": self.fallback_reason,
        }

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

    def _hallucinate(self, query: str) -> tuple[str, Optional[str], Optional[str]]:
        """Return ``(hypothetical_text, provider, model)``; prefer local Ollama, fall back to Groq."""
        try:
            text = self._call_ollama(query)
            if text:
                return text, "ollama", settings.OLLAMA_LLM_MODEL
        except Exception as exc:  # noqa: BLE001
            logger.warning("HyDE: Ollama call failed (%s), trying Groq fallback", exc)

        # Groq fallback (only if key is configured)
        if settings.GROQ_API_KEY and settings.GROQ_API_KEY != "your_groq_api_key_here":
            try:
                text = self._call_groq(query)
                if text:
                    return text, "groq", settings.GROQ_MODEL
            except Exception as exc:  # noqa: BLE001
                logger.warning("HyDE: Groq fallback also failed (%s)", exc)

        return "", None, None

    def generate_with_trace(self, query: str, *, enabled: Optional[bool] = None) -> HyDEResult:
        """Generate a HyDE dense vector and return full live telemetry for UI inspection."""
        is_enabled = settings.HYDE_ENABLED if enabled is None else enabled
        res = HyDEResult(
            enabled=is_enabled,
            temperature=settings.HYDE_TEMPERATURE,
            embed_model=settings.EMBED_MODEL,
        )
        if not is_enabled:
            res.fallback_reason = "disabled by request or config"
            return res

        t0 = time.time()
        hypo, provider, model = self._hallucinate(query)
        if not hypo:
            res.latency_ms = round((time.time() - t0) * 1000)
            res.fallback_reason = "empty LLM hallucination"
            logger.warning("HyDE: empty hallucination for query %r – falling back to query embedding", query[:80])
            return res

        res.provider = provider
        res.model = model
        res.hypothetical_doc = hypo
        logger.debug("HyDE hallucination (first 120 chars): %s", hypo[:120])

        # Embed with the *document* prefix so the vector lives in the same
        # subspace as stored passages (critical for nomic-embed-text).
        try:
            vectors = _embed([settings.EMBED_DOC_PREFIX + hypo])
            vec = vectors[0]
            res.used = True
            res.vector = vec
            res.vector_dim = len(vec)
            res.vector_preview = [round(float(v), 4) for v in vec[:5]]
            res.latency_ms = round((time.time() - t0) * 1000)
            return res
        except EmbeddingError as exc:
            res.latency_ms = round((time.time() - t0) * 1000)
            res.fallback_reason = f"embedding failed: {exc}"
            logger.warning("HyDE: embedding failed (%s) – falling back to query embedding", exc)
            return res

    def generate(self, query: str) -> Optional[list[float]]:
        """Return a dense vector from the hallucinated answer, or ``None`` on failure.

        Returns ``None`` (instead of raising) so the pipeline can degrade gracefully
        to a plain query embedding for the dense leg.
        """
        return self.generate_with_trace(query).vector


# module-level singleton
hyde = HyDEGenerator()

