"""Citation edges from reference lists (Module 1).

Papers in the knowledge base are linked with ``CITES`` when one paper's reference
section contains the other's title.

Matching deliberately does not depend on parsing individual reference entries, which
varies wildly between publishers (``[1]``, ``1.``, ``Surname, X. (2020)``,
``Firstname Lastname. 2020.``) and is often mangled by column and page breaks. Instead
the title and the whole reference section are reduced to lowercase letters and digits
only, so case, punctuation, line wraps and hyphenation across lines cannot matter.
"""

import re
import unicodedata


def normalize(text: str) -> str:
    """Lowercase words separated by single spaces."""
    text = unicodedata.normalize("NFKC", text or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def compact(text: str) -> str:
    """Lowercase letters and digits only (no spaces) for line-wrap-proof containment tests."""
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKC", text or "").lower())


def _counts_up_from_one(nums: list[int]) -> bool:
    """True for a genuine 1, 2, 3, ... sequence (page ranges like "170." must not qualify)."""
    seen = 0
    for n in nums:
        if n == seen + 1:
            seen += 1
    return seen >= 3


def split_references(blocks: list[str]) -> list[str]:
    """Best-effort split of the reference section into entries (used for counting/display).

    Citation *linking* does not use this; see module docstring.
    """
    joined = "\n".join(b.strip() for b in blocks if b.strip())
    if not joined:
        return []
    start = joined.lstrip()
    # A numbered list must actually start at 1; list items later in an appendix do not count.
    if start.startswith("[1]") and _counts_up_from_one([int(n) for n in re.findall(r"\[(\d{1,3})\]", joined)]):
        parts = re.split(r"(?=\[\d+\])", joined)
    elif re.match(r"1\.\s+\S", start) and _counts_up_from_one(
        [int(n) for n in re.findall(r"(?m)^\s*(\d{1,3})\.\s+[A-Z]", joined)]
    ):
        parts = re.split(r"(?m)^\s*(?=\d{1,3}\.\s+[A-Z])", joined)
    else:
        parts = _split_author_year(" ".join(b.strip() for b in blocks))
        if len(parts) < 2:
            parts = list(blocks)
    return [p for p in (re.sub(r"\s+", " ", x).strip() for x in parts) if len(p) >= 25]


_AUTHOR_START = re.compile(r"(?<=[.)\d])\s+(?=[A-Z][\w'’\-]+,\s+[A-Z]\.)")
_YEAR = re.compile(r"\(?\b(19|20)\d{2}[a-z]?\b\)?")


def _split_author_year(text: str) -> list[str]:
    """Split "Surname, X. (2001). Title... Surname, Y. (2002). ..." into entries.

    A new entry can only start after the current one has shown its year, which keeps
    "Smith, A., & Jones, B. (2001)" together. Styles this does not recognise come back
    unsplit, which is harmless for title matching.
    """
    parts, start = [], 0
    for m in _AUTHOR_START.finditer(text):
        if _YEAR.search(text[start : m.start()]):
            parts.append(text[start : m.start()])
            start = m.end()
    parts.append(text[start:])
    return parts


def is_linkable_title(title: str) -> bool:
    """Short or generic titles ("Introduction", "Related Work") would match everything."""
    return len(normalize(title).split()) >= 3 and len(compact(title)) >= 20


def cites(title: str, refs_compact: str) -> bool:
    """True if a paper with this title appears in a reference section (given in compact form)."""
    return bool(refs_compact) and is_linkable_title(title) and compact(title) in refs_compact
