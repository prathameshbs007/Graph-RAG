"""Weaviate schema: one ``Chunk`` collection holding every modality.

Text chunks, figure descriptions and audio transcript segments all live in the same
collection and the same (text) embedding space, so a single BM25 query and a single
dense query cover the whole knowledge base (Module 2). ``chunk_text`` is BM25-indexed.
"""

CHUNK_CLASS = "Chunk"


def _text(name, tokenization="word", searchable=True):
    prop = {"name": name, "dataType": ["text"], "tokenization": tokenization}
    if not searchable:
        prop["indexSearchable"] = False
    return prop


CHUNK_SCHEMA = {
    "class": CHUNK_CLASS,
    "description": "Text chunk, figure description or audio transcript segment",
    "vectorizer": "none",
    "vectorIndexConfig": {"distance": "cosine"},
    "properties": [
        _text("chunk_id", "field", searchable=False),
        _text("modality", "field", searchable=False),  # text | image | audio
        _text("chunk_text"),  # the BM25-indexed field
        _text("paper_id", "field", searchable=False),
        _text("paper_title"),
        {"name": "authors", "dataType": ["text[]"]},
        {"name": "year", "dataType": ["int"]},
        {"name": "page", "dataType": ["int"]},
        {"name": "chunk_index", "dataType": ["int"]},
        _text("section"),
        # figures
        _text("figure_id", "field", searchable=False),
        _text("caption"),
        _text("description"),
        _text("file_path", "field", searchable=False),
        {"name": "bbox", "dataType": ["number[]"]},
        # audio
        _text("audio_id", "field", searchable=False),
        {"name": "start_time", "dataType": ["number"]},
        {"name": "end_time", "dataType": ["number"]},
        _text("source_paper_id", "field", searchable=False),
    ],
}

PROPERTY_NAMES = [p["name"] for p in CHUNK_SCHEMA["properties"]]


def ensure_weaviate_schema(client) -> None:
    """Create the collection, or add any properties missing from an older version."""
    if not client.schema.exists(CHUNK_CLASS):
        client.schema.create_class(CHUNK_SCHEMA)
        return
    existing = {p["name"] for p in client.schema.get(CHUNK_CLASS).get("properties", [])}
    for prop in CHUNK_SCHEMA["properties"]:
        if prop["name"] not in existing:
            client.schema.property.create(CHUNK_CLASS, prop)
