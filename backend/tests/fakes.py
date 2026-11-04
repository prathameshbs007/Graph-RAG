"""Deterministic stand-ins for the external services (Ollama, Groq, Cohere) so the whole
pipeline can be exercised against real Weaviate + Neo4j without API keys."""

import json
import math
import re
import zlib

DIM = 256
STOP = set("the a an of and or to in is are for with that this on as by be it from at we can so".split())


def tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP]


def fake_vector(text: str) -> list[float]:
    """Hashed bag-of-words: similar wording -> similar vectors."""
    v = [0.0] * DIM
    for t in tokens(text):
        v[zlib.crc32(t.encode()) % DIM] += 1.0
    norm = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norm for x in v]


def fake_embed(inputs: list[str]) -> list[list[float]]:
    return [fake_vector(t.split(": ", 1)[-1]) for t in inputs]


def fake_rerank_score(query: str, documents: list[str]) -> list[float]:
    """Share of the query's words that the document contains (0..1)."""
    q = set(tokens(query))
    out = []
    for d in documents:
        dt = set(tokens(d))
        out.append(len(q & dt) / len(q) if q else 0.0)
    return out


def _concepts_for(text: str) -> list[str]:
    freq: dict[str, int] = {}
    for t in tokens(text):
        if len(t) >= 7:
            freq[t] = freq.get(t, 0) + 1
    return [w for w, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[:3]]


class FakeLLM:
    """Stands in for ``llm.chat``; behaviour is chosen from the system prompt."""

    def __init__(self):
        self.calls: list[str] = []

    def __call__(self, messages, **kwargs):
        system, user = messages[0]["content"], messages[-1]["content"]
        if system.startswith("You extract a knowledge graph"):
            self.calls.append("concepts")
            chunks = re.split(r"### Chunk (\d+)\n", user)
            entries, relations = [], []
            for i in range(1, len(chunks) - 1, 2):
                cs = _concepts_for(chunks[i + 1])
                entries.append({"id": int(chunks[i]), "concepts": cs})
                if len(cs) >= 2 and not relations:
                    relations.append({"source": cs[0], "target": cs[1], "relation": "related to"})
            return json.dumps({"chunks": entries, "relations": relations})
        if system.startswith("You are a strict fact-checking"):
            self.calls.append("verify")
            verdicts = []
            for m in re.finditer(r"(?m)^(\d+)\. (.*)$", user.split("Claims:")[1]):
                verdicts.append({"id": int(m.group(1)), "supported": "FABRICATED" not in m.group(2)})
            return json.dumps({"verdicts": verdicts})
        self.calls.append("generate")
        first = re.search(r"\[E1\] \(.*?\)\n(.*)", user)
        sentence = (first.group(1).split(". ")[0] if first else "nothing").strip().rstrip(".")
        if "FABRICATE" in user.split("Question:")[-1]:
            return f"{sentence} [E1]. The moon is made of cheese FABRICATED. [E1]"
        return f"{sentence} [E1]."
