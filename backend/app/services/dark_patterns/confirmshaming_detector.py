import logging
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.models.detection_model import DetectionEvidenceRef, DetectionFinding
from app.services.dark_patterns.base_detector import BaseDetector

logger = logging.getLogger(__name__)


class ConfirmshamingDetector(BaseDetector):
    """
    Robust detector for Confirmshaming dark patterns on e-commerce platforms.

    Identifies when an opt-out, decline, dismissal, or alternative-choice option
    uses guilt-inducing, insulting, derogatory, or emotionally manipulative language
    (e.g., 'No, I prefer paying full price', 'No, I want to stay unprotected')
    to pressure users into accepting a preferred choice (e.g. 'Save 20%', 'Protect Device').

    Strictly excludes neutral refusals ('No thanks', 'Cancel', 'Skip', 'Maybe later', 'No').
    """

    @property
    def pattern_name(self) -> str:
        return "Confirmshaming"

    # Multi-category structured linguistic manipulation signals
    MANIPULATIVE_CATEGORIES = {
        "SELF_DEPRECATION": [
            r"\b(?:i\s+prefer|i\s+like|i'?d\s+rather|i\s+choose)\s+(?:to\s+)?(?:pay|paying)\s+(?:more|full\s+price|extra|higher\s+prices)\b",
            r"\b(?:i\s+hate|i\s+dislike)\s+(?:saving|discounts?|deals?|cashback|free\s+money|bargains?|special\s+offers?)\b",
            r"\bno,?\s+i\s+(?:like|love|prefer|enjoy)\s+(?:paying\s+full\s+price|wasting\s+money|overpaying|to\s+pay\s+full\s+price)\b",
            r"\bi\s+(?:prefer|choose|like)\s+not\s+to\s+save(?:\s+money)?\b",
            r"\bi\s+enjoy\s+(?:paying|to\s+pay)\s+(?:more|full\s+price)\b",
            r"\bi'?d\s+rather\s+(?:pay\s+full\s+price|overpay)\b",
        ],
        "GUILT_AND_APATHY": [
            r"\b(?:no|nah|no\s+thanks?),?\s+(?:i\s+don'?t\s+care\s+about|i\s+don'?t\s+give\s+a|i\s+couldn'?t\s+care\s+less)\b",
            r"\b(?:i\s+don'?t\s+care\s+about\s+(?:saving|discounts?|deals?|getting\s+(?:the\s+)?offer|security|safety|my\s+device|my\s+order|my\s+phone|cashback|points|rewards?))\b",
            r"\bi\s+(?:don'?t\s+want|refuse|reject)\s+to\s+(?:save|protect|secure|claim|get\s+(?:my|the)|grow)\b",
            r"\bi\s+don'?t\s+(?:deserve|need)\s+(?:discounts?|savings?|rewards?|to\s+save)\b",
            r"\bi\s+guess\s+i\s+don'?t\s+(?:want|care|need)\b",
            r"\bi\s+don'?t\s+need\s+to\s+save\b",
        ],
        "NEGATIVE_VULNERABILITY": [
            r"\b(?:i\s+want|i\s+choose|i'?d\s+rather)\s+to\s+stay\s+(?:unprotected|vulnerable|unsafe|at\s+risk)\b",
            r"\bno\s+thanks,?\s+i\s+want\s+to\s+stay\s+unprotected\b",
            r"\b(?:i\s+don'?t\s+want|refuse|prefer\s+not)\s+to\s+protect\s+(?:myself|my\s+device|my\s+order|my\s+phone|my\s+account)\b",
            r"\bno,?\s+(?:let\s+my\s+order|let\s+my\s+package)\s+(?:be\s+unprotected|stay\s+at\s+risk|get\s+damaged)\b",
            r"\bno,?\s+i\s+don'?t\s+want\s+to\s+grow\s+my\s+business\b",
            r"\bi\s+choose\s+to\s+stay\s+unprotected\b",
        ],
        "LOSS_OF_BENEFIT": [
            r"\b(?:no|nah),?\s+(?:i\s+don'?t\s+want\s+(?:the\s+|my\s+|any\s+)?(?:discount|deal|savings?|perks?)|i\s+will\s+pass\s+on\s+savings|i'?ll\s+pay\s+full\s+price)\b",
            r"\bno,?\s+take\s+me\s+away\s+from\s+(?:deals?|savings?|offers?)\b",
            r"\bno,?\s+i\s+don'?t\s+want\s+exclusive\s+(?:access|deals?|offers?|perks?)\b",
            r"\bi\s+don'?t\s+want\s+(?:the\s+)?discount\b",
            r"\bi'?ll\s+pass\s+on\s+(?:the\s+)?(?:savings?|discount|deal)\b",
        ],
        "EMOTIONAL_PRESSURE": [
            r"\bno,?\s+i\s+have\s+enough\s+money\b",
            r"\bno,?\s+i'?m\s+not\s+interested\s+in\s+success\b",
            r"\bno,?\s+i\s+hate\s+free\s+(?:gifts?|shipping|stuff|delivery)\b",
        ],
    }

    # Strict neutral exclusions (MUST NOT trigger Confirmshaming)
    NEUTRAL_EXCLUSIONS = [
        r"^\s*no\s*$",
        r"^\s*no\s+thanks?\s*$",
        r"^\s*no\s*,?\s*thank\s+you\s*$",
        r"^\s*no\s*,?\s*i'?m\s+(?:good|fine|ok|okay)\s*$",
        r"^\s*cancel\s*$",
        r"^\s*skip\s*$",
        r"^\s*skip\s+(?:for\s+now|this\s+step|offer|deal)?\s*$",
        r"^\s*close\s*$",
        r"^\s*dismiss\s*$",
        r"^\s*not\s+now\s*$",
        r"^\s*maybe\s+later\s*$",
        r"^\s*later\s*$",
        r"^\s*not\s+interested\s*$",
        r"^\s*no\s*,?\s*not\s+interested\s*$",
        r"^\s*decline\s*$",
        r"^\s*continue\s*$",
        r"^\s*continue\s+without\s+(?:saving|discount|offer|protection|insurance)?\s*$",
        r"^\s*proceed\s+to\s+checkout\s*$",
        r"^\s*i'?ll\s+pass\s*$",
        r"^\s*never\s*$",
        r"^\s*don'?t\s+show\s+again\s*$",
        r"^\s*opt\s*out\s*$",
        r"^\s*keep\s+browsing\s*$",
    ]

    # Positive preferred action indicator keywords
    PREFERRED_KEYWORDS = [
        r"\b(?:save|discount|claim|get|protect|yes|subscribe|join|unlock|coupon|deal|off|free)\b",
        r"\b\d+%\s+off\b",
        r"\bsave\s+(?:₹|\$|€|£|\d+)\b",
    ]

    def _is_neutral_exclusion(self, text: str) -> bool:
        """Checks if text matches clean, neutral refusal without manipulation."""
        clean = text.strip()
        for pattern in self.NEUTRAL_EXCLUSIONS:
            if re.match(pattern, clean, re.IGNORECASE):
                return True
        return False

    def _extract_manipulation_signals(self, text: str) -> Tuple[List[str], int]:
        """
        Scans text against the structured manipulative categories.
        Returns: (detected_categories, base_confidence)
        """
        detected_signals = []
        base_confidence = 0

        for category, patterns in self.MANIPULATIVE_CATEGORIES.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    if category not in detected_signals:
                        detected_signals.append(category)
                    # Base confidence per category
                    cat_conf = {
                        "SELF_DEPRECATION": 85,
                        "NEGATIVE_VULNERABILITY": 85,
                        "GUILT_AND_APATHY": 80,
                        "LOSS_OF_BENEFIT": 75,
                        "EMOTIONAL_PRESSURE": 80,
                    }.get(category, 75)
                    base_confidence = max(base_confidence, cat_conf)
                    break

        return detected_signals, base_confidence

    def _find_preferred_actions(self, candidates: List[Dict[str, Any]]) -> List[str]:
        """Identifies candidate preferred / positive offer actions on the page."""
        preferred: List[str] = []
        for el in candidates:
            # Must be visible
            if el.get("is_visible") is False or el.get("is_disabled"):
                continue
            txt = (el.get("text") or "").strip()
            if not txt or len(txt) > 80:
                continue
            if self._is_neutral_exclusion(txt):
                continue

            # Check for preferred keywords
            if any(re.search(pat, txt, re.IGNORECASE) for pat in self.PREFERRED_KEYWORDS):
                # Ensure it's not itself a manipulative decline
                sigs, _ = self._extract_manipulation_signals(txt)
                if not sigs and txt not in preferred:
                    preferred.append(txt)

        return preferred

    def _find_matching_evidence(
        self,
        evidence_record: Dict[str, Any],
        candidate: Dict[str, Any],
        page_url: str,
        page_index: int = 0,
    ) -> Optional[DetectionEvidenceRef]:
        """
        Locates or constructs a traceable DetectionEvidenceRef matching the flagged element.
        """
        selector = candidate.get("selector")
        txt = candidate.get("text") or ""
        tag = candidate.get("tag") or "button"
        items = evidence_record.get("evidence_items", []) if evidence_record else []

        # 1. First, search existing evidence items
        for item in items:
            cat = item.get("category", "")
            if cat in ("buttons", "links", "visible_text", "modals"):
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
                if txt and txt in (item.get("text") or ""):
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

        # 2. If not found in evidence items, resolve artifact path from record
        artifacts = evidence_record.get("artifacts") or {} if evidence_record else {}
        extracted_artifact = ""
        if isinstance(artifacts, dict):
            extracted_artifact = artifacts.get("extracted_json") or artifacts.get("evidence_json") or ""
        elif hasattr(artifacts, "extracted_json"):
            extracted_artifact = artifacts.extracted_json or ""

        return DetectionEvidenceRef(
            evidence_id=f"ev_p{page_index}_cs_{uuid.uuid4().hex[:4]}",
            evidence_type="extracted_data",
            category="buttons" if tag in ("button", "input") else "links",
            selector=selector,
            text=txt,
            tag=tag,
            artifact_path=str(extracted_artifact),
            context=f"Interactive decline choice on {page_url}",
        )

    def detect(
        self,
        extracted_data: Dict[str, Any],
        evidence_record: Dict[str, Any],
    ) -> DetectionFinding:
        """
        Executes Confirmshaming detection on extracted page data and evidence record.
        """
        page_url = extracted_data.get("url") or evidence_record.get("page_url", "")
        page_index = evidence_record.get("page_index", 0) if evidence_record else 0

        raw_buttons = extracted_data.get("buttons", [])
        raw_links = extracted_data.get("links", [])
        raw_modals = extracted_data.get("modals", [])

        # 1. Filter to visible, active candidate elements
        visible_buttons = [b for b in raw_buttons if b.get("is_visible") is not False and not b.get("is_disabled")]
        visible_links = [l for l in raw_links if l.get("is_visible") is not False]
        visible_modals = [m for m in raw_modals if m.get("is_visible") is not False]

        all_visible_candidates = visible_buttons + visible_links

        # If page contains zero interactive elements and zero modals
        if not all_visible_candidates and not visible_modals:
            return DetectionFinding(
                pattern=self.pattern_name,
                status="INSUFFICIENT_EVIDENCE",
                detected=False,
                confidence=0,
                reason="No interactive buttons, links, or modal controls found on this page to evaluate Confirmshaming.",
                page_url=page_url,
                evidence=[],
                metadata={"reason_code": "NO_INTERACTIVE_CONTROLS"},
            )

        # 2. Find preferred actions across the page
        preferred_actions = self._find_preferred_actions(all_visible_candidates)

        flagged_elements: List[Dict[str, Any]] = []
        neutral_decline_found = False
        matched_evidence: List[DetectionEvidenceRef] = []

        # 3. Analyze each candidate element
        for el in all_visible_candidates:
            txt = (el.get("text") or "").strip()
            if not txt:
                continue

            # Check if neutral refusal
            if self._is_neutral_exclusion(txt):
                neutral_decline_found = True
                continue

            # Extract manipulation signals
            signals, base_conf = self._extract_manipulation_signals(txt)

            if signals:
                # Calculate dynamic confidence
                confidence = base_conf

                # Boost if paired with a preferred action
                if preferred_actions:
                    confidence += 10

                # Boost for first-person self-deprecation
                if re.search(r"\b(?:i\s+|i'm|i'd|my\s+)\b", txt, re.IGNORECASE):
                    confidence += 5

                # Clamp confidence bounded integer between 50 and 95
                confidence = min(95, max(50, confidence))

                pairing_info = {
                    "decline_text": txt,
                    "preferred_options": preferred_actions,
                    "signals": signals,
                    "selector": el.get("selector"),
                    "tag": el.get("tag"),
                    "confidence": confidence,
                }
                flagged_elements.append(pairing_info)

                ev_ref = self._find_matching_evidence(
                    evidence_record,
                    candidate=el,
                    page_url=page_url,
                    page_index=page_index,
                )
                if ev_ref:
                    matched_evidence.append(ev_ref)

        # Also inspect modal text if available and not yet flagged
        if not flagged_elements and visible_modals:
            for md in visible_modals:
                md_text = (md.get("text") or "").strip()
                if md_text:
                    signals, base_conf = self._extract_manipulation_signals(md_text)
                    if signals:
                        conf = min(90, max(50, base_conf + 5))
                        flagged_elements.append({
                            "decline_text": md_text[:120],
                            "preferred_options": preferred_actions,
                            "signals": signals,
                            "selector": md.get("selector"),
                            "tag": md.get("tag", "dialog"),
                            "confidence": conf,
                        })
                        ev_ref = self._find_matching_evidence(
                            evidence_record,
                            candidate=md,
                            page_url=page_url,
                            page_index=page_index,
                        )
                        if ev_ref:
                            matched_evidence.append(ev_ref)

        # 4. Determine final outcome
        if flagged_elements:
            max_conf = max(f["confidence"] for f in flagged_elements)
            sample_decline = flagged_elements[0]["decline_text"]
            sample_pref = preferred_actions[0] if preferred_actions else "Consent Option"
            all_signals = list(set(s for f in flagged_elements for s in f["signals"]))

            signals_desc = ", ".join(s.lower().replace("_", " ") for s in all_signals)

            reason = (
                f"Potential Confirmshaming detected: Manipulative guilt-inducing or self-deprecating decline phrasing "
                f"found (e.g. '{sample_decline}') designed to shame users rejecting '{sample_pref}' ({signals_desc})."
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
                    "flagged_count": len(flagged_elements),
                    "phrases": [f["decline_text"] for f in flagged_elements],
                    "preferred_actions": preferred_actions,
                    "decline_actions": [f["decline_text"] for f in flagged_elements],
                    "signals": all_signals,
                    "pairings": flagged_elements,
                },
            )

        if neutral_decline_found:
            return DetectionFinding(
                pattern=self.pattern_name,
                status="NOT_DETECTED",
                detected=False,
                confidence=0,
                reason="Interactive opt-out and decline controls were present and use neutral, non-manipulative phrasing (e.g. 'No thanks', 'Cancel', 'Maybe later').",
                page_url=page_url,
                evidence=[],
                metadata={"neutral_controls_present": True, "preferred_actions": preferred_actions},
            )

        # If interactive buttons exist but none represent opt-out or decline
        return DetectionFinding(
            pattern=self.pattern_name,
            status="INSUFFICIENT_EVIDENCE",
            detected=False,
            confidence=0,
            reason="No explicit opt-out, decline, or dismissal controls found on this page to evaluate Confirmshaming.",
            page_url=page_url,
            evidence=[],
            metadata={"reason_code": "NO_DECLINE_CONTROLS"},
        )
