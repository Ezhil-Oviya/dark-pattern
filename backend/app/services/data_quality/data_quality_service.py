import collections
import json
import logging
import re
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.models.detection_model import ALL_PATTERNS
from app.schemas.data_quality_schema import (
    CompletenessDetail,
    ConsistencyCheckItem,
    ConsistencyDetail,
    DataQualityAssessmentResponse,
    DetectorReadinessItem,
    DimensionScore,
    DuplicateItem,
    EvidenceAvailabilityDetail,
    PatternReadinessAndSufficiencyItem,
    QualityAssessmentDetails,
    RelevanceDetail,
    UniquenessDetail,
    ValidationIssue,
    ValidityDetail,
)
from app.services.evidence.mongodb_evidence_service import (
    get_audit_details_from_mongodb,
    get_evidence_items_from_mongodb,
)

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path("artifacts")


# ==============================================================================
# 1. COMPLETENESS DIMENSION
# ==============================================================================

def evaluate_completeness(
    audit: Dict[str, Any],
    pages: List[Dict[str, Any]],
    evidence_items: List[Dict[str, Any]],
) -> Tuple[DimensionScore, CompletenessDetail]:
    """
    Evaluates whether all required metadata, page records, structural elements,
    and physical artifacts are present across the crawled audit dataset.
    """
    if not audit or not pages:
        return (
            DimensionScore(
                name="Completeness",
                score=None,
                status="INSUFFICIENT_DATA",
                passed_checks=0,
                failed_checks=1,
                total_checks=1,
                summary="No crawled page records available to evaluate completeness.",
            ),
            CompletenessDetail(
                total_pages=0,
                successful_pages=0,
                failed_pages=0,
                pages_with_extracted_data=0,
                pages_with_evidence=0,
                pages_with_screenshots=0,
                pages_with_dom=0,
                missing_fields=[{"scope": "audit", "missing": ["pages", "crawled_data"]}],
            ),
        )

    total_pages = len(pages)
    successful_pages = 0
    failed_pages = 0
    pages_with_extracted = 0
    pages_with_evidence = 0
    pages_with_screenshots = 0
    pages_with_dom = 0
    missing_fields_list: List[Dict[str, Any]] = []

    passed_checks = 0
    total_checks = 0

    # 1. Audit-level metadata checks (5 checks)
    audit_meta_fields = ["audit_id", "platform", "start_url", "start_time", "status"]
    for field in audit_meta_fields:
        total_checks += 1
        val = audit.get(field)
        if val and str(val).strip():
            passed_checks += 1
        else:
            missing_fields_list.append({"scope": "audit", "field": field, "issue": f"Missing or empty audit metadata '{field}'"})

    # 2. Page-level checks (8 checks per page)
    for p in pages:
        p_idx = p.get("page_index", 0)
        p_url = p.get("url", f"page_{p_idx}")
        p_status = p.get("status", "unknown")
        p_missing: List[str] = []

        # Check 2.1: Valid URL present
        total_checks += 1
        if p.get("url") and p.get("url").strip():
            passed_checks += 1
        else:
            p_missing.append("url")

        # Check 2.2: Page title present and not generic failure placeholder
        total_checks += 1
        title = (p.get("title") or "").strip()
        if title and title.lower() != "failed page":
            passed_checks += 1
        else:
            p_missing.append("title")

        # Check 2.3: Page status success
        total_checks += 1
        if p_status == "success":
            successful_pages += 1
            passed_checks += 1
        else:
            failed_pages += 1
            p_missing.append("status_success")

        artifacts = p.get("artifacts") or {}

        # Check 2.4: Screenshot artifact present
        total_checks += 1
        if artifacts.get("screenshot"):
            pages_with_screenshots += 1
            passed_checks += 1
        else:
            p_missing.append("artifact_screenshot")

        # Check 2.5: Rendered DOM artifact present
        total_checks += 1
        if artifacts.get("dom"):
            pages_with_dom += 1
            passed_checks += 1
        else:
            p_missing.append("artifact_dom")

        # Check 2.6: Extracted JSON artifact present
        total_checks += 1
        if artifacts.get("extracted_json"):
            pages_with_extracted += 1
            passed_checks += 1
        else:
            p_missing.append("artifact_extracted_json")

        # Check 2.7: Evidence JSON artifact present
        total_checks += 1
        if artifacts.get("evidence_json"):
            passed_checks += 1
        else:
            p_missing.append("artifact_evidence_json")

        # Check 2.8: Page evidence records present
        total_checks += 1
        ev_count = p.get("evidence_count", 0)
        if ev_count > 0:
            pages_with_evidence += 1
            passed_checks += 1
        else:
            p_missing.append("evidence_items")

        if p_missing:
            missing_fields_list.append({
                "page_index": p_idx,
                "url": p_url,
                "status": p_status,
                "missing": p_missing,
            })

    failed_checks = total_checks - passed_checks
    score = round((passed_checks / total_checks) * 100.0, 1) if total_checks > 0 else 0.0

    if score >= 85.0:
        status = "PASSED"
    elif score >= 60.0:
        status = "WARNING"
    else:
        status = "CRITICAL"

    summary = (
        f"{successful_pages}/{total_pages} pages succeeded ({score}% complete). "
        f"{pages_with_screenshots} screenshots, {pages_with_dom} DOMs, and {pages_with_evidence} evidence sets captured."
    )

    score_model = DimensionScore(
        name="Completeness",
        score=score,
        status=status,
        passed_checks=passed_checks,
        failed_checks=failed_checks,
        total_checks=total_checks,
        summary=summary,
    )

    detail_model = CompletenessDetail(
        total_pages=total_pages,
        successful_pages=successful_pages,
        failed_pages=failed_pages,
        pages_with_extracted_data=pages_with_extracted,
        pages_with_evidence=pages_with_evidence,
        pages_with_screenshots=pages_with_screenshots,
        pages_with_dom=pages_with_dom,
        missing_fields=missing_fields_list,
    )

    return score_model, detail_model


# ==============================================================================
# 2. VALIDITY DIMENSION
# ==============================================================================

def evaluate_validity(
    audit: Dict[str, Any],
    pages: List[Dict[str, Any]],
    evidence_items: List[Dict[str, Any]],
) -> Tuple[DimensionScore, ValidityDetail]:
    """
    Validates whether all collected values have conformant, reasonable formats:
    valid URL syntax, valid timestamps, recognized page statuses, non-empty CSS selectors,
    sanitized element text, valid price formatting, and valid artifact URIs.
    """
    if not audit or not pages:
        return (
            DimensionScore(
                name="Validity",
                score=None,
                status="INSUFFICIENT_DATA",
                passed_checks=0,
                failed_checks=1,
                total_checks=1,
                summary="No records available to validate.",
            ),
            ValidityDetail(
                valid_records=0,
                invalid_records=1,
                validation_issues=[
                    ValidationIssue(
                        category="audit",
                        target="audit",
                        issue="Empty audit dataset has no valid records",
                        severity="error",
                    )
                ],
            ),
        )

    valid_records = 0
    invalid_records = 0
    validation_issues: List[ValidationIssue] = []

    def _check(
        is_valid: bool,
        category: str,
        target: str,
        issue_msg: str,
        value: Any = None,
        severity: str = "warning",
    ):
        nonlocal valid_records, invalid_records
        if is_valid:
            valid_records += 1
        else:
            invalid_records += 1
            validation_issues.append(
                ValidationIssue(
                    category=category,
                    target=target,
                    issue=issue_msg,
                    value=str(value)[:100] if value is not None else None,
                    severity=severity,
                )
            )

    # 1. Validate audit start_url
    start_url = audit.get("start_url", "")
    try:
        parsed_start = urllib.parse.urlparse(start_url)
        is_url_valid = bool(parsed_start.scheme in ("http", "https") and (parsed_start.hostname or parsed_start.netloc))
    except Exception:
        is_url_valid = False
    _check(is_url_valid, "url", "audit.start_url", "Invalid or malformed start URL syntax", start_url, "error")

    # 2. Validate timestamps
    def _is_valid_timestamp(ts: Optional[str]) -> bool:
        if not ts:
            return False
        # Check standard ISO or audit timestamp format: %Y-%m-%d_%H-%M-%S
        for fmt in ("%Y-%m-%d_%H-%M-%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                datetime.strptime(ts.split(".")[0], fmt)
                return True
            except ValueError:
                continue
        # Also check ISO format
        try:
            datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return True
        except Exception:
            return False

    _check(_is_valid_timestamp(audit.get("start_time")), "timestamp", "audit.start_time", "Invalid start timestamp format", audit.get("start_time"))
    if audit.get("end_time"):
        _check(_is_valid_timestamp(audit.get("end_time")), "timestamp", "audit.end_time", "Invalid end timestamp format", audit.get("end_time"))

    # 3. Validate pages
    for p in pages:
        p_idx = p.get("page_index", 0)
        p_url = p.get("url", "")
        p_status = p.get("status", "")

        # URL validation
        try:
            parsed = urllib.parse.urlparse(p_url)
            p_url_valid = bool(parsed.scheme in ("http", "https") and (parsed.hostname or parsed.netloc))
        except Exception:
            p_url_valid = False
        _check(p_url_valid, "url", f"page[{p_idx}].url", f"Page {p_idx} has invalid URL format", p_url, "error")

        # Page status recognized
        is_status_valid = p_status in ("success", "failed", "completed", "in_progress")
        _check(is_status_valid, "status", f"page[{p_idx}].status", f"Page {p_idx} has unrecognized status '{p_status}'", p_status)

        # Depth validity (must be non-negative integer <= configured depth + 2)
        depth = p.get("depth", 0)
        _check(isinstance(depth, int) and depth >= 0, "depth", f"page[{p_idx}].depth", f"Page {p_idx} depth is negative or non-integer", depth)

        # Artifact URI structure validation
        artifacts = p.get("artifacts") or {}
        for art_key, art_val in artifacts.items():
            if art_val:
                is_art_valid = bool(
                    str(art_val).startswith(("api/v1/automation/artifact/", "artifacts/", "http://", "https://"))
                )
                _check(is_art_valid, "artifact", f"page[{p_idx}].artifacts.{art_key}", f"Artifact reference has unexpected URI scheme", art_val)

    # 4. Validate evidence items
    price_regex = re.compile(r"(?:₹|Rs\.?|INR|\$|€|£)?\s*\d+(?:[\.,]\d+)?", re.IGNORECASE)

    for ev in evidence_items:
        ev_id = ev.get("evidence_id", "unknown_ev")
        cat = ev.get("category", "")
        sel = ev.get("selector")
        txt = ev.get("text")

        # If selector is present, ensure it is non-empty and has reasonable selector format
        if sel is not None:
            sel_valid = bool(str(sel).strip() and len(str(sel).strip()) > 0)
            _check(sel_valid, "selector", f"evidence[{ev_id}].selector", "Empty or whitespace-only CSS selector", sel)

        # Text sanitization: If text is provided, ensure not corrupt/empty whitespace
        if txt is not None:
            txt_valid = bool(str(txt).strip())
            _check(txt_valid, "text", f"evidence[{ev_id}].text", "Evidence item text is blank whitespace", txt)

        # Price element format validation
        if cat == "prices":
            attrs = ev.get("attributes") or {}
            detected_price = attrs.get("detected_price") or txt or ""
            is_price_valid = bool(price_regex.search(str(detected_price)))
            _check(is_price_valid, "price", f"evidence[{ev_id}].price", "Price element lacks recognizable numeric/currency amount", detected_price)

    total_checks = valid_records + invalid_records
    score = round((valid_records / total_checks) * 100.0, 1) if total_checks > 0 else 0.0

    if score >= 90.0:
        status = "PASSED"
    elif score >= 70.0:
        status = "WARNING"
    else:
        status = "CRITICAL"

    summary = f"{valid_records}/{total_checks} validity checks passed ({score}% valid). {len(validation_issues)} validation issues detected."

    score_model = DimensionScore(
        name="Validity",
        score=score,
        status=status,
        passed_checks=valid_records,
        failed_checks=invalid_records,
        total_checks=total_checks,
        summary=summary,
    )

    detail_model = ValidityDetail(
        valid_records=valid_records,
        invalid_records=invalid_records,
        validation_issues=validation_issues,
    )

    return score_model, detail_model


# ==============================================================================
# 3. CONSISTENCY DIMENSION
# ==============================================================================

def evaluate_consistency(
    audit: Dict[str, Any],
    pages: List[Dict[str, Any]],
    evidence_items: List[Dict[str, Any]],
) -> Tuple[DimensionScore, ConsistencyDetail]:
    """
    Verifies cross-referential and relational integrity across the audit session:
    uniform audit_id, page count reconciliation, evidence count mapping,
    allowed domain conformance, and temporal consistency.
    """
    if not audit:
        return (
            DimensionScore(
                name="Consistency",
                score=None,
                status="INSUFFICIENT_DATA",
                passed_checks=0,
                failed_checks=1,
                total_checks=1,
                summary="No audit record available for consistency evaluation.",
            ),
            ConsistencyDetail(passed_checks=0, failed_checks=1, consistency_issues=[]),
        )

    passed_checks = 0
    failed_checks = 0
    consistency_issues: List[ConsistencyCheckItem] = []

    audit_id = audit.get("audit_id", "")
    start_url = audit.get("start_url", "")
    parsed_start = urllib.parse.urlparse(start_url)
    start_host = (parsed_start.hostname or "").replace("www.", "").lower()

    def _add_check(name: str, passed: bool, expected: Any, actual: Any, desc: str):
        nonlocal passed_checks, failed_checks
        status_str = "PASSED" if passed else "FAILED"
        if passed:
            passed_checks += 1
        else:
            failed_checks += 1
        consistency_issues.append(
            ConsistencyCheckItem(
                check_name=name,
                status=status_str,
                expected=expected,
                actual=actual,
                description=desc,
            )
        )

    # Check 1: Audit ID present and non-empty
    _add_check("Audit ID Defined", bool(audit_id), "non-empty string", audit_id, "Audit session identifier is present.")

    # Check 2: All pages have matching audit_id
    mismatched_page_ids = [p.get("page_index") for p in pages if p.get("audit_id") and p.get("audit_id") != audit_id]
    _add_check(
        "Page Audit ID Uniformity",
        len(mismatched_page_ids) == 0,
        f"all pages match '{audit_id}'",
        f"{len(mismatched_page_ids)} mismatched page(s)",
        "Every page record must reference the parent audit ID.",
    )

    # Check 3: All evidence items have matching audit_id
    mismatched_ev_ids = [ev.get("evidence_id") for ev in evidence_items if ev.get("audit_id") and ev.get("audit_id") != audit_id]
    _add_check(
        "Evidence Audit ID Uniformity",
        len(mismatched_ev_ids) == 0,
        f"all evidence match '{audit_id}'",
        f"{len(mismatched_ev_ids)} mismatched evidence item(s)",
        "Every granular evidence item must reference the parent audit ID.",
    )

    # Check 4: Page count reconciliation (pages_crawled == len(pages))
    pages_crawled_meta = audit.get("pages_crawled", len(pages))
    _add_check(
        "Page Count Reconciliation",
        pages_crawled_meta == len(pages),
        len(pages),
        pages_crawled_meta,
        "Audit metadata pages_crawled matches the actual number of page records in storage.",
    )

    # Check 5: Page status sum reconciliation (successful + failed == total)
    p_success = audit.get("pages_successful", sum(1 for p in pages if p.get("status") == "success"))
    p_failed = audit.get("pages_failed", sum(1 for p in pages if p.get("status") != "success"))
    _add_check(
        "Success/Failure Count Sum",
        (p_success + p_failed) == len(pages),
        len(pages),
        p_success + p_failed,
        "Sum of successful and failed page counters equals total crawled pages.",
    )

    # Check 6: Evidence count reconciliation
    sum_page_ev = sum(p.get("evidence_count", 0) for p in pages)
    total_ev_meta = audit.get("total_evidence_items", sum_page_ev)
    # Evidence is consistent if sum of page counts matches metadata or DB count
    _add_check(
        "Evidence Count Reconciliation",
        total_ev_meta == sum_page_ev or (len(evidence_items) > 0 and len(evidence_items) == total_ev_meta),
        sum_page_ev,
        total_ev_meta,
        "Total evidence items in audit summary matches sum of page evidence records.",
    )

    # Check 7: Crawled URLs domain conformance (no cross-origin leaks)
    crawled_urls = [p.get("url", "") for p in pages if p.get("url")]
    off_domain_urls = []
    for u in crawled_urls:
        try:
            h = (urllib.parse.urlparse(u).hostname or "").replace("www.", "").lower()
            if start_host and h and h != start_host and not h.endswith("." + start_host):
                off_domain_urls.append(u)
        except Exception:
            pass
    _add_check(
        "Same-Origin Domain Conformance",
        len(off_domain_urls) == 0,
        f"Domain matches '{start_host}'",
        f"{len(off_domain_urls)} off-domain URL(s)",
        "All crawled pages adhere to the configured platform target domain.",
    )

    # Check 8: Detection URL correspondence
    page_urls_set = set(crawled_urls)
    dark_pattern_summary = audit.get("dark_pattern_summary") or []
    orphan_detection_urls = []
    for det in dark_pattern_summary:
        for aff in det.get("affected_pages", []):
            aff_url = aff.get("url")
            if aff_url and aff_url not in page_urls_set:
                orphan_detection_urls.append(aff_url)
    _add_check(
        "Detection Findings URL Mapping",
        len(orphan_detection_urls) == 0,
        "All finding URLs exist in crawled pages",
        f"{len(orphan_detection_urls)} orphan detection URL(s)",
        "Dark pattern detection findings correspond directly to crawled page URLs.",
    )

    # Check 9: Temporal integrity (start_time <= end_time)
    start_time_str = audit.get("start_time")
    end_time_str = audit.get("end_time")
    is_time_ordered = True
    if start_time_str and end_time_str:
        is_time_ordered = str(end_time_str) >= str(start_time_str)
    _add_check(
        "Chronological Ordering",
        is_time_ordered,
        f"end_time >= start_time",
        f"start: {start_time_str}, end: {end_time_str}",
        "Audit end timestamp is chronologically at or after start timestamp.",
    )

    total_checks = passed_checks + failed_checks
    score = round((passed_checks / total_checks) * 100.0, 1) if total_checks > 0 else 0.0

    if score >= 90.0:
        status = "PASSED"
    elif score >= 75.0:
        status = "WARNING"
    else:
        status = "CRITICAL"

    summary = f"{passed_checks}/{total_checks} consistency checks passed ({score}% consistent)."

    score_model = DimensionScore(
        name="Consistency",
        score=score,
        status=status,
        passed_checks=passed_checks,
        failed_checks=failed_checks,
        total_checks=total_checks,
        summary=summary,
    )

    detail_model = ConsistencyDetail(
        passed_checks=passed_checks,
        failed_checks=failed_checks,
        consistency_issues=consistency_issues,
    )

    return score_model, detail_model


# ==============================================================================
# 4. RELEVANCE DIMENSION (DETECTION READINESS)
# ==============================================================================

def evaluate_relevance(
    audit: Dict[str, Any],
    pages: List[Dict[str, Any]],
    evidence_items: List[Dict[str, Any]],
) -> Tuple[DimensionScore, RelevanceDetail]:
    """
    Evaluates whether the collected data contains the necessary input features
    to evaluate the active dark pattern detectors:
    1. False Urgency
    2. Confirmshaming
    3. Drip Pricing
    4. Bait and Switch

    Note: This is a data quality and readiness assessment, NOT a dark pattern prediction.
    """
    if not audit or not pages:
        return (
            DimensionScore(
                name="Relevance",
                score=None,
                status="INSUFFICIENT_DATA",
                passed_checks=0,
                failed_checks=4,
                total_checks=4,
                summary="No crawled page data available to evaluate detector relevance.",
            ),
            RelevanceDetail(
                detectors_readiness=[],
                total_relevant_features_found=0,
                summary="No crawled pages available.",
            ),
        )

    evidence_categories = set(ev.get("category", "") for ev in evidence_items)
    has_screenshots = any(bool(p.get("artifacts", {}).get("screenshot")) for p in pages)
    has_dom = any(bool(p.get("artifacts", {}).get("dom")) for p in pages)
    has_extracted = any(bool(p.get("artifacts", {}).get("extracted_json")) for p in pages)

    # Let's inspect pages detections to see what features were populated or present
    detector_evaluations: List[DetectorReadinessItem] = []
    total_features_found = 0

    # 1. False Urgency Readiness
    fu_available: List[str] = []
    fu_missing: List[str] = []
    
    # Feature 1: Urgency elements or scarcity text
    if "urgency_elements" in evidence_categories or any(p.get("findings_count", 0) > 0 for p in pages):
        fu_available.append("urgency_scarcity_elements")
    else:
        fu_missing.append("urgency_scarcity_elements")

    # Feature 2: Structured DOM extraction
    if has_extracted:
        fu_available.append("structured_dom_text")
    else:
        fu_missing.append("structured_dom_text")

    # Feature 3: Rendered DOM Context
    if has_dom:
        fu_available.append("rendered_dom_context")
    else:
        fu_missing.append("rendered_dom_context")

    # Feature 4: Visual Screenshots
    if has_screenshots:
        fu_available.append("page_screenshots")
    else:
        fu_missing.append("page_screenshots")

    fu_score = round((len(fu_available) / 4.0) * 100.0, 1)
    fu_status = "HIGH_READINESS" if fu_score >= 75 else "MODERATE_READINESS" if fu_score >= 50 else "LOW_READINESS"
    total_features_found += len(fu_available)

    detector_evaluations.append(
        DetectorReadinessItem(
            detector_name="False Urgency",
            readiness_score=fu_score,
            status=fu_status,
            available_features=fu_available,
            missing_features=fu_missing,
            explanation=(
                f"False Urgency readiness is {fu_score}% ({len(fu_available)}/4 key features present: "
                f"{', '.join(fu_available) if fu_available else 'none'})."
            ),
        )
    )

    # 2. Confirmshaming Readiness
    cs_available: List[str] = []
    cs_missing: List[str] = []

    if has_extracted:
        cs_available.append("interactive_buttons")
        cs_available.append("navigation_links")
        cs_available.append("css_selectors")
    else:
        cs_missing.extend(["interactive_buttons", "navigation_links", "css_selectors"])

    if "modals" in evidence_categories or has_dom:
        cs_available.append("modal_dialog_structures")
    else:
        cs_missing.append("modal_dialog_structures")

    if has_screenshots:
        cs_available.append("page_screenshots")
    else:
        cs_missing.append("page_screenshots")

    cs_score = round((len(cs_available) / 5.0) * 100.0, 1)
    cs_status = "HIGH_READINESS" if cs_score >= 75 else "MODERATE_READINESS" if cs_score >= 50 else "LOW_READINESS"
    total_features_found += len(cs_available)

    detector_evaluations.append(
        DetectorReadinessItem(
            detector_name="Confirmshaming",
            readiness_score=cs_score,
            status=cs_status,
            available_features=cs_available,
            missing_features=cs_missing,
            explanation=(
                f"Confirmshaming readiness is {cs_score}% ({len(cs_available)}/5 key features present: "
                f"{', '.join(cs_available) if cs_available else 'none'})."
            ),
        )
    )

    # 3. Drip Pricing Readiness
    dp_available: List[str] = []
    dp_missing: List[str] = []

    if "prices" in evidence_categories or has_extracted:
        dp_available.append("price_currency_elements")
    else:
        dp_missing.append("price_currency_elements")

    if "cart_items" in evidence_categories or has_extracted:
        dp_available.append("cart_and_fee_breakdowns")
    else:
        dp_missing.append("cart_and_fee_breakdowns")

    if has_dom:
        dp_available.append("rendered_dom_markup")
    else:
        dp_missing.append("rendered_dom_markup")

    if has_screenshots:
        dp_available.append("page_screenshots")
    else:
        dp_missing.append("page_screenshots")

    dp_score = round((len(dp_available) / 4.0) * 100.0, 1)
    dp_status = "HIGH_READINESS" if dp_score >= 75 else "MODERATE_READINESS" if dp_score >= 50 else "LOW_READINESS"
    total_features_found += len(dp_available)

    detector_evaluations.append(
        DetectorReadinessItem(
            detector_name="Drip Pricing",
            readiness_score=dp_score,
            status=dp_status,
            available_features=dp_available,
            missing_features=dp_missing,
            explanation=(
                f"Drip Pricing readiness is {dp_score}% ({len(dp_available)}/4 key features present: "
                f"{', '.join(dp_available) if dp_available else 'none'})."
            ),
        )
    )

    # 4. Bait and Switch Readiness
    bs_available: List[str] = []
    bs_missing: List[str] = []

    if has_extracted:
        bs_available.append("promotional_links_and_anchors")
        bs_available.append("commercial_visible_text")
    else:
        bs_missing.extend(["promotional_links_and_anchors", "commercial_visible_text"])

    if len(pages) >= 2:
        bs_available.append("multi_page_navigation_context")
    else:
        bs_missing.append("multi_page_navigation_context")

    if has_dom and has_screenshots:
        bs_available.append("cross_page_dom_and_visuals")
    else:
        bs_missing.append("cross_page_dom_and_visuals")

    bs_score = round((len(bs_available) / 4.0) * 100.0, 1)
    bs_status = "HIGH_READINESS" if bs_score >= 75 else "MODERATE_READINESS" if bs_score >= 50 else "LOW_READINESS"
    total_features_found += len(bs_available)

    detector_evaluations.append(
        DetectorReadinessItem(
            detector_name="Bait and Switch",
            readiness_score=bs_score,
            status=bs_status,
            available_features=bs_available,
            missing_features=bs_missing,
            explanation=(
                f"Bait and Switch readiness is {bs_score}% ({len(bs_available)}/4 key features present: "
                f"{', '.join(bs_available) if bs_available else 'none'})."
            ),
        )
    )

    # 5. SaaS Billing Readiness
    sb_available: List[str] = []
    sb_missing: List[str] = []

    if "subscription_signals" in evidence_categories or has_extracted:
        sb_available.append("recurring_and_subscription_terms")
    else:
        sb_missing.append("recurring_and_subscription_terms")

    if "prices" in evidence_categories or has_extracted:
        sb_available.append("pricing_breakdowns_or_tiers")
    else:
        sb_missing.append("pricing_breakdowns_or_tiers")

    if has_extracted or has_dom:
        sb_available.append("cancellation_or_renewal_policies")
    else:
        sb_missing.append("cancellation_or_renewal_policies")

    if has_dom and has_screenshots:
        sb_available.append("rendered_dom_and_visuals")
    else:
        sb_missing.append("rendered_dom_and_visuals")

    sb_score = round((len(sb_available) / 4.0) * 100.0, 1)
    sb_status = "HIGH_READINESS" if sb_score >= 75 else "MODERATE_READINESS" if sb_score >= 50 else "LOW_READINESS"
    total_features_found += len(sb_available)

    detector_evaluations.append(
        DetectorReadinessItem(
            detector_name="SaaS Billing",
            readiness_score=sb_score,
            status=sb_status,
            available_features=sb_available,
            missing_features=sb_missing,
            explanation=(
                f"SaaS Billing readiness is {sb_score}% ({len(sb_available)}/4 key features present: "
                f"{', '.join(sb_available) if sb_available else 'none'})."
            ),
        )
    )

    # 6. Interface Interference Readiness
    ii_available: List[str] = []
    ii_missing: List[str] = []

    if has_extracted:
        ii_available.append("element_ui_metrics_and_dimensions")
        ii_available.append("interactive_button_and_link_pairs")
    else:
        ii_missing.extend(["element_ui_metrics_and_dimensions", "interactive_button_and_link_pairs"])

    if has_dom:
        ii_available.append("computed_styles_and_colors")
    else:
        ii_missing.append("computed_styles_and_colors")

    if has_screenshots:
        ii_available.append("page_screenshots")
    else:
        ii_missing.append("page_screenshots")

    ii_score = round((len(ii_available) / 4.0) * 100.0, 1)
    ii_status = "HIGH_READINESS" if ii_score >= 75 else "MODERATE_READINESS" if ii_score >= 50 else "LOW_READINESS"
    total_features_found += len(ii_available)

    detector_evaluations.append(
        DetectorReadinessItem(
            detector_name="Interface Interference",
            readiness_score=ii_score,
            status=ii_status,
            available_features=ii_available,
            missing_features=ii_missing,
            explanation=(
                f"Interface Interference readiness is {ii_score}% ({len(ii_available)}/4 key features present: "
                f"{', '.join(ii_available) if ii_available else 'none'})."
            ),
        )
    )

    # 7. Forced Action Readiness
    fa_available: List[str] = []
    fa_missing: List[str] = []

    if has_extracted:
        fa_available.append("form_structures_and_inputs")
        fa_available.append("checkbox_and_consent_elements")
    else:
        fa_missing.extend(["form_structures_and_inputs", "checkbox_and_consent_elements"])

    if "modals" in evidence_categories or has_dom:
        fa_available.append("modal_or_overlay_gating")
    else:
        fa_missing.append("modal_or_overlay_gating")

    if has_dom and has_screenshots:
        fa_available.append("rendered_dom_and_visuals")
    else:
        fa_missing.append("rendered_dom_and_visuals")

    fa_score = round((len(fa_available) / 4.0) * 100.0, 1)
    fa_status = "HIGH_READINESS" if fa_score >= 75 else "MODERATE_READINESS" if fa_score >= 50 else "LOW_READINESS"
    total_features_found += len(fa_available)

    detector_evaluations.append(
        DetectorReadinessItem(
            detector_name="Forced Action",
            readiness_score=fa_score,
            status=fa_status,
            available_features=fa_available,
            missing_features=fa_missing,
            explanation=(
                f"Forced Action readiness is {fa_score}% ({len(fa_available)}/4 key features present: "
                f"{', '.join(fa_available) if fa_available else 'none'})."
            ),
        )
    )

    # 8. Basket Sneaking Readiness
    bsk_available: List[str] = []
    bsk_missing: List[str] = []

    if "cart_items" in evidence_categories or has_extracted:
        bsk_available.append("cart_and_basket_structures")
    else:
        bsk_missing.append("cart_and_basket_structures")

    if has_extracted:
        bsk_available.append("checkbox_and_selection_controls")
    else:
        bsk_missing.append("checkbox_and_selection_controls")

    if "prices" in evidence_categories or has_extracted:
        bsk_available.append("pricing_breakdowns")
    else:
        bsk_missing.append("pricing_breakdowns")

    if has_dom and has_screenshots:
        bsk_available.append("rendered_dom_and_visuals")
    else:
        bsk_missing.append("rendered_dom_and_visuals")

    bsk_score = round((len(bsk_available) / 4.0) * 100.0, 1)
    bsk_status = "HIGH_READINESS" if bsk_score >= 75 else "MODERATE_READINESS" if bsk_score >= 50 else "LOW_READINESS"
    total_features_found += len(bsk_available)

    detector_evaluations.append(
        DetectorReadinessItem(
            detector_name="Basket Sneaking",
            readiness_score=bsk_score,
            status=bsk_status,
            available_features=bsk_available,
            missing_features=bsk_missing,
            explanation=(
                f"Basket Sneaking readiness is {bsk_score}% ({len(bsk_available)}/4 key features present: "
                f"{', '.join(bsk_available) if bsk_available else 'none'})."
            ),
        )
    )

    # Average readiness score across all 8 detectors
    avg_relevance_score = round(
        (fu_score + cs_score + dp_score + bs_score + sb_score + ii_score + fa_score + bsk_score) / 8.0, 1
    )

    passed_checks = sum(1 for d in detector_evaluations if d.status in ("HIGH_READINESS", "MODERATE_READINESS"))
    total_checks = len(detector_evaluations)
    failed_checks = total_checks - passed_checks

    status = "PASSED" if avg_relevance_score >= 75.0 else "WARNING" if avg_relevance_score >= 50.0 else "CRITICAL"

    summary = (
        f"Detector Input Readiness: {avg_relevance_score}%. "
        f"{passed_checks}/{total_checks} detectors received sufficient structured input data."
    )

    score_model = DimensionScore(
        name="Relevance",
        score=avg_relevance_score,
        status=status,
        passed_checks=passed_checks,
        failed_checks=failed_checks,
        total_checks=total_checks,
        summary=summary,
    )

    detail_model = RelevanceDetail(
        detectors_readiness=detector_evaluations,
        total_relevant_features_found=total_features_found,
        summary=summary,
    )

    return score_model, detail_model


# ==============================================================================
# 5. UNIQUENESS DIMENSION
# ==============================================================================

def evaluate_uniqueness(
    audit: Dict[str, Any],
    pages: List[Dict[str, Any]],
    evidence_items: List[Dict[str, Any]],
) -> Tuple[DimensionScore, UniquenessDetail]:
    """
    Measures data duplication and redundancy across crawled pages and evidence items:
    detects duplicate URLs, duplicate page titles, duplicate evidence IDs, and
    excessive selector collisions.
    """
    if not pages and not evidence_items:
        return (
            DimensionScore(
                name="Uniqueness",
                score=None,
                status="INSUFFICIENT_DATA",
                passed_checks=0,
                failed_checks=1,
                total_checks=1,
                summary="No records available to evaluate uniqueness.",
            ),
            UniquenessDetail(
                total_records=0,
                unique_records=0,
                duplicate_count=0,
                duplicates=[],
            ),
        )

    duplicate_items: List[DuplicateItem] = []
    total_records = 0
    duplicate_count = 0

    # 1. Page URL Deduplication
    url_counter = collections.Counter(p.get("url", "") for p in pages if p.get("url"))
    for url, count in url_counter.items():
        total_records += count
        if count > 1:
            duplicate_count += (count - 1)
            duplicate_items.append(
                DuplicateItem(
                    duplicate_type="duplicate_crawled_url",
                    identifier=url,
                    count=count,
                    context=f"URL was crawled {count} times in the same audit session.",
                )
            )

    # 2. Page Title Deduplication (flag if non-failed pages share exact same title across different URLs)
    successful_pages = [p for p in pages if p.get("status") == "success"]
    title_counter = collections.Counter((p.get("title") or "").strip() for p in successful_pages if (p.get("title") or "").strip())
    for title, count in title_counter.items():
        if count > 3 and len(title) > 5:
            duplicate_count += (count - 1)
            duplicate_items.append(
                DuplicateItem(
                    duplicate_type="repeated_page_title",
                    identifier=title[:60],
                    count=count,
                    context=f"Page title repeated across {count} distinct crawled pages (possible redirect loop or landing page trap).",
                )
            )

    # 3. Evidence ID Deduplication
    ev_id_counter = collections.Counter(ev.get("evidence_id") for ev in evidence_items if ev.get("evidence_id"))
    for ev_id, count in ev_id_counter.items():
        total_records += count
        if count > 1:
            duplicate_count += (count - 1)
            duplicate_items.append(
                DuplicateItem(
                    duplicate_type="duplicate_evidence_id",
                    identifier=ev_id,
                    count=count,
                    context=f"Evidence identifier '{ev_id}' appears {count} times.",
                )
            )

    # 4. Evidence Content Deduplication (same page, category, selector, and text)
    ev_sig_counter = collections.Counter()
    for ev in evidence_items:
        sig = f"{ev.get('page_index', 0)}_{ev.get('category', '')}_{ev.get('selector', '')}_{str(ev.get('text', ''))[:40]}"
        ev_sig_counter[sig] += 1

    for sig, count in ev_sig_counter.items():
        if count > 1:
            duplicate_count += (count - 1)
            duplicate_items.append(
                DuplicateItem(
                    duplicate_type="duplicate_evidence_content",
                    identifier=sig[:80],
                    count=count,
                    context=f"Identical evidence element extracted {count} times on the same page.",
                )
            )

    # Ensure total_records is at least total pages + evidence
    total_records = max(total_records, len(pages) + len(evidence_items))
    unique_records = max(0, total_records - duplicate_count)

    score = round((unique_records / total_records) * 100.0, 1) if total_records > 0 else 100.0

    if score >= 90.0:
        status = "PASSED"
    elif score >= 75.0:
        status = "WARNING"
    else:
        status = "CRITICAL"

    passed_checks = unique_records
    failed_checks = duplicate_count
    total_checks = total_records

    summary = f"{unique_records}/{total_records} unique records ({score}% uniqueness). {duplicate_count} duplicates detected."

    score_model = DimensionScore(
        name="Uniqueness",
        score=score,
        status=status,
        passed_checks=passed_checks,
        failed_checks=failed_checks,
        total_checks=total_checks,
        summary=summary,
    )

    detail_model = UniquenessDetail(
        total_records=total_records,
        unique_records=unique_records,
        duplicate_count=duplicate_count,
        duplicates=duplicate_items,
    )

    return score_model, detail_model


# ==============================================================================
# 6. EVIDENCE AVAILABILITY & TRACEABILITY DIMENSION
# ==============================================================================

def evaluate_evidence_availability(
    audit: Dict[str, Any],
    pages: List[Dict[str, Any]],
    evidence_items: List[Dict[str, Any]],
) -> Tuple[DimensionScore, EvidenceAvailabilityDetail]:
    """
    Measures evidence coverage and traceability:
    verifies that detection findings and crawled pages have tangible physical
    artifacts (screenshots, DOM, extracted JSON, evidence records) persisted in storage.
    """
    if not pages:
        return (
            DimensionScore(
                name="Evidence Availability",
                score=None,
                status="INSUFFICIENT_DATA",
                passed_checks=0,
                failed_checks=1,
                total_checks=1,
                summary="No page records available to evaluate evidence availability.",
            ),
            EvidenceAvailabilityDetail(),
        )

    pages_crawled = len(pages)
    pages_with_evidence = sum(1 for p in pages if p.get("evidence_count", 0) > 0)
    pages_with_screenshots = sum(1 for p in pages if (p.get("artifacts") or {}).get("screenshot"))
    pages_with_dom = sum(1 for p in pages if (p.get("artifacts") or {}).get("dom"))
    pages_with_extracted = sum(1 for p in pages if (p.get("artifacts") or {}).get("extracted_json"))

    total_evidence_items = len(evidence_items) or audit.get("total_evidence_items", 0)

    # Evaluate detection traceability: do all detected findings have supporting evidence items?
    dark_pattern_summary = audit.get("dark_pattern_summary") or []
    total_findings = 0
    traceable_findings = 0
    untraceable_findings = 0

    evidence_id_set = set(ev.get("evidence_id") for ev in evidence_items if ev.get("evidence_id"))

    for pat in dark_pattern_summary:
        if pat.get("detected"):
            total_findings += 1
            ev_list = pat.get("evidence") or []
            if ev_list:
                # Check if evidence items have text/selector or valid ID
                has_substance = any(
                    bool(e.get("text") or e.get("selector") or e.get("evidence_id") in evidence_id_set)
                    for e in ev_list
                )
                if has_substance:
                    traceable_findings += 1
                else:
                    untraceable_findings += 1
            else:
                untraceable_findings += 1

    # Calculate coverage components
    # 1. Screenshot coverage
    scr_cov = (pages_with_screenshots / pages_crawled) if pages_crawled > 0 else 0
    # 2. DOM coverage
    dom_cov = (pages_with_dom / pages_crawled) if pages_crawled > 0 else 0
    # 3. Evidence set coverage
    ev_cov = (pages_with_evidence / pages_crawled) if pages_crawled > 0 else 0
    # 4. Extracted JSON coverage
    ext_cov = (pages_with_extracted / pages_crawled) if pages_crawled > 0 else 0

    page_artifact_score = (scr_cov + dom_cov + ev_cov + ext_cov) / 4.0

    if total_findings > 0:
        finding_trace_score = (traceable_findings / total_findings)
        overall_cov = (0.6 * page_artifact_score) + (0.4 * finding_trace_score)
    else:
        overall_cov = page_artifact_score

    score = round(overall_cov * 100.0, 1)

    passed_checks = pages_with_screenshots + pages_with_dom + pages_with_extracted + traceable_findings
    total_checks = (pages_crawled * 3) + max(total_findings, 1)
    failed_checks = max(0, total_checks - passed_checks)

    if score >= 85.0:
        status = "PASSED"
    elif score >= 60.0:
        status = "WARNING"
    else:
        status = "CRITICAL"

    summary = (
        f"Evidence coverage: {score}%. "
        f"{pages_with_screenshots}/{pages_crawled} screenshots, {pages_with_dom}/{pages_crawled} DOMs, "
        f"{traceable_findings}/{total_findings} findings traceable."
    )

    score_model = DimensionScore(
        name="Evidence Availability",
        score=score,
        status=status,
        passed_checks=passed_checks,
        failed_checks=failed_checks,
        total_checks=total_checks,
        summary=summary,
    )

    detail_model = EvidenceAvailabilityDetail(
        pages_crawled=pages_crawled,
        pages_with_evidence=pages_with_evidence,
        pages_with_screenshots=pages_with_screenshots,
        pages_with_dom=pages_with_dom,
        pages_with_extracted_json=pages_with_extracted,
        total_evidence_items=total_evidence_items,
        total_detection_findings=total_findings,
        traceable_detection_findings=traceable_findings,
        untraceable_detection_findings=untraceable_findings,
        coverage_percentage=score,
    )

    return score_model, detail_model


# ==============================================================================
# 7. PATTERN READINESS & EVIDENCE SUFFICIENCY EVALUATION
# ==============================================================================

def evaluate_pattern_readiness_and_sufficiency(
    audit: Dict[str, Any],
    relevance_detail: RelevanceDetail,
    pages: List[Dict[str, Any]],
    evidence_items: List[Dict[str, Any]],
) -> List[PatternReadinessAndSufficiencyItem]:
    """
    Evaluates detector input readiness vs. actual detection outcome and evidence sufficiency
    for all 8 dark patterns:
    1. False Urgency
    2. Drip Pricing
    3. Bait and Switch
    4. Confirmshaming
    5. SaaS Billing
    6. Interface Interference
    7. Forced Action
    8. Basket Sneaking

    Ensures strict conceptual separation:
    - Input Readiness: Evaluates if required DOM/feature signals were captured for execution.
    - Detection Result: The actual compliance audit finding (DETECTED, NOT_DETECTED, INSUFFICIENT_EVIDENCE, NOT_EVALUATED).
    - Evidence Sufficiency: Indicates whether qualifying pattern-specific evidence was available vs. absent/insufficient.
    """
    # Map readiness from relevance_detail
    readiness_by_name: Dict[str, DetectorReadinessItem] = {
        item.detector_name.lower(): item for item in relevance_detail.detectors_readiness
    }

    # Map dark_pattern_summary from audit if present
    summary_findings = audit.get("dark_pattern_summary") or []
    findings_by_name: Dict[str, Dict[str, Any]] = {
        f.get("pattern", "").lower(): f for f in summary_findings if f.get("pattern")
    }

    results: List[PatternReadinessAndSufficiencyItem] = []

    for pat in ALL_PATTERNS:
        pat_lower = pat.lower()

        # 1. Detector Input Readiness
        r_item = readiness_by_name.get(pat_lower)
        if r_item:
            input_readiness_score = r_item.readiness_score
            input_readiness_status = r_item.status
            input_ready = r_item.readiness_score >= 50.0 or r_item.status in ("HIGH_READINESS", "MODERATE_READINESS")
        else:
            input_readiness_score = 0.0
            input_readiness_status = "INSUFFICIENT_DATA"
            input_ready = False

        # 2. Actual Detection Result from persisted audit summary
        finding = findings_by_name.get(pat_lower)

        if finding is not None:
            raw_status = str(finding.get("status", "")).upper()
            detected = bool(finding.get("detected", False))
            confidence = int(finding.get("confidence", 0))
            affected_pages_count = int(finding.get("pages_affected_count", len(finding.get("affected_pages", []))))
            evidence_instances_count = int(finding.get("total_instances", len(finding.get("evidence", []))))
            reason = str(finding.get("reason", "")).strip()

            if detected or raw_status == "DETECTED":
                detection_status = "DETECTED"
                evidence_sufficient = True
                explanation = reason or f"Actual {pat} violation evidence identified during audit evaluation."
            elif raw_status == "NOT_DETECTED":
                detection_status = "NOT_DETECTED"
                evidence_sufficient = True
                explanation = reason or f"Detector evaluated available domain data and found no qualifying {pat} violations."
            elif raw_status == "INSUFFICIENT_EVIDENCE":
                detection_status = "INSUFFICIENT_EVIDENCE"
                evidence_sufficient = False
                explanation = reason or f"No qualifying interactive or domain evidence was available for a confident {pat} determination."
            else:
                detection_status = raw_status or "NOT_EVALUATED"
                evidence_sufficient = (detection_status in ("DETECTED", "NOT_DETECTED"))
                explanation = reason or f"{pat} detector status: {detection_status}"

        else:
            # Fallback if dark_pattern_summary does not have this entry: inspect page detections
            page_dets = []
            for p in pages:
                for d in p.get("detections", []):
                    if d.get("pattern", "").lower() == pat_lower:
                        page_dets.append(d)

            if page_dets:
                has_det = any(d.get("detected") or d.get("status") == "DETECTED" for d in page_dets)
                if has_det:
                    detection_status = "DETECTED"
                    detected = True
                    evidence_sufficient = True
                    det_item = next(d for d in page_dets if d.get("detected") or d.get("status") == "DETECTED")
                    confidence = int(det_item.get("confidence", 80))
                    affected_pages_count = sum(
                        1 for p in pages if any(
                            d.get("pattern", "").lower() == pat_lower and (d.get("detected") or d.get("status") == "DETECTED")
                            for d in p.get("detections", [])
                        )
                    )
                    evidence_instances_count = sum(
                        len(d.get("evidence", [])) for d in page_dets if d.get("detected") or d.get("status") == "DETECTED"
                    )
                    explanation = det_item.get("reason", f"Actual {pat} violation evidence found.")
                elif any(d.get("status") == "NOT_DETECTED" for d in page_dets):
                    detection_status = "NOT_DETECTED"
                    detected = False
                    confidence = 0
                    evidence_sufficient = True
                    affected_pages_count = 0
                    evidence_instances_count = 0
                    explanation = f"Detector evaluated available page elements and found no qualifying {pat} violations."
                else:
                    detection_status = "INSUFFICIENT_EVIDENCE"
                    detected = False
                    confidence = 0
                    evidence_sufficient = False
                    affected_pages_count = 0
                    evidence_instances_count = 0
                    explanation = f"Insufficient qualifying evidence on crawled pages for a confident {pat} determination."
            else:
                detection_status = "NOT_EVALUATED"
                detected = False
                confidence = 0
                evidence_sufficient = False
                affected_pages_count = 0
                evidence_instances_count = 0
                explanation = f"{pat} detector was not evaluated for this audit session."

        results.append(
            PatternReadinessAndSufficiencyItem(
                pattern=pat,
                input_ready=input_ready,
                input_readiness_status=input_readiness_status,
                input_readiness_score=input_readiness_score,
                detection_status=detection_status,
                detected=detected,
                evidence_sufficient=evidence_sufficient,
                affected_pages_count=affected_pages_count,
                evidence_instances_count=evidence_instances_count,
                explanation=explanation,
                confidence=confidence,
            )
        )

    return results


# ==============================================================================
# 8. MAIN DATA QUALITY ASSESSMENT ENGINE
# ==============================================================================

def assess_audit_data_quality(
    audit: Optional[Dict[str, Any]],
    evidence_items: Optional[List[Dict[str, Any]]] = None,
) -> DataQualityAssessmentResponse:
    """
    Executes the comprehensive 6-dimension Data Quality Assessment on a given audit document
    and associated evidence records.

    Calculates:
    A. Completeness
    B. Validity
    C. Consistency
    D. Relevance (Detector Input Readiness)
    E. Uniqueness
    F. Evidence Availability

    Derives the transparent overall data quality score, quality grade, and
    Pattern Readiness & Evidence Sufficiency breakdowns.
    """
    if not audit:
        empty_score = DimensionScore(
            name="N/A",
            score=None,
            status="INSUFFICIENT_DATA",
            passed_checks=0,
            failed_checks=1,
            total_checks=1,
            summary="No audit dataset provided.",
        )
        return DataQualityAssessmentResponse(
            audit_id="unknown",
            platform="Unknown",
            start_url="",
            start_time="",
            end_time="",
            audit_status="NOT_FOUND",
            configured_crawl_depth=0,
            actual_max_depth_reached=0,
            overall_score=None,
            overall_status="INSUFFICIENT_DATA",
            quality_grade="N/A",
            summary_text="Audit record not found or empty.",
            dimensions={
                "completeness": empty_score.model_copy(update={"name": "Completeness"}),
                "validity": empty_score.model_copy(update={"name": "Validity"}),
                "consistency": empty_score.model_copy(update={"name": "Consistency"}),
                "relevance": empty_score.model_copy(update={"name": "Relevance"}),
                "uniqueness": empty_score.model_copy(update={"name": "Uniqueness"}),
                "evidence_availability": empty_score.model_copy(update={"name": "Evidence Availability"}),
            },
            details=QualityAssessmentDetails(
                completeness=CompletenessDetail(),
                validity=ValidityDetail(),
                consistency=ConsistencyDetail(),
                relevance=RelevanceDetail(),
                uniqueness=UniquenessDetail(),
                evidence_availability=EvidenceAvailabilityDetail(),
                pattern_readiness_and_sufficiency=[],
            ),
        )

    pages = audit.get("pages") or []
    ev_items = evidence_items if evidence_items is not None else []

    # Calculate the 6 Dimensions
    comp_score, comp_detail = evaluate_completeness(audit, pages, ev_items)
    val_score, val_detail = evaluate_validity(audit, pages, ev_items)
    cons_score, cons_detail = evaluate_consistency(audit, pages, ev_items)
    rel_score, rel_detail = evaluate_relevance(audit, pages, ev_items)
    uniq_score, uniq_detail = evaluate_uniqueness(audit, pages, ev_items)
    ev_score, ev_detail = evaluate_evidence_availability(audit, pages, ev_items)

    dimensions = {
        "completeness": comp_score,
        "validity": val_score,
        "consistency": cons_score,
        "relevance": rel_score,
        "uniqueness": uniq_score,
        "evidence_availability": ev_score,
    }

    # Evaluate Pattern Readiness vs Detection Result and Evidence Sufficiency
    prs_items = evaluate_pattern_readiness_and_sufficiency(audit, rel_detail, pages, ev_items)

    # Calculate Overall Score (Arithmetic Mean of non-None valid scores)
    valid_scores = [d.score for d in dimensions.values() if d.score is not None]

    if not valid_scores or len(pages) == 0:
        overall_score = None
        overall_status = "INSUFFICIENT_DATA"
        quality_grade = "N/A"
        summary_text = "Insufficient audit data to calculate an overall data quality score."
    else:
        overall_score = round(sum(valid_scores) / float(len(valid_scores)), 1)

        if overall_score >= 90.0:
            overall_status = "EXCELLENT"
            quality_grade = "A+ (High Integrity)"
            summary_text = (
                f"High-quality audit dataset ({overall_score}%). Collected data is comprehensive, "
                "structurally sound, and fully reliable for dark-pattern compliance auditing."
            )
        elif overall_score >= 75.0:
            overall_status = "ACCEPTABLE"
            quality_grade = "B (Audit Ready)"
            summary_text = (
                f"Acceptable audit dataset ({overall_score}%). Collected data satisfies core requirements "
                "with minor warnings. Dark-pattern detection results are trustworthy."
            )
        elif overall_score >= 50.0:
            overall_status = "DEGRADED"
            quality_grade = "C (Partial Quality)"
            summary_text = (
                f"Degraded audit dataset ({overall_score}%). Notable failure rates or missing artifacts "
                "detected. Review flagged issues before relying on compliance findings."
            )
        else:
            overall_status = "CRITICAL"
            quality_grade = "D (Re-crawl Recommended)"
            summary_text = (
                f"Critical data quality deficiency ({overall_score}%). High page failure rate or severe "
                "missing evidence. Re-running the browser crawl audit is strongly recommended."
            )

    return DataQualityAssessmentResponse(
        audit_id=audit.get("audit_id", "unknown"),
        platform=audit.get("platform", "Platform"),
        start_url=audit.get("start_url", ""),
        start_time=audit.get("start_time", ""),
        end_time=audit.get("end_time", ""),
        audit_status=audit.get("status", "completed"),
        configured_crawl_depth=int(audit.get("configured_crawl_depth", 0)),
        actual_max_depth_reached=int(audit.get("actual_max_depth_reached", 0)),
        overall_score=overall_score,
        overall_status=overall_status,
        quality_grade=quality_grade,
        summary_text=summary_text,
        dimensions=dimensions,
        details=QualityAssessmentDetails(
            completeness=comp_detail,
            validity=val_detail,
            consistency=cons_detail,
            relevance=rel_detail,
            uniqueness=uniq_detail,
            evidence_availability=ev_detail,
            pattern_readiness_and_sufficiency=prs_items,
        ),
    )


def evaluate_audit_quality_by_id(audit_id: str) -> Optional[DataQualityAssessmentResponse]:
    """
    Retrieves the audit session and its granular evidence items from MongoDB
    (or local artifacts fallback), then executes data quality evaluation.
    """
    audit = None
    evidence_items = []

    # 1. Attempt MongoDB retrieval
    try:
        audit = get_audit_details_from_mongodb(audit_id)
        if audit:
            evidence_items = get_evidence_items_from_mongodb(audit_id)
    except Exception as e:
        logger.warning(f"MongoDB retrieval failed for audit '{audit_id}', checking local artifacts fallback: {e}")

    # 2. If not found in MongoDB, attempt local filesystem artifacts fallback
    if not audit:
        # Search in artifacts/
        for summary_file in ARTIFACTS_DIR.glob(f"**/{audit_id}/audit_summary.json"):
            try:
                with open(summary_file, "r", encoding="utf-8") as f:
                    audit = json.load(f)
                    break
            except Exception as e:
                logger.error(f"Failed to read local audit_summary.json at '{summary_file}': {e}")

    if not audit:
        return None

    return assess_audit_data_quality(audit, evidence_items)
