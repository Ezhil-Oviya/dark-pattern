import re
from typing import Any, Dict, List, Optional, Tuple

from app.models.detection_model import DetectionEvidenceRef, DetectionFinding
from app.services.dark_patterns.base_detector import BaseDetector


class DripPricingDetector(BaseDetector):
    """
    Detector for Drip Pricing / Hidden Costs dark pattern.

    Identifies when additional mandatory fees, platform charges, convenience fees,
    booking surcharges, or hidden handling costs are incrementally revealed or added
    that were not clearly disclosed in the upfront headline price.
    """

    @property
    def pattern_name(self) -> str:
        return "Drip Pricing"

    # Suspicious drip pricing / mandatory hidden fee patterns
    HIDDEN_FEE_PATTERNS = [
        r"\b(?:mandatory|undisclosed|hidden)\s+(?:fee|charge|surcharge)\b",
        r"\b(?:platform|convenience|service|booking|handling|processing|facility)\s+fee(?:\s*:\s*|\s+of\s+)(?:₹|Rs\.?|INR|\$|€|£)?\s*\d+",
        r"\b(?:platform|convenience|service|booking|handling|processing)\s+fee\b",
        r"\bresort\s+fee\b",
        r"\bcleaning\s+fee(?:\s*:\s*|\s+of\s+)(?:₹|Rs\.?|INR|\$|€|£)?\s*\d+",
        r"\badditional\s+(?:mandatory|handling)\s+charge\b",
        r"\bextra\s+fee\s+applied\b",
        r"\bunavoidable\s+surcharge\b",
    ]

    # Standard clearly disclosed / transparent tax patterns (NOT drip pricing)
    TRANSPARENT_EXCLUSIONS = [
        r"^\s*inclusive\s+of\s+all\s+taxes\s*$",
        r"^\s*all\s+taxes\s+included\s*$",
        r"^\s*free\s+shipping\s*$",
        r"^\s*zero\s+convenience\s+fee\s*$",
        r"^\s*no\s+hidden\s+(?:fees|charges)\s*$",
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
            if item.get("category") in ("prices", "visible_text", "cart_items"):
                if selector and item.get("selector") == selector:
                    return DetectionEvidenceRef(
                        evidence_id=item.get("evidence_id", ""),
                        evidence_type=item.get("evidence_type", "extracted_data"),
                        category=item.get("category", "prices"),
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
                        category=item.get("category", "prices"),
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
        prices = extracted_data.get("prices", [])
        visible_text = extracted_data.get("visible_text", [])

        # Check if page has any pricing or transactional content
        if not prices and not any("₹" in t.get("text", "") or "$" in t.get("text", "") for t in visible_text):
            return DetectionFinding(
                pattern=self.pattern_name,
                status="INSUFFICIENT_EVIDENCE",
                detected=False,
                confidence=0,
                reason="No price components or transaction breakdown present on this page to evaluate Drip Pricing.",
                page_url=page_url,
                evidence=[],
                metadata={"reason_code": "NO_PRICE_DATA"}
            )

        flagged_fees: List[Dict[str, Any]] = []
        matched_evidence: List[DetectionEvidenceRef] = []

        # 1. Scan price elements and contexts
        for p_item in prices:
            context = (p_item.get("context") or "") + " " + (p_item.get("raw_text") or "")
            for pattern in self.HIDDEN_FEE_PATTERNS:
                if re.search(pattern, context, re.IGNORECASE):
                    # Ensure it's not an exclusion
                    if not any(re.search(exc, context, re.IGNORECASE) for exc in self.TRANSPARENT_EXCLUSIONS):
                        flagged_fees.append({
                            "text": context.strip()[:100],
                            "selector": p_item.get("selector"),
                            "confidence": 85
                        })
                        ev_ref = self._find_matching_evidence(
                            evidence_record,
                            selector=p_item.get("selector"),
                            text_snippet=p_item.get("raw_text")
                        )
                        if ev_ref:
                            matched_evidence.append(ev_ref)
                        break

        # 2. Scan visible text blocks for mandatory fee disclosures
        for t_item in visible_text:
            txt = t_item.get("text", "")
            for pattern in self.HIDDEN_FEE_PATTERNS:
                if re.search(pattern, txt, re.IGNORECASE):
                    if not any(re.search(exc, txt, re.IGNORECASE) for exc in self.TRANSPARENT_EXCLUSIONS):
                        flagged_fees.append({
                            "text": txt[:100],
                            "selector": t_item.get("selector"),
                            "confidence": 80
                        })
                        ev_ref = self._find_matching_evidence(
                            evidence_record,
                            text_snippet=txt[:50]
                        )
                        if ev_ref:
                            matched_evidence.append(ev_ref)
                        break

        if flagged_fees:
            sample_fee = flagged_fees[0]["text"]
            max_conf = max(f["confidence"] for f in flagged_fees)
            return DetectionFinding(
                pattern=self.pattern_name,
                status="DETECTED",
                detected=True,
                confidence=max_conf,
                reason=(
                    f"Potential Drip Pricing / Hidden Costs detected: {len(flagged_fees)} undisclosed "
                    f"or incremental mandatory charge(s) found (e.g. '{sample_fee}')."
                ),
                page_url=page_url,
                evidence=matched_evidence,
                metadata={"flagged_count": len(flagged_fees), "samples": [f["text"] for f in flagged_fees[:3]]}
            )

        return DetectionFinding(
            pattern=self.pattern_name,
            status="NOT_DETECTED",
            detected=False,
            confidence=0,
            reason="Price disclosures appear upfront; no hidden mandatory fees, convenience surcharges, or unexpected cost drippings detected.",
            page_url=page_url,
            evidence=[],
            metadata={"flagged_count": 0}
        )
