import logging
import re
from typing import Any, Dict, List

from app.models.detection_model import ALL_PATTERNS
from app.services.dark_patterns.bait_and_switch_detector import BaitAndSwitchDetector
from app.services.dark_patterns.basket_sneaking_detector import BasketSneakingDetector
from app.services.dark_patterns.confirmshaming_detector import ConfirmshamingDetector
from app.services.dark_patterns.drip_pricing_detector import DripPricingDetector
from app.services.dark_patterns.false_urgency_detector import FalseUrgencyDetector
from app.services.dark_patterns.forced_action_detector import ForcedActionDetector
from app.services.dark_patterns.interface_interference_detector import InterfaceInterferenceDetector
from app.services.dark_patterns.saas_billing_detector import SaaSBillingDetector

logger = logging.getLogger(__name__)

# Register all 8 active dark pattern detectors
ACTIVE_DETECTORS = [
    FalseUrgencyDetector(),
    DripPricingDetector(),
    BaitAndSwitchDetector(),
    ConfirmshamingDetector(),
    SaaSBillingDetector(),
    InterfaceInterferenceDetector(),
    ForcedActionDetector(),
    BasketSneakingDetector(),
]


def run_dark_pattern_detection(
    extracted_data: Dict[str, Any],
    evidence_record: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Executes the 8 dark pattern detectors on the extracted DOM data
    and linked evidence record for a single crawled page.

    Returns a list of structured detection findings.
    """
    results: List[Dict[str, Any]] = []

    for detector in ACTIVE_DETECTORS:
        try:
            finding = detector.detect(extracted_data, evidence_record)
            results.append(finding.model_dump())
        except Exception as e:
            logger.error(
                f"Error executing detector '{detector.pattern_name}': {e}",
                exc_info=True
            )
            results.append({
                "pattern": detector.pattern_name,
                "status": "INSUFFICIENT_EVIDENCE",
                "detected": False,
                "confidence": 0,
                "reason": f"Detector execution encountered an unexpected error: {str(e)}",
                "page_url": extracted_data.get("url", ""),
                "evidence": [],
                "metadata": {"error": True}
            })

    return results


def deduplicate_evidence_instances(evidence_list: List[Dict[str, Any]]) -> int:
    """
    Deduplicates nested DOM elements sharing identical text or selectors on the same page.
    """
    if not evidence_list:
        return 0

    seen_text_signatures = set()
    unique_count = 0

    for ev in evidence_list:
        raw_text = (ev.get("text") or "").strip().lower()
        norm_text = re.sub(r"\s+", " ", raw_text)
        if not norm_text:
            unique_count += 1
            continue

        is_subsumed = False
        for seen in seen_text_signatures:
            if norm_text == seen or (len(norm_text) > 8 and norm_text in seen) or (len(seen) > 8 and seen in norm_text):
                is_subsumed = True
                break

        if not is_subsumed:
            seen_text_signatures.add(norm_text)
            unique_count += 1

    return max(unique_count, 1)


def aggregate_detection_findings(
    page_records: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Aggregates dark pattern findings across all crawled pages in an audit
    for all 8 Dark Patterns:
    1. False Urgency
    2. Drip Pricing
    3. Bait and Switch
    4. Confirmshaming
    5. SaaS Billing
    6. Interface Interference
    7. Forced Action
    8. Basket Sneaking
    """
    aggregated: List[Dict[str, Any]] = []

    pattern_data: Dict[str, Dict[str, Any]] = {
        pat: {
            "status": "NOT_DETECTED",
            "detected": False,
            "max_confidence": 0,
            "affected_pages": [],
            "all_evidence": [],
            "reasons": [],
            "detected_count": 0,
            "not_detected_count": 0,
            "insufficient_count": 0,
        }
        for pat in ALL_PATTERNS
    }

    for page in page_records:
        page_idx = page.get("page_index", 0)
        page_url = page.get("url", "")
        page_depth = page.get("depth", 0)
        page_detections = page.get("detections", [])

        for det in page_detections:
            pat_name = det.get("pattern", "")
            if pat_name not in pattern_data:
                continue

            entry = pattern_data[pat_name]
            det_status = det.get("status", "DETECTED" if det.get("detected") else "NOT_DETECTED")

            if det_status == "DETECTED" or det.get("detected", False):
                entry["detected"] = True
                entry["status"] = "DETECTED"
                entry["detected_count"] += 1
                conf = det.get("confidence", 0)
                if conf > entry["max_confidence"]:
                    entry["max_confidence"] = conf

                ev_items = det.get("evidence", [])
                entry["all_evidence"].extend(ev_items)
                entry["reasons"].append(det.get("reason", ""))

                entry["affected_pages"].append({
                    "page_index": page_idx,
                    "url": page_url,
                    "depth": page_depth,
                    "evidence_count": len(ev_items)
                })

            elif det_status == "NOT_DETECTED":
                entry["not_detected_count"] += 1
                entry["reasons"].append(det.get("reason", ""))

            elif det_status in ("INSUFFICIENT_EVIDENCE", "NOT_EVALUATED"):
                entry["insufficient_count"] += 1
                entry["reasons"].append(det.get("reason", ""))

    # Build final aggregated finding for each of the 8 patterns
    for pat in ALL_PATTERNS:
        entry = pattern_data[pat]
        affected_pages = entry["affected_pages"]
        all_ev = entry["all_evidence"]
        max_conf = entry["max_confidence"]

        if entry["detected"]:
            total_instances = deduplicate_evidence_instances(all_ev)
            affected_count = len(affected_pages)
            aggregated.append({
                "pattern": pat,
                "status": "DETECTED",
                "detected": True,
                "confidence": max_conf,
                "pages_affected_count": affected_count,
                "affected_pages": affected_pages,
                "total_instances": total_instances,
                "reason": (
                    f"Potential {pat} detected across {affected_count} page(s) "
                    f"({total_instances} unique instance(s) found with {len(all_ev)} traceable evidence items)."
                ),
                "evidence": all_ev
            })

        elif entry["not_detected_count"] > 0:
            reasons = {
                "False Urgency": "No dynamic countdown timers or artificial scarcity pressure detected across crawled pages.",
                "Drip Pricing": "Price disclosures appear upfront; no undisclosed mandatory fees or unexpected surcharges detected.",
                "Bait and Switch": "Advertised offers, link descriptions, and product terms appear consistent across pages.",
                "Confirmshaming": "Decline and opt-out buttons use neutral, non-manipulative phrasing.",
                "SaaS Billing": "Subscription terms, billing frequency, and cancellation policies appear transparent without hidden auto-renewals or obstructive barriers.",
                "Interface Interference": "Interface choices, button sizes, and visual hierarchies appear balanced without deceptive visual suppression.",
                "Forced Action": "Form requirements and user interactions appear voluntary and strictly relevant to requested functionality.",
                "Basket Sneaking": "Cart and checkout data evaluated; no preselected add-on items, automatic warranties, donations, or unsolicited fees found.",
            }
            aggregated.append({
                "pattern": pat,
                "status": "NOT_DETECTED",
                "detected": False,
                "confidence": 0,
                "pages_affected_count": 0,
                "affected_pages": [],
                "total_instances": 0,
                "reason": reasons.get(pat, f"No evidence of {pat} found across crawled pages."),
                "evidence": []
            })

        else:
            # Insufficient Evidence
            reasons = {
                "False Urgency": "No urgency or time-sensitive elements present on crawled pages.",
                "Drip Pricing": "Insufficient pricing or checkout breakdown data present across crawled pages to evaluate Drip Pricing.",
                "Bait and Switch": "Insufficient cross-page promotional comparison data to evaluate Bait and Switch.",
                "Confirmshaming": "No interactive opt-out or decline modal elements found on crawled pages.",
                "SaaS Billing": "No subscription plans, recurring billing terms, or pricing controls found on crawled pages to evaluate SaaS Billing.",
                "Interface Interference": "No comparative interactive controls or paired choice elements present on crawled pages to evaluate Interface Interference.",
                "Forced Action": "No interactive forms, required checkboxes, or modal gating elements found on crawled pages to evaluate Forced Action.",
                "Basket Sneaking": "Insufficient cart or checkout interaction data present across crawled pages to evaluate Basket Sneaking.",
            }
            aggregated.append({
                "pattern": pat,
                "status": "INSUFFICIENT_EVIDENCE",
                "detected": False,
                "confidence": 0,
                "pages_affected_count": 0,
                "affected_pages": [],
                "total_instances": 0,
                "reason": reasons.get(pat, f"Insufficient evidence to evaluate {pat} on crawled pages."),
                "evidence": []
            })

    return aggregated

