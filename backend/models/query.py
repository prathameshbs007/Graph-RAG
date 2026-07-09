from pydantic import BaseModel
from typing import Optional, List, Literal

class QueryRequest(BaseModel):
    text: str
    top_k: int = 10
    rerank_top_n: int = 5

class SourceChunk(BaseModel):
    chunk_id: str
    paper_id: str
    paper_title: str
    authors: List[str]
    year: Optional[int]
    chunk_text: str
    score: float
    modality: Literal["text", "image", "audio"]
    start_time: Optional[float] = None
    end_time: Optional[float] = None

class FigureReference(BaseModel):
    figure_id: str
    paper_id: str
    paper_title: str
    page: int
    caption: str
    url: str
    score: float

class GraphContext(BaseModel):
    related_papers: List[str]
    concepts: List[str]

class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]
    figures: List[FigureReference]
    graph_context: GraphContext
