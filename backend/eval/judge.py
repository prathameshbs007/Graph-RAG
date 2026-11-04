"""The judge model (Section 4.1).

A hosted LLM that is stronger than, and different from, the Llama-3.1-8B generator, so the
generator never grades itself. It is configured by environment variables, pinned by name
and date in the run manifest, runs at temperature 0, is identical for every system, and is
never the Cohere reranker (which supplies the feedback signal) so the two signals stay
independent. Only questions, answers and passages are sent to it, only during evaluation.

    JUDGE_PROVIDER   "openai" (any OpenAI-compatible API) or "anthropic"
    JUDGE_MODEL      model id, e.g. "gpt-4.1" or "claude-opus-5-5"
    JUDGE_API_KEY    key for that provider
    JUDGE_BASE_URL   optional, for OpenAI-compatible servers
    JUDGE_MODEL_DATE a date or snapshot label you want recorded with the results
"""

import os
from dataclasses import dataclass
from typing import Optional

import requests
from pydantic import BaseModel

from config import settings


@dataclass
class JudgeConfig:
    provider: str
    model: str
    api_key: str
    base_url: Optional[str] = None
    model_date: str = ""

    @classmethod
    def from_env(cls) -> "JudgeConfig":
        model = os.environ.get("JUDGE_MODEL", "")
        key = os.environ.get("JUDGE_API_KEY", "")
        if not model or not key:
            raise RuntimeError(
                "Set JUDGE_MODEL and JUDGE_API_KEY (and JUDGE_PROVIDER=openai|anthropic) to run the "
                "Ragas judge. It must be a stronger model than the generator."
            )
        cfg = cls(
            provider=os.environ.get("JUDGE_PROVIDER", "openai").lower(),
            model=model,
            api_key=key,
            base_url=os.environ.get("JUDGE_BASE_URL") or None,
            model_date=os.environ.get("JUDGE_MODEL_DATE", ""),
        )
        cfg.check_independent()
        return cfg

    def check_independent(self):
        generator = settings.OLLAMA_LLM_MODEL if settings.LLM_PROVIDER.lower() == "ollama" else settings.GROQ_MODEL
        if self.model.lower() == generator.lower():
            raise RuntimeError("The judge must differ from the generator model; the generator would grade itself.")
        if "cohere" in self.model.lower() or "rerank" in self.model.lower():
            raise RuntimeError("The judge must not be the Cohere reranker that drives the feedback loop.")

    def manifest(self) -> dict:
        return {"provider": self.provider, "model": self.model, "date": self.model_date, "temperature": 0.0}


# ---------------------------------------------------------- Ragas LLM / embeddings
def build_ragas_llm(cfg: JudgeConfig):
    """Instructor-based Ragas LLM used by the ``ragas.metrics.collections`` metrics."""
    from ragas.llms import llm_factory

    if cfg.provider == "anthropic":
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=cfg.api_key)
        return llm_factory(cfg.model, provider="anthropic", client=client, temperature=0.0, max_tokens=4096)
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=cfg.api_key, base_url=cfg.base_url)
    return llm_factory(cfg.model, provider="openai", client=client, temperature=0.0)


def build_langchain_chat(cfg: JudgeConfig):
    """LangChain chat model, used by Ragas' test-set generator."""
    if cfg.provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=cfg.model, api_key=cfg.api_key, temperature=0.0, max_tokens=4096)
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=cfg.model, api_key=cfg.api_key, base_url=cfg.base_url, temperature=0.0)


def _ollama_embed(texts: list[str]) -> list[list[float]]:
    r = requests.post(
        f"{settings.OLLAMA_URL}/api/embed", json={"model": settings.EMBED_MODEL, "input": texts}, timeout=120
    )
    r.raise_for_status()
    return r.json()["embeddings"]


def build_ragas_embeddings():
    """Answer Relevancy needs embeddings; reuse the local Ollama model (no extra API key)."""
    from ragas.embeddings import BaseRagasEmbedding

    class OllamaEmbedding(BaseRagasEmbedding):
        def embed_text(self, text: str, **kwargs) -> list[float]:
            return _ollama_embed([text])[0]

        async def aembed_text(self, text: str, **kwargs) -> list[float]:
            import asyncio

            return await asyncio.to_thread(self.embed_text, text)

    return OllamaEmbedding()


def build_langchain_embeddings():
    from langchain_community.embeddings import OllamaEmbeddings

    return OllamaEmbeddings(base_url=settings.OLLAMA_URL, model=settings.EMBED_MODEL)


# ------------------------------------------------------ passage relevance judge
class Relevance(BaseModel):
    relevant: bool
    reason: str = ""


RELEVANCE_PROMPT = (
    "You judge retrieval quality. Decide whether the passage contains information that helps answer "
    "the question (given the reference answer). Answer relevant=false if it is off-topic or only "
    "superficially similar.\n\nQuestion: {question}\n\nReference answer: {reference}\n\nPassage:\n{passage}"
)


async def judge_relevance(llm, question: str, reference: str, passage: str) -> bool:
    out = await llm.agenerate(
        RELEVANCE_PROMPT.format(question=question, reference=reference, passage=passage[:2500]), Relevance
    )
    return bool(out.relevant)
