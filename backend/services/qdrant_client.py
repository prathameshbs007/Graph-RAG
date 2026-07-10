import logging
import uuid
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    Fusion,
    FusionQuery,
    MatchValue,
    Modifier,
    PayloadSchemaType,
    PointStruct,
    Prefetch,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from config import settings

logger = logging.getLogger(__name__)

DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"
TEXT_DENSE_SIZE = 384

# text_chunks/audio_chunks carry named dense+sparse vectors for hybrid search.
# figure_chunks (CLIP space) and concepts are single-vector collections, unaffected
# by hybrid search -- fusing CLIP similarity with BM25 term matches makes no sense.
HYBRID_COLLECTIONS = ("text_chunks", "audio_chunks")
SIMPLE_COLLECTIONS = {"figure_chunks": 512, "concepts": 384}
ALL_COLLECTION_NAMES = (*HYBRID_COLLECTIONS, *SIMPLE_COLLECTIONS.keys())

COLLECTION_MODALITY = {
    "text_chunks": "text",
    "audio_chunks": "audio",
}


class QdrantDB:
    def __init__(self):
        self.client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)

    def init_collections(self):
        existing = {c.name for c in self.client.get_collections().collections}

        for name in HYBRID_COLLECTIONS:
            if name not in existing:
                self.client.create_collection(
                    collection_name=name,
                    vectors_config={DENSE_VECTOR_NAME: VectorParams(size=TEXT_DENSE_SIZE, distance=Distance.COSINE)},
                    sparse_vectors_config={SPARSE_VECTOR_NAME: SparseVectorParams(modifier=Modifier.IDF)},
                )
                self.client.create_payload_index(
                    collection_name=name,
                    field_name="paper_id",
                    field_schema=PayloadSchemaType.KEYWORD,
                )

        for name, size in SIMPLE_COLLECTIONS.items():
            if name not in existing:
                self.client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(size=size, distance=Distance.COSINE),
                )
                if name == "figure_chunks":
                    self.client.create_payload_index(
                        collection_name=name,
                        field_name="paper_id",
                        field_schema=PayloadSchemaType.KEYWORD,
                    )
                    self.client.create_payload_index(
                        collection_name=name,
                        field_name="figure_id",
                        field_schema=PayloadSchemaType.KEYWORD,
                    )

    def _hybrid_vector(self, chunk: dict) -> dict:
        vector = {DENSE_VECTOR_NAME: chunk["vector"]}
        if chunk.get("sparse_vector") is not None:
            vector[SPARSE_VECTOR_NAME] = chunk["sparse_vector"]
        return vector

    def insert_text_chunks(self, chunks: list[dict]):
        if not chunks:
            return
        points = []
        for chunk in chunks:
            chunk_id = str(uuid.uuid4())
            points.append(PointStruct(
                id=chunk_id,
                vector=self._hybrid_vector(chunk),
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
                vector=self._hybrid_vector(chunk),
                payload={
                    "chunk_id": chunk_id,
                    "audio_id": chunk.get("audio_id"),
                    "title": chunk.get("title"),
                    "chunk_text": chunk.get("chunk_text"),
                    "start_time": chunk.get("start_time"),
                    "end_time": chunk.get("end_time"),
                    "source_paper_id": chunk.get("source_paper_id", ""),
                    "paper_id": chunk.get("source_paper_id", ""),
                },
            ))
        self.client.upsert(collection_name="audio_chunks", points=points)

    def _search_hybrid_collection(self, collection: str, query_vector: list[float], sparse_query: Optional[SparseVector], limit: int):
        if settings.HYBRID_SEARCH and sparse_query is not None:
            return self.client.query_points(
                collection_name=collection,
                prefetch=[
                    Prefetch(query=query_vector, using=DENSE_VECTOR_NAME, limit=limit),
                    Prefetch(query=sparse_query, using=SPARSE_VECTOR_NAME, limit=limit),
                ],
                query=FusionQuery(fusion=Fusion.RRF),
                limit=limit,
                with_payload=True,
            ).points
        return self.client.query_points(
            collection_name=collection,
            query=query_vector,
            using=DENSE_VECTOR_NAME,
            limit=limit,
            with_payload=True,
        ).points

    def search_all_classes(
        self,
        query_vector: list[float],
        clip_vector: Optional[list[float]] = None,
        sparse_query: Optional[SparseVector] = None,
        limit: int = 10,
    ) -> tuple[list[dict], list[dict]]:
        """Search all collections, keeping text-space (text/audio) and CLIP-space (figures)
        results in separate lists — their scores live in different embedding spaces and are
        not comparable, so they must never be merged into one ranked list. Text/audio search
        uses RRF fusion of dense + BM25 sparse results when HYBRID_SEARCH is enabled and a
        sparse query is supplied; otherwise falls back to dense-only search."""
        text_space_results = []
        image_space_results = []

        for collection, modality in COLLECTION_MODALITY.items():
            try:
                hits = self._search_hybrid_collection(collection, query_vector, sparse_query, limit)
                for hit in hits:
                    payload = dict(hit.payload or {})
                    payload["modality"] = modality
                    payload["score"] = hit.score
                    payload.setdefault("chunk_id", str(hit.id))
                    if collection == "audio_chunks":
                        payload["paper_id"] = payload.get("source_paper_id", "")
                        payload["paper_title"] = payload.get("title", "")
                    payload["chunk_text"] = payload.get("chunk_text") or payload.get("caption", "")
                    text_space_results.append(payload)
            except Exception as e:
                logger.error("Error searching %s: %s", collection, e)

        try:
            hits = self.client.query_points(collection_name="figure_chunks", query=clip_vector, limit=limit, with_payload=True).points
            for hit in hits:
                payload = dict(hit.payload or {})
                payload["modality"] = "image"
                payload["score"] = hit.score
                payload.setdefault("chunk_id", str(hit.id))
                payload["chunk_text"] = payload.get("chunk_text") or payload.get("caption", "")
                image_space_results.append(payload)
        except Exception as e:
            logger.error("Error searching figure_chunks: %s", e)

        text_space_results.sort(key=lambda x: x["score"], reverse=True)
        image_space_results.sort(key=lambda x: x["score"], reverse=True)
        return text_space_results, image_space_results

    def find_top_concept_match(self, vector: list[float]) -> Optional[tuple[str, float]]:
        """Return (name, cosine_score) of the single nearest existing concept, or None
        if the concepts collection is empty. Does not apply any threshold — callers
        decide what score (and what other evidence, e.g. lexical overlap) counts as
        a match."""
        hits = self.client.query_points(collection_name="concepts", query=vector, limit=1, with_payload=True).points
        if not hits:
            return None
        return hits[0].payload.get("name"), hits[0].score

    def upsert_concept(self, name: str, vector: list[float]):
        self.client.upsert(collection_name="concepts", points=[
            PointStruct(id=str(uuid.uuid4()), vector=vector, payload={"name": name}),
        ])

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
        for name in ALL_COLLECTION_NAMES:
            if name in existing:
                self.client.delete_collection(collection_name=name)
        self.init_collections()


db = QdrantDB()
