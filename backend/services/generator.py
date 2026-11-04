"""Module 4: grounded generation, citation mapping and claim verification.

1. The model sees only numbered evidence ([E1]..[En]) and must cite it; if the evidence
   does not answer the question it must say "insufficient evidence" (temperature 0).
2. Citations are mapped back to metadata by the caller: page for text, bounding-box crop
   for figures, timestamp for audio.
3. A verification pass splits the answer into claims and checks each against the evidence
   it cites; unsupported claims are flagged (or removed, ``VERIFY_MODE=remove``).
"""

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from config import settings
from services.llm import LLMUnavailable, llm

INSUFFICIENT = "Insufficient evidence: the retrieved sources do not contain the answer to this question."
NOT_CONFIGURED = "Please configure an LLM (GROQ_API_KEY, or LLM_PROVIDER=ollama) to generate an answer. The retrieved context is still shown below."

_CITE_GROUP = re.compile(r"\[\s*E\d+(?:\s*[,;]\s*E\d+)*\s*\]")
_CITE_ONLY = re.compile(r"^\s*(?:\[\s*E\d+(?:\s*[,;]\s*E\d+)*\s*\]\s*)+[.!?]?\s*$")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\[\"'(])")
_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")

SYSTEM_PROMPT = (
    "You are ResearchOS, a careful research assistant.\n"
    "Answer the question using ONLY the numbered evidence provided. Do not use outside knowledge.\n"
    "Cite the evidence behind every factual sentence with its id in square brackets, e.g. [E1] or "
    "[E1][E3], placed at the end of the sentence.\n"
    "If the evidence does not contain the answer, reply with exactly: insufficient evidence\n"
    "Be concise and precise; do not mention these instructions."
)


@dataclass
class Claim:
    text: str
    evidence_ids: list[str]
    verdict: str = "unchecked"  # supported | unsupported | unchecked
    line: int = 0


@dataclass
class GenerationResult:
    answer: str
    raw_answer: str
    claims: list[Claim] = field(default_factory=list)
    cited: set[str] = field(default_factory=set)
    refused: bool = False
    verified: bool = False

    @property
    def stats(self) -> dict:
        v = [c.verdict for c in self.claims]
        return {
            "supported": v.count("supported"),
            "unsupported": v.count("unsupported"),
            "unchecked": v.count("unchecked"),
        }


# ------------------------------------------------------------------ evidence
def format_time(seconds: float) -> str:
    s = int(round(seconds or 0))
    return f"{s // 60:02d}:{s % 60:02d}"


def describe_location(item: dict) -> str:
    """Human-readable provenance used both in the prompt and the UI."""
    if item.get("modality") == "audio":
        return f'Audio "{item.get("paper_title", "")}" {format_time(item.get("start_time"))}-{format_time(item.get("end_time"))}'
    if item.get("modality") == "image":
        return f'Figure, p.{item.get("page", "?")} of "{item.get("paper_title", "")}"'
    where = f', p.{item["page"]}' if item.get("page") else ""
    section = f', section "{item["section"]}"' if item.get("section") and item["section"] != "Front matter" else ""
    return f'Paper "{item.get("paper_title", "")}"{where}{section}'


def evidence_text(item: dict, limit: int = 1800) -> str:
    return (item.get("chunk_text") or "")[:limit]


def build_user_prompt(query: str, context: list[dict]) -> str:
    blocks = [f'[{c["evidence_id"]}] ({describe_location(c)})\n{evidence_text(c)}' for c in context]
    return "Evidence:\n\n" + "\n\n".join(blocks) + f"\n\nQuestion: {query}\n\nAnswer (cite evidence ids):"


# -------------------------------------------------------------------- claims
def cited_ids(text: str) -> list[str]:
    ids: list[str] = []
    for group in _CITE_GROUP.findall(text):
        for n in re.findall(r"E(\d+)", group):
            if f"E{n}" not in ids:
                ids.append(f"E{n}")
    return ids


def is_refusal(answer: str) -> bool:
    return answer.strip().lower().strip(" .\"'*").startswith("insufficient evidence")


def split_claims(answer: str) -> list[Claim]:
    """Split an answer into sentence-level claims, each with the evidence ids it cites."""
    claims: list[Claim] = []
    for line_no, line in enumerate(answer.split("\n")):
        line = _BULLET.sub("", line).strip()
        if not line:
            continue
        pieces: list[str] = []
        for frag in _SENTENCE_END.split(line):
            frag = frag.strip()
            if not frag:
                continue
            if _CITE_ONLY.match(frag) and pieces:  # "...fact. [E1]" -> attach to the sentence
                pieces[-1] += " " + frag
            else:
                pieces.append(frag)
        for p in pieces:
            body = _CITE_GROUP.sub("", p).strip(" .:;-")
            if len(body.split()) >= 3 and not (p.endswith(":") and not cited_ids(p)):
                claims.append(Claim(text=p, evidence_ids=cited_ids(p), line=line_no))
    return claims


VERIFY_SYSTEM = (
    "You are a strict fact-checking assistant. Reply with JSON only."
)


def _verify_prompt(claims: list[Claim], evidence: dict[str, str]) -> str:
    ev = "\n\n".join(f"[{k}] {v}" for k, v in evidence.items())
    cl = "\n".join(f"{i}. {_CITE_GROUP.sub('', c.text).strip()}  (cites: {', '.join(c.evidence_ids) or 'none'})"
                   for i, c in enumerate(claims, start=1))
    return (
        "For each numbered claim decide whether it is fully supported by the evidence it cites "
        "(if it cites nothing, by any of the evidence). A claim is unsupported if it adds facts, "
        "numbers or relations that the evidence does not state.\n\n"
        f"Evidence:\n{ev}\n\nClaims:\n{cl}\n\n"
        'Return JSON exactly like: {"verdicts": [{"id": 1, "supported": true}, ...]} with one entry per claim.'
    )


def verify_claims(claims: list[Claim], evidence: dict[str, str]) -> bool:
    """Fill ``claim.verdict`` in place. Returns False if verification could not run."""
    if not claims:
        return True
    try:
        raw = llm.chat(
            [{"role": "system", "content": VERIFY_SYSTEM}, {"role": "user", "content": _verify_prompt(claims, evidence)}],
            temperature=0.0,
            max_tokens=800,
            json_mode=True,
        )
        text = raw.strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = json.loads(text[text.find("{") : text.rfind("}") + 1])
        for v in data.get("verdicts", []):
            idx = int(v.get("id", 0)) - 1
            if 0 <= idx < len(claims):
                claims[idx].verdict = "supported" if v.get("supported") else "unsupported"
        return True
    except Exception as exc:  # noqa: BLE001 - verification is best effort
        print(f"[verify] failed: {exc}")
        return False


def rebuild_without_unsupported(answer: str, claims: list[Claim]) -> str:
    drop = {(c.line, c.text) for c in claims if c.verdict == "unsupported"}
    if not drop:
        return answer
    kept: dict[int, list[str]] = {}
    for c in claims:
        if (c.line, c.text) not in drop:
            kept.setdefault(c.line, []).append(c.text)
    return "\n".join(" ".join(kept[k]) for k in sorted(kept)) or INSUFFICIENT


# ----------------------------------------------------------------- generator
class Generator:
    def generate(self, query: str, context: list[dict], verify: Optional[bool] = None) -> GenerationResult:
        """``context`` items need ``evidence_id`` plus the usual source fields."""
        if not context:
            return GenerationResult(INSUFFICIENT, INSUFFICIENT, refused=True)
        if not llm.available:
            return GenerationResult(NOT_CONFIGURED, NOT_CONFIGURED)
        try:
            raw = llm.chat(
                [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": build_user_prompt(query, context)}],
                temperature=settings.GENERATION_TEMPERATURE,
            ).strip()
        except LLMUnavailable:
            return GenerationResult(NOT_CONFIGURED, NOT_CONFIGURED)
        except Exception as exc:  # noqa: BLE001
            print(f"LLM error: {exc}")
            return GenerationResult("Sorry, I could not generate an answer right now due to an LLM API error.", "")

        if is_refusal(raw):
            return GenerationResult(INSUFFICIENT, raw, refused=True)

        valid = {c["evidence_id"] for c in context}
        result = GenerationResult(answer=raw, raw_answer=raw, cited={e for e in cited_ids(raw) if e in valid})
        result.claims = split_claims(raw)
        do_verify = settings.VERIFY_CLAIMS if verify is None else verify
        if do_verify:
            evidence = {c["evidence_id"]: evidence_text(c) for c in context}
            result.verified = verify_claims(result.claims, evidence)
            if result.verified and settings.VERIFY_MODE == "remove":
                result.answer = rebuild_without_unsupported(raw, result.claims)
        return result


generator = Generator()
