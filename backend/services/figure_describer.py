"""Short text descriptions of figures from a vision-language model (Module 1, step 2).

Descriptions make figures searchable by the same BM25 + dense retrieval as text. The VLM
is optional: with ``VLM_PROVIDER`` unset, figures are indexed by their caption and the
text found inside the figure instead, which already works well for plots and diagrams.
"""

import base64

import requests

from config import settings
from services.llm import with_retries

PROMPT = (
    "This is a figure from a research paper. In 2-3 sentences describe what it shows: the kind of "
    "figure (plot, diagram, table, screenshot), what is on the axes or in the boxes, and the main "
    "trend or message. Do not guess beyond what is visible.\nCaption: {caption}"
)


def enabled() -> bool:
    return bool(settings.VLM_PROVIDER and settings.VLM_MODEL)


def _read_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def _ollama(image_b64: str, prompt: str) -> str:
    r = requests.post(
        f"{settings.OLLAMA_URL}/api/chat",
        json={
            "model": settings.VLM_MODEL,
            "stream": False,
            "options": {"temperature": 0.0, "num_predict": 200},
            "messages": [{"role": "user", "content": prompt, "images": [image_b64]}],
        },
        timeout=600,
    )
    r.raise_for_status()
    return r.json().get("message", {}).get("content", "")


def _groq(image_b64: str, prompt: str) -> str:
    from groq import Groq

    client = Groq(api_key=settings.GROQ_API_KEY)
    res = client.chat.completions.create(
        model=settings.VLM_MODEL,
        temperature=0.0,
        max_tokens=200,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                ],
            }
        ],
    )
    return res.choices[0].message.content or ""


def describe_figure(image_path: str, caption: str) -> str:
    """Description text, or "" if the VLM is disabled or fails (never raises)."""
    if not enabled():
        return ""
    try:
        image_b64 = _read_b64(image_path)
        prompt = PROMPT.format(caption=caption[:300])
        fn = _groq if settings.VLM_PROVIDER.lower() == "groq" else _ollama
        return with_retries(lambda: fn(image_b64, prompt), retries=2).strip()
    except Exception as exc:  # noqa: BLE001
        print(f"[figures] description failed for {image_path}: {exc}")
        return ""
