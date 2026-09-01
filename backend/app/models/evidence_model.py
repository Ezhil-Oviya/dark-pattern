from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ArtifactReferences(BaseModel):
    screenshot: Optional[str] = None
    dom: Optional[str] = None
    extracted_json: Optional[str] = None
    evidence_json: Optional[str] = None


class EvidenceItem(BaseModel):
    evidence_id: str
    audit_id: Optional[str] = None
    page_url: str
    page_title: Optional[str] = None
    crawl_depth: int = 0
    page_index: int = 0
    evidence_type: str = "extracted_data"  # "screenshot", "dom_html", "extracted_data"
    category: str
    selector: Optional[str] = None
    text: Optional[str] = None
    tag: Optional[str] = None
    artifact_path: str
    timestamp: Optional[str] = None
    context: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class EvidenceRecord(BaseModel):
    evidence_id: str
    audit_id: Optional[str] = None
    website_id: Optional[str] = None
    platform: str
    page_url: str
    page_title: Optional[str] = None
    crawl_depth: int = 0
    page_index: int = 0
    audit_time: str
    artifacts: ArtifactReferences
    summary: Dict[str, int] = Field(default_factory=dict)
    evidence_items: List[EvidenceItem] = Field(default_factory=list)


class PageSummary(BaseModel):
    page_index: int
    folder: str
    url: str
    title: str = ""
    depth: int = 0
    status: str = "success"  # "success", "failed"
    error: Optional[str] = None
    evidence_count: int = 0
    findings_count: int = 0
    artifacts: ArtifactReferences
    detections: List[Dict[str, Any]] = Field(default_factory=list)


class AuditSummary(BaseModel):
    audit_id: str
    website_id: Optional[str] = None
    platform: str
    start_url: str
    configured_crawl_depth: int = 0
    actual_max_depth_reached: int = 0
    max_pages_limit: int = 50
    pages_discovered: int = 0
    pages_crawled: int = 0
    pages_successful: int = 0
    pages_failed: int = 0
    total_evidence_items: int = 0
    total_dark_pattern_findings: int = 0
    start_time: str
    end_time: str
    status: str = "completed"
    dark_pattern_summary: List[Dict[str, Any]] = Field(default_factory=list)
    pages: List[PageSummary] = Field(default_factory=list)
