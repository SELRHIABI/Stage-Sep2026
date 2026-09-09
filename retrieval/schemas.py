from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class ChunkMetadata(BaseModel):
    source_document: str = Field(default="unknown_source.pdf", description="Nom du document source")
    page_number: Optional[int] = Field(default=1, description="Numéro de page")
    chunk_id: str = Field(..., description="Identifiant unique du chunk")

class ChunkInput(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SearchResult(BaseModel):
    rank: int
    chunk_id: str
    content: str
    similarity_score: float
    metadata: Dict[str, Any]