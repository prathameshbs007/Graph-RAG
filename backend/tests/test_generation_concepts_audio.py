import json

import pytest

from services.audio_transcriber import merge_segments
from services.concept_extractor import ConceptGraph, normalize_concept, parse_response
from services.generator import (
    Claim,
    cited_ids,
    describe_location,
    is_refusal,
    rebuild_without_unsupported,
    split_claims,
)


# ------------------------------------------------------------------- claims
def test_cited_ids_handles_groups_and_duplicates():
    assert cited_ids("Fact [E1][E3]. More [E2, E3].") == ["E1", "E3", "E2"]
    assert cited_ids("no citations here") == []
    assert cited_ids("array[1] is not a citation [E] either") == []


def test_split_claims_sentences_bullets_and_trailing_citations():
    answer = (
        "Dense retrieval embeds passages [E1]. It is trained contrastively. [E2]\n"
        "- BM25 matches exact terms [E1][E3]\n"
        "- Rerankers read query and passage together [E2]\n"
        "Summary:"
    )
    claims = split_claims(answer)
    assert [c.evidence_ids for c in claims] == [["E1"], ["E2"], ["E1", "E3"], ["E2"]]
    assert claims[1].text.endswith("[E2]")  # the citation after the full stop stays with its sentence
    assert all(len(c.text.split()) >= 3 for c in claims)
    assert [c.line for c in claims] == [0, 0, 1, 2]


def test_refusal_detection():
    assert is_refusal("insufficient evidence")
    assert is_refusal("Insufficient evidence.")
    assert is_refusal("**Insufficient evidence** to say")
    assert not is_refusal("There is insufficient evidence for X but Y [E1].")


def test_removing_unsupported_claims_rebuilds_by_line():
    answer = "Good fact one [E1]. Bad fact two [E1].\nGood fact three [E2]."
    claims = split_claims(answer)
    claims[1].verdict = "unsupported"
    claims[0].verdict = claims[2].verdict = "supported"
    assert rebuild_without_unsupported(answer, claims) == "Good fact one [E1].\nGood fact three [E2]."
    all_bad = [Claim("x y z", [], "unsupported", 0)]
    assert "Insufficient evidence" in rebuild_without_unsupported("x y z", all_bad)


def test_location_strings_for_each_modality():
    assert "p.3" in describe_location({"modality": "text", "paper_title": "T", "page": 3, "section": "2 Method"})
    assert "Figure" in describe_location({"modality": "image", "paper_title": "T", "page": 5})
    assert "02:05-03:00" in describe_location({"modality": "audio", "paper_title": "Talk", "start_time": 125, "end_time": 180})


# ----------------------------------------------------------------- concepts
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Self-Attention", "self attention"),
        ("self attention", "self attention"),
        ("Self-Attentions", "self attention"),
        ("Transformers", "transformer"),
        ("Libraries", "library"),
        ("bias", "bias"),
        ("BM25", "bm25"),
        ("C++", "c++"),
        ("model", None),  # generic
        ("Results", None),  # generic
        ("42", None),
        ("a", None),
        ("", None),
        ("x" * 80, None),
    ],
)
def test_concept_normalisation_merges_variants_and_drops_junk(raw, expected):
    assert normalize_concept(raw) == expected


def test_parse_response_validates_against_the_batch():
    batch = [{"id": "c1", "text": "..."}, {"id": "c2", "text": "..."}]
    raw = json.dumps(
        {
            "chunks": [
                {"id": 1, "concepts": ["Self-Attention", "transformer", "results", "Self attention"]},
                {"id": 2, "concepts": ["BM25"]},
                {"id": 9, "concepts": ["hallucinated chunk"]},
            ],
            "relations": [
                {"source": "transformer", "target": "self attention", "relation": "uses"},
                {"source": "transformer", "target": "never listed", "relation": "x"},
                {"source": "bm25", "target": "bm25", "relation": "self"},
            ],
        }
    )
    g = parse_response(raw, batch)
    assert sorted((i, c) for i, c, _ in g.mentions) == [("c1", "self attention"), ("c1", "transformer"), ("c2", "bm25")]
    assert g.relations == [("transformer", "self attention", "uses")]


def test_parse_response_tolerates_prose_around_json_and_rejects_garbage():
    batch = [{"id": "c1", "text": "..."}]
    g = parse_response('Sure! Here is the JSON: {"chunks": [{"id": 1, "concepts": ["bm25 ranking"]}]} Hope it helps', batch)
    assert g.mentions == [("c1", "bm25 ranking", "bm25 ranking")]
    with pytest.raises(Exception):
        parse_response("no json at all", batch)
    assert isinstance(ConceptGraph(), ConceptGraph)


# -------------------------------------------------------------------- audio
def test_audio_segments_merge_into_time_windows():
    segs = [{"chunk_text": f"sentence {i}.", "start_time": i * 10.0, "end_time": i * 10.0 + 9.0} for i in range(7)]
    windows = merge_segments(segs, window_sec=30.0)
    assert [(w["start_time"], w["end_time"]) for w in windows] == [(0.0, 29.0), (30.0, 59.0), (60.0, 69.0)]
    assert windows[0]["chunk_text"] == "sentence 0. sentence 1. sentence 2."
    assert merge_segments([{"chunk_text": "  ", "start_time": 0, "end_time": 1}], 30) == []
