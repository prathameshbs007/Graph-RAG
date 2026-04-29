from pydantic import BaseModel

class IngestPDFResponse(BaseModel):
    paper_id: str
    chunks_created: int
    figures_extracted: int
    graph_nodes_created: int
    status: str

class IngestAudioResponse(BaseModel):
    audio_id: str
    segments: int
    chunks_created: int
    duration_seconds: float
    status: str

class IngestImageResponse(BaseModel):
    image_id: str
    chunks_created: int
    status: str
