import logging
import re
from typing import Any, Dict, List, Optional

from app.models.detection_model import DetectionEvidenceRef, DetectionFinding
from app.services.dark_patterns.base_detector import BaseDetector

logger = logging.getLogger(__name__)


class ForcedActionDetector(BaseDetector):
    """
    Detector for Forced Action dark patterns.

    Identifies scenarios where consumers are required or coerced into performing an unnecessary,
    unrelated, or intrusive action (e.g., mandatory promotional newsletter signup, forced account
    creation to view public catalog, forced social sharing, or unrelated data harvesting)
    as a prerequisite to accessing the desired service or completing a basic task.

    Distinguishes legitimate necessary steps (e.g., shipping address for physical delivery,
    payment credentials on checkout) from manipulative forced actions.
    """

    @property
    def pattern_name(self) -> str:
        return "Forced Action"

    # Keywords for promotional marketing and unrelated consent
    PROMOTIONAL_CONSENT_PATTERNS = [
        r"\b(?:receive|send\s+me)\s+(?:promotional|marketing|newsletter|offers?|deals?|updates?|sponsored|partner)\b",
        r"\bi\s+agree\s+to\s+receive\s+(?:marketing|commercial|promotional)\s+(?:emails?|sms|messages?|calls?)\b",
        r"\bconsent\s+to\s+share\s+(?:my\s+data|information)\s+with\s+(?:third\s+parties|partners|advertisers)\b",
        r"\bsubscribe\s+to\s+(?:our\s+)?(?:newsletter|promotions?|daily\s+deals?)\b",
    ]

    # Mandatory blocking modal/overlay wall patterns
    BLOCKING_OVERLAY_PATTERNS = [
        r"\b(?:sign\s+up|log\s+in|register)\s+to\s+(?:continue\s+reading|view\s+product|browse|view\s+prices?|see\s+details?)\b",
        r"\bshare\s+on\s+(?:facebook|twitter|whatsapp|social\s+media)\s+to\s+unlock\b",
        r"\brate\s+(?:our\s+app|us)\s+to\s+(?:continue|proceed)\b",
        r"\bdownload\s+(?:our\s+)?app\s+to\s+view\s+this\s+deal\b",
    ]

    # Legitimate required fields (NOT forced action)
    LEGITIMATE_REQUIRED_TERMS = [
        r"\bi\s+accept\s+(?:the\s+)?terms\s+(?:and|&)\s+conditions\b",
        r"\bi\s+agree\s+to\s+(?:the\s+)?privacy\s+policy\b",
        r"\bshipping\s+address\b",
        r"\bbilling\s+address\b",
        r"\bpayment\s+method\b",
        r"\bcard\s+number\b",
        r"\bcvv\b",
        r"\bexpiration\s+date\b",
    ]

    def _is_legitimate_required(self, text: str) -> bool:
        """Checks if required consent/input is a standard legally required term or shipping/payment."""
        lower = text.lower().strip()
        for pat in self.LEGITIMATE_REQUIRED_TERMS:
            if re.search(pat, lower):
                return True
        return False

    def _find_matching_evidence(
        self,
        evidence_record: Dict[str, Any],
        selector: Optional[str] = None,
        text_snippet: Optional[str] = None,
    ) -> Optional[DetectionEvidenceRef]:
        """Finds corresponding EvidenceItem in the evidence record."""
        items = evidence_record.get("evidence_items", []) if evidence_record else []
        for item in items:
            cat = item.get("category", "")
            if cat in ("checkboxes", "forms", "visible_text", "modals", "buttons"):
                if selector and item.get("selector") == selector:
                    return DetectionEvidenceRef(
                        evidence_id=item.get("evidence_id", ""),
                        evidence_type=item.get("evidence_type", "extracted_data"),
                        category=cat or "checkboxes",
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
                        category=cat or "checkboxes",
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
        forms = extracted_data.get("forms", [])
        checkboxes = extracted_data.get("checkboxes", [])
        modals = extracted_data.get("modals", [])
        visible_text = extracted_data.get("visible_text", [])

        if not forms and not checkboxes and not modals:
            return DetectionFinding(
                pattern=self.pattern_name,
                status="INSUFFICIENT_EVIDENCE",
                detected=False,
                confidence=0,
                reason="No interactive forms, required checkboxes, or modal gating elements found on this page to evaluate Forced Action.",
                page_url=page_url,
                evidence=[],
                metadata={"reason_code": "NO_FORM_OR_MODAL_ELEMENTS"}
            )

        flagged_actions: List[Dict[str, Any]] = []
        matched_evidence: List[DetectionEvidenceRef] = []

        # 1. Check for Required Promotional Checkboxes
        for cb in checkboxes:
            is_req = cb.get("required") is True
            label = (cb.get("label") or "") + " " + (cb.get("surrounding_text") or "")
            if not label.strip():
                continue

            # Check if checkbox requires promotional/marketing consent
            is_promo = any(re.search(pat, label, re.IGNORECASE) for pat in self.PROMOTIONAL_CONSENT_PATTERNS)

            if is_req and is_promo:
                if not self._is_legitimate_required(label):
                    flagged_actions.append({
                        "type": "FORCED_MARKETING_CONSENT",
                        "text": label[:120],
                        "selector": cb.get("selector"),
                        "confidence": 85,
                    })

                    ev_ref = self._find_matching_evidence(evidence_record, selector=cb.get("selector"), text_snippet=label[:40])
                    if ev_ref:
                        matched_evidence.append(ev_ref)

        # 2. Check for Blocking Overlays / Mandatory Gating Walls
        for md in modals:
            md_text = (md.get("text") or "").strip()
            if not md_text:
                continue

            for pat in self.BLOCKING_OVERLAY_PATTERNS:
                if re.search(pat, md_text, re.IGNORECASE):
                    flagged_actions.append({
                        "type": "BLOCKING_GATING_OVERLAY",
                        "text": md_text[:120],
                        "selector": md.get("selector"),
                        "confidence": 80,
                    })

                    ev_ref = self._find_matching_evidence(evidence_record, selector=md.get("selector"), text_snippet=md_text[:40])
                    if ev_ref:
                        matched_evidence.append(ev_ref)
                    break

        # 3. Check for Mandatory Unrelated Inputs in Forms
        for fm in forms:
            for inp in fm.get("inputs", []):
                if inp.get("required") and inp.get("is_visible") is not False:
                    inp_name = (inp.get("name") or "") + " " + (inp.get("label") or "") + " " + (inp.get("placeholder") or "")
                    # Detect intrusive requirements (e.g. mandatory phone or social handle on simple newsletter or public download)
                    if re.search(r"\b(?:telephone|phone\s+number|mobile|annual\s+income|ssn|aadhaar)\b", inp_name, re.IGNORECASE):
                        # If form action is not checkout or payment
                        fm_action = (fm.get("action") or "").lower()
                        if not any(k in fm_action for k in ["checkout", "payment", "order", "shipping", "pay"]):
                            if re.search(r"\b(?:newsletter|download|free|survey)\b", fm_action + " " + inp_name, re.IGNORECASE):
                                flagged_actions.append({
                                    "type": "UNRELATED_MANDATORY_FIELD",
                                    "text": f"Mandatory field '{inp_name.strip()}' in non-transactional form",
                                    "selector": fm.get("selector"),
                                    "confidence": 75,
                                })

        if flagged_actions:
            max_conf = max(f["confidence"] for f in flagged_actions)
            sample = flagged_actions[0]
            types_str = ", ".join(set(f["type"].lower().replace("_", " ") for f in flagged_actions))
            reason = (
                f"Potential Forced Action detected: Unnecessary mandatory action or promotional requirement found "
                f"({types_str}, e.g. '{sample['text']}')."
            )

            return DetectionFinding(
                pattern=self.pattern_name,
                status="DETECTED",
                detected=True,
                confidence=max_conf,
                reason=reason,
                page_url=page_url,
                evidence=matched_evidence,
                metadata={
                    "flagged_count": len(flagged_actions),
                    "signals": [f["type"] for f in flagged_actions],
                    "actions": flagged_actions[:3]
                }
            )

        return DetectionFinding(
            pattern=self.pattern_name,
            status="NOT_DETECTED",
            detected=False,
            confidence=0,
            reason="Form requirements and user interactions appear voluntary and strictly relevant to requested functionality.",
            page_url=page_url,
            evidence=[],
            metadata={"flagged_count": 0}
        )
