import re
from typing import Any, Dict, List, Optional

from app.models.detection_model import DetectionEvidenceRef, DetectionFinding
from app.services.dark_patterns.base_detector import BaseDetector


class BaitAndSwitchDetector(BaseDetector):
    """
    Detector for Bait and Switch dark pattern.

    Identifies when an advertised offer, product, or headline condition materially
    differs from the actual product, price, or terms delivered on the destination page
    or within the same shopping context.
    """

    @property
    def pattern_name(self) -> str:
        return "Bait and Switch"

    # Patterns indicating coercive switch / mismatch
    SWITCH_PATTERNS = [
        r"\bitem\s+unavailable,?\s+view\s+similar\s+(?:at|for)\b",
        r"\bout\s+of\s+stock,?\s+switch\s+to\b",
        r"\bpromotional\s+offer\s+replaced\b",
        r"\badvertised\s+price\s+no\s+longer\s+valid\b",
        r"\bprice\s+changed\s+after\s+selection\b",
    ]

    def _find_matching_evidence(
        self,
        evidence_record: Dict[str, Any],
        selector: Optional[str] = None,
        text_snippet: Optional[str] = None,
    ) -> Optional[DetectionEvidenceRef]:
        """Finds corresponding Module 4 EvidenceItem in the evidence record."""
        items = evidence_record.get("evidence_items", [])
        for item in items:
            if item.get("category") in ("links", "visible_text", "prices", "buttons"):
                if selector and item.get("selector") == selector:
                    return DetectionEvidenceRef(
                        evidence_id=item.get("evidence_id", ""),
                        evidence_type=item.get("evidence_type", "extracted_data"),
                        category=item.get("category", "links"),
                        selector=item.get("selector"),
                        text=item.get("text"),
                        tag=item.get("tag"),
                        artifact_path=item.get("artifact_path", ""),
                        context=item.get("context"),
                    )
                if text_snippet and text_snippet in (item.get("text") or ""):
                    return DetectionEvidenceRef(
                        evidence_id=item.get("evidence_id", ""),
                        evidence_type=item.get("evidence_type", "extracted_data"),
                        category=item.get("category", "links"),
                        selector=item.get("selector"),
                        text=item.get("text"),
                        tag=item.get("tag"),
                        artifact_path=item.get("artifact_path", ""),
                        context=item.get("context"),
                    )
        return None

    def detect(
        self,
        extracted_data: Dict[str, Any],
        evidence_record: Dict[str, Any]
    ) -> DetectionFinding:
        page_url = extracted_data.get("url") or evidence_record.get("page_url", "")
        links = extracted_data.get("links", [])
        visible_text = extracted_data.get("visible_text", [])
        prices = extracted_data.get("prices", [])

        # If page has virtually no commercial content, return INSUFFICIENT_EVIDENCE
        if not links and not visible_text and not prices:
            return DetectionFinding(
                pattern=self.pattern_name,
                status="INSUFFICIENT_EVIDENCE",
                detected=False,
                confidence=0,
                reason="Insufficient page content and link data to evaluate Bait and Switch.",
                page_url=page_url,
                evidence=[],
                metadata={"reason_code": "NO_CONTENT"}
            )

        flagged_items: List[Dict[str, Any]] = []
        matched_evidence: List[DetectionEvidenceRef] = []

        # 1. Check for explicit switch messaging
        for t_item in visible_text:
            txt = t_item.get("text", "")
            for pattern in self.SWITCH_PATTERNS:
                if re.search(pattern, txt, re.IGNORECASE):
                    flagged_items.append({
                        "text": txt[:100],
                        "selector": t_item.get("selector"),
                        "confidence": 85,
                        "type": "coercive_switch_message"
                    })
                    ev_ref = self._find_matching_evidence(evidence_record, text_snippet=txt[:50])
                    if ev_ref:
                        matched_evidence.append(ev_ref)

        # 2. Check for advertised free/cheap link promises vs price discrepancies
        # Example: Link text promises "Get Free Trial / 100% Free" but surrounding/destination text requires immediate non-zero payment
        for l_item in links:
            l_text = (l_item.get("text") or "").lower().strip()
            if re.search(r"\b(?:100%\s+free|free\s+download|get\s+free)\b", l_text):
                # Check if same container or page requires paid purchase without free tier
                if any(p.get("detected_price") and not "0" in p.get("detected_price", "") for p in prices[:3]):
                    flagged_items.append({
                        "text": f"Link advertised '{l_text}' alongside paid product terms",
                        "selector": l_item.get("selector"),
                        "confidence": 80,
                        "type": "free_vs_paid_mismatch"
                    })
                    ev_ref = self._find_matching_evidence(evidence_record, selector=l_item.get("selector"))
                    if ev_ref:
                        matched_evidence.append(ev_ref)

        if flagged_items:
            sample = flagged_items[0]["text"]
            max_conf = max(f["confidence"] for f in flagged_items)
            return DetectionFinding(
                pattern=self.pattern_name,
                status="DETECTED",
                detected=True,
                confidence=max_conf,
                reason=(
                    f"Potential Bait and Switch detected: {len(flagged_items)} material discrepancy "
                    f"instance(s) found between advertised offer and presented terms (e.g. '{sample}')."
                ),
                page_url=page_url,
                evidence=matched_evidence,
                metadata={"flagged_count": len(flagged_items), "items": flagged_items[:3]}
            )

        return DetectionFinding(
            pattern=self.pattern_name,
            status="NOT_DETECTED",
            detected=False,
            confidence=0,
            reason="Advertised offers, link descriptions, and product terms appear consistent without deceptive substitution.",
            page_url=page_url,
            evidence=[],
            metadata={"flagged_count": 0}
        )
