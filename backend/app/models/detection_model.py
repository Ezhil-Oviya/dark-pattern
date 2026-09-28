from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Centralized Dark Pattern Taxonomy (8 Patterns)
ALL_PATTERNS: List[str] = [
    "False Urgency",
    "Drip Pricing",
    "Bait and Switch",
    "Confirmshaming",
    "SaaS Billing",
    "Interface Interference",
    "Forced Action",
    "Basket Sneaking",
]


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
    pattern: str  # e.g., "False Urgency", "Drip Pricing", "Bait and Switch", "Confirmshaming", "SaaS Billing", "Interface Interference", "Forced Action", "Basket Sneaking"
    status: str = "NOT_DETECTED"  # "DETECTED", "NOT_DETECTED", "INSUFFICIENT_EVIDENCE", "NOT_EVALUATED"
    detected: bool = False
    model_score: Optional[float] = None  # AI/NLP semantic model classification score (0.0 to 1.0)
    validation_status: Optional[str] = None  # DOM/Evidence deterministic validation state ("PASSED", "FAILED", "SKIPPED")
    confidence: int = Field(default=0, ge=0, le=100)
    reason: str
    page_url: str
    evidence: List[DetectionEvidenceRef] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

