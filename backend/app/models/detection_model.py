from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DetectionEvidenceRef(BaseModel):
    evidence_id: str
    evidence_type: str = "extracted_data"
    category: str
    selector: Optional[str] = None
    text: Optional[str] = None
    tag: Optional[str] = None
    artifact_path: str = ""
    context: Optional[str] = None


class DetectionFinding(BaseModel):
    pattern: str  # e.g., "False Urgency", "Drip Pricing", "Bait and Switch", "Confirmshaming"
    status: str = "NOT_DETECTED"  # "DETECTED", "NOT_DETECTED", "INSUFFICIENT_EVIDENCE"
    detected: bool = False
    confidence: int = Field(default=0, ge=0, le=100)
    reason: str
    page_url: str
    evidence: List[DetectionEvidenceRef] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
