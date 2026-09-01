import re
from typing import Any, Dict, List, Optional, Tuple

from app.models.detection_model import DetectionEvidenceRef, DetectionFinding
from app.services.dark_patterns.base_detector import BaseDetector


class FalseUrgencyDetector(BaseDetector):
    """
    Dedicated detector for False Urgency dark pattern.

    Identifies when dynamic countdown timers, artificial scarcity statements
    (e.g., 'Only 2 left in stock'), high-demand pressure warnings, or expiring
    deal banners are utilized to pressure consumers into making accelerated
    purchasing decisions.
    """

    @property
    def pattern_name(self) -> str:
        return "False Urgency"

    # Strong countdown/timer patterns
    TIMER_REGEX = re.compile(
        r"(?:\b\d{1,2}\s*:\s*\d{2}(?:\s*:\s*\d{2})?\b|"
        r"\b\d+\s*(?:mins?|minutes?|hours?|hrs?|seconds?|secs?)\s*left\b|"
        r"\b\d+\s*days?\s*left\b|"
        r"\bends?\s+in\s+\d+|"
        r"\bexpires?\s+in\s+\d+)",
        re.IGNORECASE,
    )

    # Explicit scarcity statements (moderate-to-strong urgency)
    SCARCITY_PATTERNS = [
        r"\bonly\s+\d+\s+(?:left|items?\s+left|units?\s+left|in\s+stock|remaining)\b",
        r"\b\d+\s+(?:left\s+in\s+stock|units?\s+remaining|items?\s+remaining)\b",
        r"\balmost\s+gone\b",
        r"\bfew\s+(?:items?|units?|seats?|rooms?)\s+left\b",
        r"\bselling\s+fast\b",
        r"\bin\s+high\s+demand\b",
        r"\b\d+\s+people\s+(?:bought|viewing|looking|ordered)\b",
        r"\bclaimed\s+\d+%\b",
        r"\bclaim(?:ing|ed)?\s+\d+%\s+of\s+deal\b",
        r"\blightning\s+deal\b",
        r"\bflash\s+sale\s+ends\b",
        r"\blast\s+chance\b",
        r"\bhurry,\s+offer\s+ends\b",
        r"\bhurry,\s+deal\s+ends\b",
        r"\bstock\s+running\s+out\b",
    ]

    # Weak generic promotional words (MUST NOT trigger detection alone)
    GENERIC_EXCLUSIONS = [
        r"^\s*special\s+offer\s+available\s*$",
        r"^\s*best\s+offers?\s*$",
        r"^\s*great\s+deals?\s*$",
        r"^\s*available\s+now\s*$",
        r"^\s*sale\s+is\s+live\s*$",
        r"^\s*on\s+sale\s*$",
        r"^\s*top\s+offers?\s*$",
    ]

    def _is_weak_generic_text(self, text: str) -> bool:
        """Checks if text contains only generic promotional phrases without urgency."""
        lower_text = text.lower().strip()
        for pattern in self.GENERIC_EXCLUSIONS:
            if re.match(pattern, lower_text):
                return True
        return False

    def _evaluate_element(self, element: Dict[str, Any]) -> Tuple[bool, int, str]:
        """
        Evaluates an individual urgency element.
        Returns: (is_flagged, confidence, signal_type)
        """
        text = (element.get("text") or "").strip()
        classes = (element.get("classes") or "").lower()
        tag = (element.get("tag") or "").lower()
        pattern_type = element.get("pattern_type")

        if not text or self._is_weak_generic_text(text):
            return False, 0, "none"

        has_timer = bool(self.TIMER_REGEX.search(text)) or pattern_type == "timer" or any(
            t in classes for t in ["timer", "countdown", "countdown-timer", "deal-timer"]
        )

        has_scarcity = any(
            re.search(p, text, re.IGNORECASE) for p in self.SCARCITY_PATTERNS
        ) or pattern_type == "scarcity"

        # Strongest: Combined countdown + scarcity/offer deadline
        if has_timer and has_scarcity:
            return True, 95, "countdown_and_scarcity"

        # Strong: Active countdown timer
        if has_timer:
            return True, 90, "countdown_timer"

        # Moderate-to-Strong: Explicit scarcity ("Only X left")
        if has_scarcity:
            return True, 85, "scarcity_pressure"

        return False, 0, "none"

    def _find_matching_evidence(
        self,
        evidence_record: Dict[str, Any],
        selector: Optional[str] = None,
        text_snippet: Optional[str] = None,
    ) -> Optional[DetectionEvidenceRef]:
        """Finds corresponding Module 4 EvidenceItem in the evidence record."""
        items = evidence_record.get("evidence_items", [])
        for item in items:
            if item.get("category") == "urgency_elements":
                if selector and item.get("selector") == selector:
                    return DetectionEvidenceRef(
                        evidence_id=item.get("evidence_id", ""),
                        evidence_type=item.get("evidence_type", "extracted_data"),
                        category="urgency_elements",
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
                        category="urgency_elements",
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
        evidence_record: Dict[str, Any],
    ) -> DetectionFinding:
        page_url = extracted_data.get("url") or evidence_record.get("page_url", "")
        urgency_elements = extracted_data.get("urgency_elements", [])

        flagged_candidates: List[Dict[str, Any]] = []
        matched_evidence: List[DetectionEvidenceRef] = []

        for urg in urgency_elements:
            is_flagged, confidence, signal_type = self._evaluate_element(urg)
            if is_flagged:
                txt = urg.get("text", "")
                flagged_candidates.append(
                    {
                        "text": txt,
                        "confidence": confidence,
                        "signal_type": signal_type,
                        "selector": urg.get("selector"),
                    }
                )

                ev_ref = self._find_matching_evidence(
                    evidence_record,
                    selector=urg.get("selector"),
                    text_snippet=txt,
                )
                if ev_ref:
                    matched_evidence.append(ev_ref)

        # Build decision
        if flagged_candidates:
            max_confidence = max(c["confidence"] for c in flagged_candidates)
            signals_summary = ", ".join(
                set(c["signal_type"].replace("_", " ") for c in flagged_candidates)
            )
            sample_text = flagged_candidates[0]["text"][:60]

            reason = (
                f"Potential False Urgency detected: {len(flagged_candidates)} urgency "
                f"indicator(s) ({signals_summary}, e.g. '{sample_text}...') were present "
                f"to accelerate consumer decision-making."
            )

            return DetectionFinding(
                pattern=self.pattern_name,
                status="DETECTED",
                detected=True,
                confidence=max_confidence,
                reason=reason,
                page_url=page_url,
                evidence=matched_evidence,
                metadata={
                    "flagged_count": len(flagged_candidates),
                    "signals": [c["signal_type"] for c in flagged_candidates],
                },
            )

        return DetectionFinding(
            pattern=self.pattern_name,
            status="NOT_DETECTED",
            detected=False,
            confidence=0,
            reason=(
                "No evidence of dynamic countdown timers, artificial scarcity statements, "
                "or high-demand urgency pressure found on the page."
            ),
            page_url=page_url,
            evidence=[],
            metadata={"flagged_count": 0, "signals": []},
        )
