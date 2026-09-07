from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ExtractionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REJECTED = "REJECTED"

class QualityLabel(str, Enum):
    HIGH_QUALITY = "HIGH_QUALITY"
    MEDIUM_QUALITY = "MEDIUM_QUALITY"
    SUSPICIOUS_OR_SCAN = "SUSPICIOUS_OR_SCAN"

class PageMetadata(BaseModel):
    page_number: int
    char_count: int
    preview: str

class ExtractionReport(BaseModel):
    file_path: str
    file_name: str
    file_size_bytes: int
    extension: str
    status: ExtractionStatus
    text: Optional[str] = None
    preview: Optional[str] = None
    total_chars: int = 0
    pages_count: int = 0
    pages_detail: List[PageMetadata] = Field(default_factory=list)
    quality_score: float = 0.0
    quality_label: Optional[QualityLabel] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)