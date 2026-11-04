"""Concept and relation extraction with Llama-3 (Module 1, step 5).

For each batch of chunks the model returns JSON with the concepts mentioned in each
chunk and the relations between concepts. Concepts are normalised so duplicates merge
(``Self-Attention`` / ``self attention`` / ``self-attentions`` -> one node).
"""

import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from config import settings
from services.llm import LLMUnavailable, llm

# Words that name nothing specific and would turn into hub nodes linking everything.
GENERIC = {
    "paper", "papers", "method", "methods", "approach", "approaches", "model", "models",
    "result", "results", "figure", "table", "data", "performance", "task", "tasks", "work",
    "system", "systems", "example", "examples", "introduction", "conclusion", "section",
    "experiment", "experiments", "analysis", "problem", "problems", "technique", "techniques",
    "framework", "algorithm", "setting", "case", "number", "way", "time", "use", "set",
}

_PLURAL_KEEP = ("ss", "us", "is", "as", "os")


def _singular(word: str) -> str:
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 4 and word.endswith("s") and not word.endswith(_PLURAL_KEEP):
        return word[:-1]
    return word


def normalize_concept(name: str) -> str | None:
    """Canonical concept id, or ``None`` if the string is not a usable concept."""
    s = unicodedata.normalize("NFKC", str(name)).lower().strip()
    s = re.sub(r"[^a-z0-9+#.\s-]", " ", s)
    s = re.sub(r"[-_\s]+", " ", s).strip(" .")
    if not s:
        return None
    words = s.split(" ")
    words[-1] = _singular(words[-1])
    s = " ".join(words)
    if len(s) < 3 or len(s) > 60 or s.isdigit() or s in GENERIC:
        return None
    return s


@dataclass
class ConceptGraph:
    # (item_id, concept_id, display_name)
    mentions: list[tuple[str, str, str]] = field(default_factory=list)
    # (concept_id_a, concept_id_b, relation_label)
    relations: list[tuple[str, str, str]] = field(default_factory=list)
    failed_batches: int = 0

    def merge(self, other: "ConceptGraph") -> None:
        self.mentions.extend(other.mentions)
        self.relations.extend(other.relations)
        self.failed_batches += other.failed_batches


SYSTEM_PROMPT = (
    "You extract a knowledge graph from research text. Reply with JSON only."
)


def build_prompt(batch: list[dict]) -> str:
    parts = []
    for i, item in enumerate(batch, start=1):
        text = item["text"][:2500]
        parts.append(f"### Chunk {i}\n{text}")
    chunks = "\n\n".join(parts)
    return (
        "For each chunk below list the specific technical concepts it discusses "
        "(methods, models, datasets, metrics, tasks, named techniques). Use short noun "
        f"phrases, at most {settings.CONCEPT_MAX_PER_CHUNK} per chunk, no generic words like "
        "'method' or 'results'. Then list important relations between concepts that the "
        "text states explicitly.\n\n"
        'Return JSON exactly like: {"chunks": [{"id": 1, "concepts": ["..."]}], '
        '"relations": [{"source": "...", "target": "...", "relation": "..."}]}\n'
        "Relation endpoints must be concepts you listed. Use the chunk numbers given.\n\n"
        f"{chunks}"
    )


def _loads(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def parse_response(raw: str, batch: list[dict]) -> ConceptGraph:
    """Validate the model output against the batch (ignore anything not grounded in it)."""
    data = _loads(raw)
    out = ConceptGraph()
    seen_in_batch: dict[str, str] = {}  # concept id -> display name
    for entry in data.get("chunks", []) or []:
        try:
            idx = int(entry.get("id")) - 1
        except (TypeError, ValueError):
            continue
        if not 0 <= idx < len(batch):
            continue
        item_id = batch[idx]["id"]
        taken: set[str] = set()
        for name in (entry.get("concepts") or [])[: settings.CONCEPT_MAX_PER_CHUNK]:
            cid = normalize_concept(name)
            if cid and cid not in taken:
                taken.add(cid)
                seen_in_batch.setdefault(cid, str(name).strip())
                out.mentions.append((item_id, cid, seen_in_batch[cid]))
    for rel in data.get("relations", []) or []:
        a = normalize_concept(rel.get("source", ""))
        b = normalize_concept(rel.get("target", ""))
        if a and b and a != b and a in seen_in_batch and b in seen_in_batch:
            out.relations.append((a, b, str(rel.get("relation", "related to"))[:60]))
    return out


def _extract_batch(batch: list[dict]) -> ConceptGraph:
    try:
        raw = llm.chat(
            [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": build_prompt(batch)}],
            temperature=0.0,
            max_tokens=1500,
            json_mode=True,
        )
        return parse_response(raw, batch)
    except LLMUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001 - one bad batch must not fail the ingest
        print(f"[concepts] batch failed: {exc}")
        return ConceptGraph(failed_batches=1)


def extract_concepts(items: list[dict]) -> ConceptGraph:
    """``items`` are ``{"id": ..., "text": ...}``. Returns merged mentions/relations."""
    result = ConceptGraph()
    if not items or not settings.CONCEPT_EXTRACTION:
        return result
    size = max(1, settings.CONCEPT_BATCH_SIZE)
    batches = [items[i : i + size] for i in range(0, len(items), size)]
    with ThreadPoolExecutor(max_workers=max(1, settings.CONCEPT_WORKERS)) as pool:
        for part in pool.map(_extract_batch, batches):
            result.merge(part)
    return result
