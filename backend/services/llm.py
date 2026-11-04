"""Thin chat-completion wrapper used for generation, concept extraction and claim
verification. Supports hosted Llama-3 on Groq and local Llama-3.1-8B on Ollama
(``LLM_PROVIDER``), always at temperature 0 unless told otherwise."""

import random
import time
from typing import Optional

import requests

from config import settings


class LLMUnavailable(RuntimeError):
    """No usable LLM is configured (e.g. missing API key)."""


def _is_retryable(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    if status is None:
        resp = getattr(exc, "response", None)
        status = getattr(resp, "status_code", None)
    if status is not None:
        return status == 429 or status >= 500
    return isinstance(exc, (requests.ConnectionError, requests.Timeout, TimeoutError, ConnectionError))


def with_retries(fn, retries: int = 4, base_delay: float = 2.0):
    """Call ``fn`` retrying rate-limit / transient errors with exponential backoff."""
    for attempt in range(retries + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - provider SDKs raise many types
            if attempt == retries or not _is_retryable(exc):
                raise
            time.sleep(min(30.0, base_delay * (2**attempt)) + random.random())


class LLMClient:
    def __init__(self):
        self._groq = None

    # ------------------------------------------------------------ availability
    @property
    def provider(self) -> str:
        return settings.LLM_PROVIDER.lower()

    @property
    def available(self) -> bool:
        if self.provider == "ollama":
            return True
        key = settings.GROQ_API_KEY
        return bool(key) and key != "your_groq_api_key_here"

    # -------------------------------------------------------------------- chat
    def chat(
        self,
        messages: list[dict],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> str:
        if not self.available:
            raise LLMUnavailable("No LLM configured: set GROQ_API_KEY or LLM_PROVIDER=ollama")
        temperature = settings.GENERATION_TEMPERATURE if temperature is None else temperature
        max_tokens = max_tokens or settings.GROQ_MAX_TOKENS
        if self.provider == "ollama":
            return with_retries(lambda: self._chat_ollama(messages, temperature, max_tokens, json_mode))
        return with_retries(lambda: self._chat_groq(messages, temperature, max_tokens, json_mode))

    def _chat_groq(self, messages, temperature, max_tokens, json_mode) -> str:
        if self._groq is None:
            from groq import Groq

            self._groq = Groq(api_key=settings.GROQ_API_KEY)
        kwargs = {}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        res = self._groq.chat.completions.create(
            messages=messages,
            model=settings.GROQ_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        return res.choices[0].message.content or ""

    def _chat_ollama(self, messages, temperature, max_tokens, json_mode) -> str:
        payload = {
            "model": settings.OLLAMA_LLM_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if json_mode:
            payload["format"] = "json"
        r = requests.post(f"{settings.OLLAMA_URL}/api/chat", json=payload, timeout=600)
        r.raise_for_status()
        return r.json().get("message", {}).get("content", "")


llm = LLMClient()
