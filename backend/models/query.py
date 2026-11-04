from typing import Any, List, Literal, Optional

from pydantic import BaseModel


class QueryRequest(BaseModel):
    text: str
    # Which retrieval system to run (see GET /query/systems). "full" is ResearchOS itself;
    # the others are the baselines and ablations used by the evaluation.
    system: str = "full"
    # Apply reranker feedback for this query. None = whatever the system defines.
    learn: Optional[bool] = None
    seed: Optional[int] = None  # makes the 5% edge exploration reproducible
    verify: Optional[bool] = None  # override claim verification


class SourceChunk(BaseModel):
    evidence_id: str = ""
    chunk_id: str
    paper_id: str
    paper_title: str
    authors: List[str] = []
    year: Optional[int] = None
    chunk_text: str
    score: float  # reranker relevance (or fused score if no reranker)
    modality: Literal["text", "image", "audio"]
    page: Optional[int] = None
    section: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    audio_id: Optional[str] = None
    location: str = ""
    found_by: List[str] = []
    via: str = "seed"
    cited: bool = False


class FigureReference(BaseModel):
    evidence_id: str = ""
    figure_id: str
    paper_id: str
    paper_title: str
    page: int
    caption: str
    description: str = ""
    bbox: List[float] = []
    url: str
    score: float
    cited: bool = False


class GraphContext(BaseModel):
    related_papers: List[str]
    concepts: List[str]


class Claim(BaseModel):
    text: str
    evidence_ids: List[str] = []
    verdict: Literal["supported", "unsupported", "unchecked"] = "unchecked"


class ClaimStats(BaseModel):
    supported: int = 0
    unsupported: int = 0
    unchecked: int = 0
    verified: bool = False


class QueryResponse(BaseModel):
    query_id: str = ""
    answer: str
    sources: List[SourceChunk]
    figures: List[FigureReference]
    graph_context: GraphContext
    claims: List[Claim] = []
    claim_stats: ClaimStats = ClaimStats()
    diagnostics: dict[str, Any] = {}
