from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DimensionScore(BaseModel):
    name: str
    score: Optional[float] = None
    status: str = "INSUFFICIENT_DATA"  # "PASSED", "WARNING", "CRITICAL", "INSUFFICIENT_DATA"
    passed_checks: int = 0
    failed_checks: int = 0
    total_checks: int = 0
    summary: str = ""


class CompletenessDetail(BaseModel):
    total_pages: int = 0
    successful_pages: int = 0
    failed_pages: int = 0
    pages_with_extracted_data: int = 0
    pages_with_evidence: int = 0
    pages_with_screenshots: int = 0
    pages_with_dom: int = 0
    missing_fields: List[Dict[str, Any]] = Field(default_factory=list)


class ValidationIssue(BaseModel):
    category: str
    target: str
    issue: str
    value: Optional[str] = None
    severity: str = "warning"  # "warning", "error"


class ValidityDetail(BaseModel):
    valid_records: int = 0
    invalid_records: int = 0
    validation_issues: List[ValidationIssue] = Field(default_factory=list)


class ConsistencyCheckItem(BaseModel):
    check_name: str
    status: str  # "PASSED", "FAILED"
    expected: Any = None
    actual: Any = None
    description: str = ""


class ConsistencyDetail(BaseModel):
    passed_checks: int = 0
    failed_checks: int = 0
    consistency_issues: List[ConsistencyCheckItem] = Field(default_factory=list)


class DetectorReadinessItem(BaseModel):
    detector_name: str
    readiness_score: float = 0.0
    status: str = "INSUFFICIENT_DATA"  # "HIGH_READINESS", "MODERATE_READINESS", "LOW_READINESS", "INSUFFICIENT_DATA"
    available_features: List[str] = Field(default_factory=list)
    missing_features: List[str] = Field(default_factory=list)
    explanation: str = ""


class RelevanceDetail(BaseModel):
    detectors_readiness: List[DetectorReadinessItem] = Field(default_factory=list)
    total_relevant_features_found: int = 0
    summary: str = ""


class DuplicateItem(BaseModel):
    duplicate_type: str
    identifier: str
    count: int
    context: Optional[str] = None


class UniquenessDetail(BaseModel):
    total_records: int = 0
    unique_records: int = 0
    duplicate_count: int = 0
    duplicates: List[DuplicateItem] = Field(default_factory=list)


class EvidenceAvailabilityDetail(BaseModel):
    pages_crawled: int = 0
    pages_with_evidence: int = 0
    pages_with_screenshots: int = 0
    pages_with_dom: int = 0
    pages_with_extracted_json: int = 0
    total_evidence_items: int = 0
    total_detection_findings: int = 0
    traceable_detection_findings: int = 0
    untraceable_detection_findings: int = 0
    coverage_percentage: float = 0.0


class PatternReadinessAndSufficiencyItem(BaseModel):
    pattern: str
    input_ready: bool = True
    input_readiness_status: str = "HIGH_READINESS"  # "HIGH_READINESS", "MODERATE_READINESS", "LOW_READINESS", "INSUFFICIENT_DATA"
    input_readiness_score: float = 0.0
    detection_status: str = "NOT_EVALUATED"  # "DETECTED", "NOT_DETECTED", "INSUFFICIENT_EVIDENCE", "NOT_EVALUATED"
    detected: bool = False
    evidence_sufficient: bool = False
    affected_pages_count: int = 0
    evidence_instances_count: int = 0
    explanation: str = ""
    confidence: int = 0


class QualityAssessmentDetails(BaseModel):
    completeness: CompletenessDetail
    validity: ValidityDetail
    consistency: ConsistencyDetail
    relevance: RelevanceDetail
    uniqueness: UniquenessDetail
    evidence_availability: EvidenceAvailabilityDetail
    pattern_readiness_and_sufficiency: List[PatternReadinessAndSufficiencyItem] = Field(default_factory=list)


class DataQualityAssessmentResponse(BaseModel):
    audit_id: str
    platform: str
    start_url: str
    start_time: str
    end_time: str
    audit_status: str
    configured_crawl_depth: int = 0
    actual_max_depth_reached: int = 0
    overall_score: Optional[float] = None
    overall_status: str = "INSUFFICIENT_DATA"  # "EXCELLENT", "ACCEPTABLE", "DEGRADED", "CRITICAL", "INSUFFICIENT_DATA"
    quality_grade: str = "N/A"
    summary_text: str = ""
    methodology: str = (
        "Arithmetic mean of the six unweighted quality dimensions (Completeness, Validity, "
        "Consistency, Relevance, Uniqueness, Evidence Availability) calculated directly on "
        "actual persisted MongoDB audit documents and GridFS artifacts."
    )
    dimensions: Dict[str, DimensionScore]
    details: QualityAssessmentDetails
