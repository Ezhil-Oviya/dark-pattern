import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from app.models.evidence_model import ArtifactReferences, EvidenceItem, EvidenceRecord

logger = logging.getLogger(__name__)


def _to_rel_path(path: Path) -> str:
    """Converts a Path object to a standard relative URL path under artifacts/."""
    p_str = str(path).replace("\\", "/")
    if "artifacts/" in p_str:
        idx = p_str.find("artifacts/")
        return p_str[idx:]
    return p_str


def create_evidence_record(
    website: Dict[str, Any],
    audit_time: str,
    screenshot_path: Path,
    dom_path: Path,
    extracted_path: Path,
    evidence_path: Path,
    extracted_data: Dict[str, Any],
    audit_id: Optional[str] = None,
    crawl_depth: int = 0,
    page_index: int = 0
) -> Dict[str, Any]:
    """
    Constructs a traceable EvidenceRecord tying together:
    - Physical artifacts (screenshot.png, dom.html, extracted.json, evidence.json)
    - Granular evidence items associated with the individual crawled page
    - Page title, crawl depth, and page index provenance.

    Persists the result to evidence.json and returns the record as a dictionary.
    """
    platform = website.get("platform", "Unknown")
    page_url = extracted_data.get("url") or website.get("url", "")
    page_title = extracted_data.get("title") or ""
    website_id = str(website.get("id") or website.get("_id") or "")
    run_id = audit_id or f"audit_{platform.lower().replace(' ', '_')}_{audit_time}"
    page_evidence_id = f"ev_page_{page_index:03d}_{run_id}"

    # Verify physical artifact existence and assign relative URLs
    rel_screenshot = _to_rel_path(screenshot_path) if screenshot_path.exists() else None
    rel_dom = _to_rel_path(dom_path) if dom_path.exists() else None
    rel_extracted = _to_rel_path(extracted_path) if extracted_path.exists() else None
    rel_evidence = _to_rel_path(evidence_path)

    artifacts = ArtifactReferences(
        screenshot=rel_screenshot,
        dom=rel_dom,
        extracted_json=rel_extracted,
        evidence_json=rel_evidence
    )

    evidence_items: List[EvidenceItem] = []

    # 1. Base artifact evidence (Screenshot)
    if rel_screenshot:
        evidence_items.append(
            EvidenceItem(
                evidence_id=f"ev_p{page_index}_scr_{uuid.uuid4().hex[:6]}",
                audit_id=run_id,
                page_url=page_url,
                page_title=page_title,
                crawl_depth=crawl_depth,
                page_index=page_index,
                evidence_type="screenshot",
                category="page_screenshot",
                artifact_path=rel_screenshot,
                text="Full page viewport capture",
                timestamp=audit_time,
                context=f"Platform: {platform} | Page: {page_index} | Depth: {crawl_depth}",
                attributes={"format": "PNG", "full_page": True}
            )
        )

    # 2. Base artifact evidence (DOM HTML)
    if rel_dom:
        evidence_items.append(
            EvidenceItem(
                evidence_id=f"ev_p{page_index}_dom_{uuid.uuid4().hex[:6]}",
                audit_id=run_id,
                page_url=page_url,
                page_title=page_title,
                crawl_depth=crawl_depth,
                page_index=page_index,
                evidence_type="dom_html",
                category="full_dom",
                artifact_path=rel_dom,
                text="Complete rendered HTML DOM structure",
                timestamp=audit_time,
                context=f"Captured at network idle for {page_url} (depth={crawl_depth})",
                attributes={"format": "HTML5", "encoding": "utf-8"}
            )
        )

    # 3. Checkboxes (Only if extracted checkboxes exist)
    checkboxes = extracted_data.get("checkboxes", [])
    for idx, cb in enumerate(checkboxes):
        evidence_items.append(
            EvidenceItem(
                evidence_id=f"ev_p{page_index}_cb_{idx}_{uuid.uuid4().hex[:4]}",
                audit_id=run_id,
                page_url=page_url,
                page_title=page_title,
                crawl_depth=crawl_depth,
                page_index=page_index,
                evidence_type="extracted_data",
                category="checkboxes",
                selector=cb.get("selector"),
                text=cb.get("label") or cb.get("surrounding_text"),
                tag="input",
                artifact_path=rel_extracted or "",
                timestamp=audit_time,
                context=cb.get("surrounding_text"),
                attributes={
                    "name": cb.get("name", ""),
                    "checked": cb.get("checked", False),
                    "default_checked": cb.get("default_checked", False),
                    "is_visible": cb.get("is_visible", True)
                }
            )
        )

    # 4. Urgency Elements (Only if extracted urgency elements exist)
    urgency_elements = extracted_data.get("urgency_elements", [])
    for idx, urg in enumerate(urgency_elements):
        evidence_items.append(
            EvidenceItem(
                evidence_id=f"ev_p{page_index}_urg_{idx}_{uuid.uuid4().hex[:4]}",
                audit_id=run_id,
                page_url=page_url,
                page_title=page_title,
                crawl_depth=crawl_depth,
                page_index=page_index,
                evidence_type="extracted_data",
                category="urgency_elements",
                selector=urg.get("selector"),
                text=urg.get("text"),
                tag=urg.get("tag"),
                artifact_path=rel_extracted or "",
                timestamp=audit_time,
                context=urg.get("text"),
                attributes={
                    "pattern_type": urg.get("pattern_type", ""),
                    "classes": urg.get("classes", "")
                }
            )
        )

    # 5. Price Elements (Only if extracted price elements exist)
    prices = extracted_data.get("prices", [])
    for idx, pr in enumerate(prices):
        evidence_items.append(
            EvidenceItem(
                evidence_id=f"ev_p{page_index}_pr_{idx}_{uuid.uuid4().hex[:4]}",
                audit_id=run_id,
                page_url=page_url,
                page_title=page_title,
                crawl_depth=crawl_depth,
                page_index=page_index,
                evidence_type="extracted_data",
                category="prices",
                selector=pr.get("selector"),
                text=pr.get("raw_text"),
                tag=pr.get("tag"),
                artifact_path=rel_extracted or "",
                timestamp=audit_time,
                context=pr.get("context"),
                attributes={
                    "detected_price": pr.get("detected_price", ""),
                    "currency": pr.get("currency", "")
                }
            )
        )

    # 6. Cart & Basket Items (Only if extracted cart items exist)
    cart_items = extracted_data.get("cart_items", [])
    for idx, ci in enumerate(cart_items):
        evidence_items.append(
            EvidenceItem(
                evidence_id=f"ev_p{page_index}_cart_{idx}_{uuid.uuid4().hex[:4]}",
                audit_id=run_id,
                page_url=page_url,
                page_title=page_title,
                crawl_depth=crawl_depth,
                page_index=page_index,
                evidence_type="extracted_data",
                category="cart_items",
                selector=ci.get("selector"),
                text=ci.get("text"),
                tag=ci.get("tag"),
                artifact_path=rel_extracted or "",
                timestamp=audit_time,
                attributes={
                    "is_addon": ci.get("is_addon", False),
                    "is_checked": ci.get("is_checked", False)
                }
            )
        )

    # 7. Modals / Overlays (Only if extracted modals exist)
    modals = extracted_data.get("modals", [])
    for idx, md in enumerate(modals):
        evidence_items.append(
            EvidenceItem(
                evidence_id=f"ev_p{page_index}_md_{idx}_{uuid.uuid4().hex[:4]}",
                audit_id=run_id,
                page_url=page_url,
                page_title=page_title,
                crawl_depth=crawl_depth,
                page_index=page_index,
                evidence_type="extracted_data",
                category="modals",
                selector=md.get("selector"),
                text=md.get("text"),
                tag=md.get("tag"),
                artifact_path=rel_extracted or "",
                timestamp=audit_time,
                attributes={
                    "id": md.get("id", ""),
                    "classes": md.get("classes", "")
                }
            )
        )

    # Construct EvidenceRecord
    summary_counts = {
        "total_evidence_items": len(evidence_items),
        "total_checkbox_evidence": len(checkboxes),
        "total_urgency_evidence": len(urgency_elements),
        "total_price_evidence": len(prices),
        "total_cart_evidence": len(cart_items),
        "total_modal_evidence": len(modals),
        "has_screenshot": rel_screenshot is not None,
        "has_dom": rel_dom is not None,
        "has_extracted_data": rel_extracted is not None
    }

    evidence_record = EvidenceRecord(
        evidence_id=page_evidence_id,
        audit_id=run_id,
        website_id=website_id,
        platform=platform,
        page_url=page_url,
        page_title=page_title,
        crawl_depth=crawl_depth,
        page_index=page_index,
        audit_time=audit_time,
        artifacts=artifacts,
        summary=summary_counts,
        evidence_items=evidence_items
    )

    record_dict = evidence_record.model_dump()

    # Persist evidence.json
    try:
        with open(evidence_path, "w", encoding="utf-8") as f:
            json.dump(record_dict, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to persist evidence.json: {e}")

    return record_dict
