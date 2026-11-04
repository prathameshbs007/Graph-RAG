"""Test-set splitting (Section 4.1): feedback 40% / development 20% / held-out test 40%,
split by question type so every split has the same single-hop / multi-hop mix, plus the
20% human-review sample. Pure functions, deterministic given the seed."""

import random
from collections import defaultdict

SPLIT_NAMES = ("feedback", "development", "test")
SPLIT_FRACTIONS = (0.4, 0.2, 0.4)


def query_type(synthesizer_name: str) -> str:
    """Ragas names its synthesizers e.g. ``single_hop_specific_query_synthesizer``."""
    return "multi_hop" if "multi_hop" in (synthesizer_name or "") else "single_hop"


def _allocate(n: int, fractions) -> list[int]:
    """Split ``n`` items by ``fractions`` with largest-remainder rounding (sums to ``n``)."""
    raw = [n * f for f in fractions]
    counts = [int(x) for x in raw]
    order = sorted(range(len(raw)), key=lambda i: raw[i] - counts[i], reverse=True)
    for i in order[: n - sum(counts)]:
        counts[i] += 1
    return counts


def stratified_split(rows: list[dict], seed: int = 13, key: str = "query_type") -> dict[str, list[dict]]:
    """Split ``rows`` into the three named splits, stratified by ``row[key]``."""
    rng = random.Random(seed)
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r.get(key, "")].append(r)
    out: dict[str, list[dict]] = {name: [] for name in SPLIT_NAMES}
    for g in sorted(groups):
        items = sorted(groups[g], key=lambda r: r["id"])  # stable before shuffling
        rng.shuffle(items)
        start = 0
        for name, n in zip(SPLIT_NAMES, _allocate(len(items), SPLIT_FRACTIONS)):
            out[name].extend(items[start : start + n])
            start += n
    for name in out:
        out[name].sort(key=lambda r: r["id"])
    return out


def review_sample(rows: list[dict], fraction: float = 0.2, seed: int = 13) -> list[dict]:
    """The questions a human should check for clarity, answerability and a correct reference."""
    rng = random.Random(seed + 1)
    k = max(1, round(len(rows) * fraction)) if rows else 0
    return sorted(rng.sample(rows, k), key=lambda r: r["id"])
