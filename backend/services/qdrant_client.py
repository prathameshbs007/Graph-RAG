import logging
import uuid
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from config import settings

logger = logging.getLogger(__name__)

COLLECTIONS = {
    "text_chunks": 384,
    "figure_chunks": 512,
    "audio_chunks": 384,
}

COLLECTION_MODALITY = {
    "text_chunks": "text",
    "figure_chunks": "image",
    "audio_chunks": "audio",
}


class QdrantDB:
    def __init__(self):
        self.client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)

    def init_collections(self):
        existing = {c.name for c in self.client.get_collections().collections}
        for name, size in COLLECTIONS.items():
            if name not in existing:
                self.client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(size=size, distance=Distance.COSINE),
                )
                self.client.create_payload_index(
                    collection_name=name,
                    field_name="paper_id",
                    field_schema=PayloadSchemaType.KEYWORD,
                )
                if name == "figure_chunks":
                    self.client.create_payload_index(
                        collection_name=name,
                        field_name="figure_id",
                        field_schema=PayloadSchemaType.KEYWORD,
                    )

    def insert_text_chunks(self, chunks: list[dict]):
        if not chunks:
            return
        points = []
        for chunk in chunks:
            chunk_id = str(uuid.uuid4())
            points.append(PointStruct(
                id=chunk_id,
                vector=chunk["vector"],
                payload={
                    "chunk_id": chunk_id,
                    "paper_id": chunk.get("paper_id"),
                    "paper_title": chunk.get("paper_title"),
                    "authors": chunk.get("authors", []),
                    "year": chunk.get("year"),
                    "chunk_text": chunk.get("chunk_text"),
                    "chunk_index": chunk.get("chunk_index"),
                    "page": chunk.get("page"),
                },
            ))
        self.client.upsert(collection_name="text_chunks", points=points)

    def insert_figure_chunks(self, figures: list[dict]):
        if not figures:
            return
        points = []
        for fig in figures:
            points.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=fig["vector"],
                payload={
                    "paper_id": fig.get("paper_id"),
                    "paper_title": fig.get("paper_title"),
                    "figure_id": fig.get("figure_id"),
                    "caption": fig.get("caption"),
                    "page": fig.get("page"),
                    "file_path": fig.get("file_path"),
                    "image_base64": fig.get("image_base64"),
                },
            ))
        self.client.upsert(collection_name="figure_chunks", points=points)

    def insert_audio_chunks(self, chunks: list[dict]):
        if not chunks:
            return
        points = []
        for chunk in chunks:
            chunk_id = str(uuid.uuid4())
            points.append(PointStruct(
                id=chunk_id,
                vector=chunk["vector"],
                payload={
                    "chunk_id": chunk_id,
                    "audio_id": chunk.get("audio_id"),
                    "title": chunk.get("title"),
                    "chunk_text": chunk.get("chunk_text"),
                    "start_time": chunk.get("start_time"),
                    "end_time": chunk.get("end_time"),
                    "source_paper_id": chunk.get("source_paper_id", ""),
                },
            ))
        self.client.upsert(collection_name="audio_chunks", points=points)

    def search_all_classes(self, query_vector: list[float], clip_vector: Optional[list[float]] = None, limit: int = 10) -> list[dict]:
        results = []
        for collection, modality in COLLECTION_MODALITY.items():
            try:
                vec = clip_vector if collection == "figure_chunks" and clip_vector else query_vector
                hits = self.client.query_points(collection_name=collection, query=vec, limit=limit, with_payload=True).points
                for hit in hits:
                    payload = dict(hit.payload or {})
                    payload["modality"] = modality
                    payload["score"] = hit.score
                    payload.setdefault("chunk_id", str(hit.id))
                    if collection == "audio_chunks":
                        payload["paper_id"] = payload.get("source_paper_id", "")
                        payload["paper_title"] = payload.get("title", "")
                    payload["chunk_text"] = payload.get("chunk_text") or payload.get("caption", "")
                    results.append(payload)
            except Exception as e:
                logger.error("Error searching %s: %s", collection, e)

        # Sort the overall results for good measure, but do not truncate globally.
        # Top-K was already applied per-collection by `limit` inside the loop!
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def get_figure_by_id(self, figure_id: str) -> Optional[dict]:
        points, _ = self.client.scroll(
            collection_name="figure_chunks",
            scroll_filter=Filter(must=[FieldCondition(key="figure_id", match=MatchValue(value=figure_id))]),
            limit=1,
            with_payload=True,
        )
        if points:
            return dict(points[0].payload or {})
        return None

    def delete_all(self):
        existing = {c.name for c in self.client.get_collections().collections}
        for name in COLLECTIONS:
            if name in existing:
                self.client.delete_collection(collection_name=name)
        self.init_collections()


db = QdrantDB()
