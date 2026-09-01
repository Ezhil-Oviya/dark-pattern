import re
from typing import Any, Dict, List, Optional

from app.models.detection_model import DetectionEvidenceRef, DetectionFinding
from app.services.dark_patterns.base_detector import BaseDetector


class ConfirmshamingDetector(BaseDetector):
    """
    Detector for Confirmshaming dark pattern.

    Identifies emotionally manipulative, guilt-inducing, or derogatory language
    embedded in opt-out, decline, or dismissal buttons/links designed to shame
    users into consenting to an offer or newsletter.
    """

    @property
    def pattern_name(self) -> str:
        return "Confirmshaming"

    # Manipulative confirmshaming decline patterns
    CONFIRMSHAMING_PATTERNS = [
        r"\b(?:no|nah|no\s+thanks?),?\s+(?:i\s+don'?t\s+want\s+to\s+save|i\s+hate\s+saving|i\s+prefer\s+paying\s+more|i\s+hate\s+discounts)\b",
        r"\b(?:no|nah),?\s+(?:i\s+don'?t\s+care\s+about\s+(?:saving|security|safety|discounts|deals))\b",
        r"\bi\s+(?:don'?t\s+want|refuse)\s+to\s+protect\s+(?:myself|my\s+device|my\s+order)\b",
        r"\bno,?\s+i\s+like\s+paying\s+full\s+price\b",
        r"\bno,?\s+i\s+don'?t\s+deserve\s+discounts\b",
        r"\bno\s+thanks,?\s+i\s+want\s+to\s+stay\s+unprotected\b",
        r"\bno,?\s+i\s+don'?t\s+want\s+to\s+grow\s+my\s+business\b",
    ]

    # Neutral decline options (MUST NOT trigger Confirmshaming)
    NEUTRAL_EXCLUSIONS = [
        r"^\s*no\s+thanks?\s*$",
        r"^\s*no\s*,?\s*thank\s+you\s*$",
        r"^\s*cancel\s*$",
        r"^\s*skip\s*$",
        r"^\s*close\s*$",
        r"^\s*dismiss\s*$",
        r"^\s*not\s+now\s*$",
        r"^\s*maybe\s+later\s*$",
        r"^\s*continue\s+without\s+saving\s*$",
        r"^\s*decline\s*$",
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
            if item.get("category") in ("buttons", "links", "visible_text", "modals"):
                if selector and item.get("selector") == selector:
                    return DetectionEvidenceRef(
                        evidence_id=item.get("evidence_id", ""),
                        evidence_type=item.get("evidence_type", "extracted_data"),
                        category=item.get("category", "buttons"),
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
                        category=item.get("category", "buttons"),
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
        buttons = extracted_data.get("buttons", [])
        links = extracted_data.get("links", [])
        modals = extracted_data.get("modals", [])

        flagged_elements: List[Dict[str, Any]] = []
        matched_evidence: List[DetectionEvidenceRef] = []

        candidates = buttons + links
        for el in candidates:
            txt = (el.get("text") or "").strip()
            if not txt:
                continue

            # Check if it matches neutral exclusion
            is_neutral = any(re.match(exc, txt, re.IGNORECASE) for exc in self.NEUTRAL_EXCLUSIONS)
            if is_neutral:
                continue

            # Check against confirmshaming patterns
            for pattern in self.CONFIRMSHAMING_PATTERNS:
                if re.search(pattern, txt, re.IGNORECASE):
                    flagged_elements.append({
                        "text": txt,
                        "tag": el.get("tag"),
                        "selector": el.get("selector"),
                        "confidence": 90
                    })
                    ev_ref = self._find_matching_evidence(
                        evidence_record,
                        selector=el.get("selector"),
                        text_snippet=txt
                    )
                    if ev_ref:
                        matched_evidence.append(ev_ref)
                    break

        if flagged_elements:
            sample = flagged_elements[0]["text"]
            max_conf = max(f["confidence"] for f in flagged_elements)
            return DetectionFinding(
                pattern=self.pattern_name,
                status="DETECTED",
                detected=True,
                confidence=max_conf,
                reason=(
                    f"Potential Confirmshaming detected: Manipulative guilt-inducing decline phrasing "
                    f"found (e.g. '{sample}')."
                ),
                page_url=page_url,
                evidence=matched_evidence,
                metadata={"flagged_count": len(flagged_elements), "phrases": [f["text"] for f in flagged_elements]}
            )

        return DetectionFinding(
            pattern=self.pattern_name,
            status="NOT_DETECTED",
            detected=False,
            confidence=0,
            reason="Decline and dismissal options use neutral, non-manipulative phrasing.",
            page_url=page_url,
            evidence=[],
            metadata={"flagged_count": 0}
        )
