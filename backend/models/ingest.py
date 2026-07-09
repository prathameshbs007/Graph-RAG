from pydantic import BaseModel

class IngestAcceptedResponse(BaseModel):
    id: str
    status: str = "processing"
