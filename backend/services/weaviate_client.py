import weaviate
from config import settings

class WeaviateDB:
    def __init__(self):
        self.client = weaviate.Client(url=settings.WEAVIATE_URL)

    def insert_text_chunks(self, chunks: list[dict]):
        with self.client.batch as batch:
            batch.batch_size=100
            for chunk in chunks:
                properties = {
                    "paper_id": chunk.get("paper_id"),
                    "paper_title": chunk.get("paper_title"),
                    "authors": chunk.get("authors", []),
                    "year": chunk.get("year"),
                    "chunk_text": chunk.get("chunk_text"),
                    "chunk_index": chunk.get("chunk_index"),
                    "page": chunk.get("page")
                }
                vector = chunk.get("vector")
                batch.add_data_object(
                    data_object=properties,
                    class_name="TextChunk",
                    vector=vector
                )

    def insert_figure_chunks(self, figures: list[dict]):
        with self.client.batch as batch:
            batch.batch_size=100
            for fig in figures:
                properties = {
                    "paper_id": fig.get("paper_id"),
                    "paper_title": fig.get("paper_title"),
                    "figure_id": fig.get("figure_id"),
                    "caption": fig.get("caption"),
                    "page": fig.get("page"),
                    "file_path": fig.get("file_path"),
                }
                vector = fig.get("vector")
                batch.add_data_object(
                    data_object=properties,
                    class_name="FigureChunk",
                    vector=vector
                )

    def insert_audio_chunks(self, chunks: list[dict]):
        with self.client.batch as batch:
            batch.batch_size=100
            for chunk in chunks:
                properties = {
                    "audio_id": chunk.get("audio_id"),
                    "title": chunk.get("title"),
                    "chunk_text": chunk.get("chunk_text"),
                    "start_time": chunk.get("start_time"),
                    "end_time": chunk.get("end_time"),
                    "source_paper_id": chunk.get("source_paper_id", ""),
                }
                vector = chunk.get("vector")
                batch.add_data_object(
                    data_object=properties,
                    class_name="AudioChunk",
                    vector=vector
                )

    def search_all_classes(self, query_vector: list[float], clip_vector: list[float] = None, limit: int = 10) -> list[dict]:
        results = []
        # Standardize retrieval field mapping across classes
        fields_map = {
            "TextChunk": ["paper_id", "paper_title", "chunk_text", "authors", "year"],
            "FigureChunk": ["paper_id", "paper_title", "figure_id", "caption", "file_path", "page"],
            "AudioChunk": ["source_paper_id", "title", "chunk_text"]
        }
        for cls, fields in fields_map.items():
            try:
                target_vector = clip_vector if cls == "FigureChunk" and clip_vector else query_vector
                res = (
                    self.client.query
                    .get(cls, fields)
                    .with_near_vector({"vector": target_vector})
                    .with_limit(limit)
                    .with_additional("certainty")
                    .do()
                )
                items = res.get("data", {}).get("Get", {}).get(cls)
                if items:
                    for item in items:
                        item_copy = dict(item)
                        item_copy["modality"] = "text" if cls == "TextChunk" else ("image" if cls == "FigureChunk" else "audio")
                        item_copy["score"] = item_copy.pop("_additional", {}).get("certainty", 0)
                        
                        # Normalize common fields for uniform processing
                        if cls == "AudioChunk":
                            item_copy["paper_id"] = item_copy.get("source_paper_id", "")
                            item_copy["paper_title"] = item_copy.get("title", "")
                            
                        item_copy["chunk_text"] = item_copy.get("chunk_text") or item_copy.get("caption", "")
                        item_copy["chunk_id"] = "chunk_" + str(hash(item_copy["chunk_text"]))
                        results.append(item_copy)
            except Exception as e:
                print(f"Error searching {cls}: {e}")
        
        # Sort the overall results for good measure, but do not truncate globally.
        # Top-K was already applied per-class by .with_limit(limit) inside the loop! 
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

db = WeaviateDB()
