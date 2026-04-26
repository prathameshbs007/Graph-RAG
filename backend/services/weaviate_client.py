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

db = WeaviateDB()
