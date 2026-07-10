import logging

from services.embedder import get_text_embedding
from services.qdrant_client import db

logger = logging.getLogger(__name__)

# Calibrated empirically against bge-small-en-v1.5 across repeated extractions of the
# same two papers, since Groq's concept phrasing is non-deterministic run to run:
#   0.888  "Transformer" vs "Transformer Architecture"                    (same concept)
#   0.820  "Encoder-Decoder Architecture" vs "...Representations from
#          Transformers" (BERT's full name)                              (DISTINCT concept)
#   0.785  "Transformers" vs "Transformer model"                         (same concept)
#   0.759  "Machine Translation" vs "Natural Language Processing"         (distinct scope)
#   <=0.617 unrelated pairs (Fine-Tuning/Pre-Training, Transformer/BERT, ...)
#
# The 0.820 false-merge and the 0.785 true-merge overlap, so no single threshold
# classifies both correctly. Two tiers instead:
#   - score >= HIGH_SIMILARITY_THRESHOLD: merge on similarity alone.
#   - LOW_SIMILARITY_THRESHOLD <= score < HIGH: merge only if one name is a literal
#     substring of the other (case-insensitive) -- catches same-concept rephrasing
#     that shares a word ("Transformer" / "Transformer model") while still rejecting
#     the "Encoder-Decoder Architecture" case (not a substring of BERT's full name).
HIGH_SIMILARITY_THRESHOLD = 0.85
LOW_SIMILARITY_THRESHOLD = 0.70


def _is_substring_related(a: str, b: str) -> bool:
    a_lower, b_lower = a.lower(), b.lower()
    return a_lower in b_lower or b_lower in a_lower


def resolve_concepts(concept_names: list[str]) -> list[str]:
    """Map freshly extracted concept names onto existing canonical concept names
    when a semantically close match already exists in Qdrant, so that e.g.
    "Transformer" and "Transformer Architecture" resolve to the same graph node
    instead of creating near-duplicate Concept nodes with no edge between them.
    New concepts are registered in Qdrant so later papers can match against them.
    Falls back to the raw name on any embedding/lookup failure. Returns canonical
    names, deduplicated case-insensitively.
    """
    if not concept_names:
        return []

    canonical_names = []
    seen = set()
    for name in concept_names:
        canonical = name
        try:
            vector = get_text_embedding(name)
            top_match = db.find_top_concept_match(vector)
            if top_match:
                match_name, score = top_match
                if score >= HIGH_SIMILARITY_THRESHOLD:
                    canonical = match_name
                elif score >= LOW_SIMILARITY_THRESHOLD and _is_substring_related(name, match_name):
                    canonical = match_name
                else:
                    db.upsert_concept(name, vector)
            else:
                db.upsert_concept(name, vector)
        except Exception as e:
            logger.error("Concept resolution failed for %r, using raw name: %s", name, e)

        key = canonical.lower()
        if key not in seen:
            seen.add(key)
            canonical_names.append(canonical)

    return canonical_names
