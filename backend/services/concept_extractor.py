import json
import logging

from groq import Groq

from config import settings

logger = logging.getLogger(__name__)

_client = None

SYSTEM_PROMPT = (
    "You extract structured metadata from academic paper text. "
    "Given the opening pages of a paper, return a JSON object with exactly two keys: "
    '"concepts" (a list of 5-10 short key technical concepts/topics the paper discusses) and '
    '"cited_titles" (a list of paper titles referenced or cited in the given text, if any are recognizable). '
    "If nothing is found for a key, return an empty list for it. Respond with JSON only."
)


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.GROQ_API_KEY)
    return _client


def extract_concepts(lead_text: str) -> dict:
    """Extract concepts and cited paper titles from a paper's opening text via one Groq JSON-mode call.

    Returns {"concepts": [...], "cited_titles": [...]}. Fails gracefully to empty lists.
    """
    if not lead_text.strip():
        return {"concepts": [], "cited_titles": []}

    try:
        client = _get_client()
        completion = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": lead_text[:8000]},
            ],
            max_tokens=1024,
        )
        data = json.loads(completion.choices[0].message.content)
        concepts = data.get("concepts", [])
        cited_titles = data.get("cited_titles", [])
        if not isinstance(concepts, list):
            concepts = []
        if not isinstance(cited_titles, list):
            cited_titles = []
        return {
            "concepts": [str(c).strip() for c in concepts if str(c).strip()],
            "cited_titles": [str(t).strip() for t in cited_titles if str(t).strip()],
        }
    except Exception as e:
        logger.error("Concept extraction failed: %s", e)
        return {"concepts": [], "cited_titles": []}
