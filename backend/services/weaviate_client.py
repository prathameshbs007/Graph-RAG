import weaviate
from weaviate.util import generate_uuid5

from config import settings
from services.schema import CHUNK_CLASS, PROPERTY_NAMES, ensure_weaviate_schema

# Properties that carry data into the stored object (``vector`` and bookkeeping are separate).
_INSERT_FIELDS = [p for p in PROPERTY_NAMES]


class WeaviateError(RuntimeError):
    pass


class WeaviateDB:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        # connect lazily so importing the app never needs a live database
        if self._client is None:
            self._client = weaviate.Client(url=settings.WEAVIATE_URL)
        return self._client

    # ------------------------------------------------------------------ schema
    def ensure_schema(self):
        ensure_weaviate_schema(self.client)

    def reset(self):
        """Drop everything and recreate the schema."""
        self.client.schema.delete_all()
        self.ensure_schema()

    # ------------------------------------------------------------------ insert
    def insert_chunks(self, chunks: list[dict]) -> int:
        """Insert items that each have ``chunk_id``, ``modality`` and ``vector``.

        The object UUID is derived from ``chunk_id`` so re-ingesting overwrites rather
        than duplicates.
        """
        errors: list[str] = []

        def on_batch(results):
            for r in results or []:
                errs = r.get("result", {}).get("errors")
                if errs:
                    errors.append(str(errs))

        self.client.batch.configure(batch_size=100, callback=on_batch)
        with self.client.batch as batch:
            for chunk in chunks:
                if not chunk.get("vector"):
                    raise WeaviateError(f"chunk {chunk.get('chunk_id')} has no vector")
                props = {k: chunk[k] for k in _INSERT_FIELDS if chunk.get(k) is not None}
                batch.add_data_object(
                    data_object=props,
                    class_name=CHUNK_CLASS,
                    uuid=generate_uuid5(chunk["chunk_id"]),
                    vector=chunk["vector"],
                )
        if errors:
            raise WeaviateError(f"{len(errors)} batch errors, first: {errors[0]}")
        return len(chunks)

    # ------------------------------------------------------------------ search
    def _do(self, builder) -> list[dict]:
        res = builder.do()
        if res.get("errors"):
            raise WeaviateError(str(res["errors"]))
        return res.get("data", {}).get("Get", {}).get(CHUNK_CLASS) or []

    @staticmethod
    def _hit(item: dict, score: float) -> dict:
        hit = {k: v for k, v in item.items() if k != "_additional"}
        hit["score"] = score
        return hit

    def bm25(self, query: str, limit: int) -> list[dict]:
        """Top-``limit`` by BM25 over ``chunk_text``, best first."""
        if not query.strip():
            return []
        builder = (
            self.client.query.get(CHUNK_CLASS, PROPERTY_NAMES)
            .with_bm25(query=query, properties=["chunk_text"])
            .with_additional(["score"])
            .with_limit(limit)
        )
        return [self._hit(i, float(i.get("_additional", {}).get("score") or 0.0)) for i in self._do(builder)]

    def dense(self, vector: list[float], limit: int) -> list[dict]:
        """Top-``limit`` by cosine similarity, best first (score = certainty in [0, 1])."""
        builder = (
            self.client.query.get(CHUNK_CLASS, PROPERTY_NAMES)
            .with_near_vector({"vector": vector})
            .with_additional(["certainty"])
            .with_limit(limit)
        )
        return [self._hit(i, float(i.get("_additional", {}).get("certainty") or 0.0)) for i in self._do(builder)]

    def fetch(self, chunk_ids: list[str]) -> dict[str, dict]:
        """Load items by ``chunk_id`` (used for items reached through the graph)."""
        if not chunk_ids:
            return {}
        where = {
            "operator": "Or",
            "operands": [{"path": ["chunk_id"], "operator": "Equal", "valueText": cid} for cid in chunk_ids],
        }
        builder = (
            self.client.query.get(CHUNK_CLASS, PROPERTY_NAMES).with_where(where).with_limit(len(chunk_ids))
        )
        return {i["chunk_id"]: self._hit(i, 0.0) for i in self._do(builder)}

    def iterate_chunks(self, batch: int = 200):
        """Every stored chunk, using Weaviate's cursor API (used to build the evaluation corpus)."""
        cursor = None
        while True:
            q = self.client.query.get(CHUNK_CLASS, PROPERTY_NAMES).with_additional(["id"]).with_limit(batch)
            if cursor:
                q = q.with_after(cursor)
            items = self._do(q)
            if not items:
                return
            for it in items:
                yield {k: v for k, v in it.items() if k != "_additional"}
            cursor = items[-1]["_additional"]["id"]

    def delete_where(self, prop: str, value: str):
        """Delete every object whose ``prop`` equals ``value`` (used to undo a failed ingest)."""
        self.client.batch.delete_objects(
            class_name=CHUNK_CLASS,
            where={"path": [prop], "operator": "Equal", "valueText": value},
        )

    def count(self) -> int:
        res = self.client.query.aggregate(CHUNK_CLASS).with_meta_count().do()
        try:
            return res["data"]["Aggregate"][CHUNK_CLASS][0]["meta"]["count"]
        except (KeyError, IndexError, TypeError):
            return 0


db = WeaviateDB()
