import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.models.detection_model import DetectionEvidenceRef, DetectionFinding
from app.services.dark_patterns.base_detector import BaseDetector

logger = logging.getLogger(__name__)


class InterfaceInterferenceDetector(BaseDetector):
    """
    Detector for Interface Interference dark patterns.

    Identifies user interface designs that intentionally manipulate visual hierarchy,
    element dimensions, color contrast, and relative positioning to nudge or steer
    users toward a preferred choice while obscuring, de-emphasizing, or hiding alternative actions.

    Signals analyzed:
    - Asymmetric button prominence (bounding box area ratio >= 2.5x, font size disparity)
    - Visual de-emphasis (primary action is high-contrast colorful button while alternative is plain text link)
    - Low-contrast or suppressed secondary controls
    - Obscured opt-out / reject choices placed far below or de-emphasized compared to primary CTA
    """

    @property
    def pattern_name(self) -> str:
        return "Interface Interference"

    # Keywords typical for preferred primary actions
    PREFERRED_KEYWORDS = [
        r"\b(?:accept|agree|allow|continue|proceed|buy|order|sign\s+up|subscribe|get\s+started|upgrade|confirm|save|yes|claim)\b",
    ]

    # Keywords typical for alternative secondary / decline actions
    ALTERNATIVE_KEYWORDS = [
        r"\b(?:decline|reject|cancel|skip|no\s+thanks?|manage\s+cookies|customize|settings|options|later|maybe\s+later|dismiss)\b",
    ]

    def _parse_font_size(self, font_size_str: Optional[str]) -> float:
        """Parses CSS font-size in px to float."""
        if not font_size_str:
            return 14.0
        match = re.search(r"(\d+(?:\.\d+)?)px", str(font_size_str))
        if match:
            return float(match.group(1))
        return 14.0

    def _is_low_contrast_style(self, bg_color: str, text_color: str) -> bool:
        """Checks if colors indicate transparent, muted gray, or near-invisible styling."""
        bg_lower = (bg_color or "").lower()
        txt_lower = (text_color or "").lower()

        is_transparent_bg = "rgba(0, 0, 0, 0)" in bg_lower or "transparent" in bg_lower or bg_lower == ""
        is_gray_text = any(g in txt_lower for g in ["rgb(156, 163, 175)", "rgb(107, 114, 128)", "rgb(150, 150, 150)", "#9ca3af", "#6b7280", "#aaa", "#888", "#999"])

        return is_transparent_bg and is_gray_text

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
            if cat in ("buttons", "links", "visible_text", "modals"):
                if selector and item.get("selector") == selector:
                    return DetectionEvidenceRef(
                        evidence_id=item.get("evidence_id", ""),
                        evidence_type=item.get("evidence_type", "extracted_data"),
                        category=cat or "buttons",
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
                        category=cat or "buttons",
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

        # Filter visible interactive controls
        vis_buttons = [b for b in buttons if b.get("is_visible") is not False and not b.get("is_disabled")]
        vis_links = [l for l in links if l.get("is_visible") is not False]
        all_interactive = vis_buttons + vis_links

        if len(all_interactive) < 2 and not modals:
            return DetectionFinding(
                pattern=self.pattern_name,
                status="INSUFFICIENT_EVIDENCE",
                detected=False,
                confidence=0,
                reason="No comparative interactive controls or paired choice elements present on this page to evaluate Interface Interference.",
                page_url=page_url,
                evidence=[],
                metadata={"reason_code": "NO_PAIRED_CONTROLS"}
            )

        flagged_interferences: List[Dict[str, Any]] = []
        matched_evidence: List[DetectionEvidenceRef] = []

        # Find preferred vs alternative candidates
        preferred_candidates = []
        alternative_candidates = []

        for item in all_interactive:
            txt = (item.get("text") or "").strip()
            if not txt:
                continue

            for pat in self.PREFERRED_KEYWORDS:
                if re.search(pat, txt, re.IGNORECASE):
                    preferred_candidates.append(item)
                    break

            for pat in self.ALTERNATIVE_KEYWORDS:
                if re.search(pat, txt, re.IGNORECASE):
                    alternative_candidates.append(item)
                    break

        # Analyze paired choices (e.g. Accept vs Reject / Subscribe vs Cancel)
        for pref in preferred_candidates[:3]:
            pref_text = pref.get("text", "")
            pref_metrics = pref.get("metrics") or {}
            pref_w = pref_metrics.get("width") or 0
            pref_h = pref_metrics.get("height") or 0
            pref_area = pref_w * pref_h
            pref_font = self._parse_font_size(pref_metrics.get("font_size"))
            pref_bg = pref_metrics.get("bg_color") or ""
            pref_tag = pref.get("tag", "button")

            for alt in alternative_candidates[:3]:
                alt_text = alt.get("text", "")
                if pref_text.lower() == alt_text.lower():
                    continue

                alt_metrics = alt.get("metrics") or {}
                alt_w = alt_metrics.get("width") or 0
                alt_h = alt_metrics.get("height") or 0
                alt_area = alt_w * alt_h
                alt_font = self._parse_font_size(alt_metrics.get("font_size"))
                alt_bg = alt_metrics.get("bg_color") or ""
                alt_txt_color = alt_metrics.get("text_color") or ""
                alt_tag = alt.get("tag", "a")

                visual_signals = []
                layout_signals = []
                interaction_signals = []
                confidence = 0

                # Check 1: Severe Area Disparity (>= 3.0x difference when metrics available)
                if pref_area > 0 and alt_area > 0:
                    area_ratio = pref_area / alt_area
                    if area_ratio >= 3.0:
                        visual_signals.append(f"Button area asymmetry ratio {area_ratio:.1f}x (preferred: {pref_area}px² vs alt: {alt_area}px²)")
                        confidence = max(confidence, 85)
                    elif area_ratio >= 2.0:
                        visual_signals.append(f"Moderate area disparity {area_ratio:.1f}x")
                        confidence = max(confidence, 75)

                # Check 2: Element Tag Hierarchy Disparity (Primary styled as solid <button>, Alternative styled as subtle unstyled <a>)
                if pref_tag in ("button", "input") and alt_tag == "a":
                    if not alt_bg or "transparent" in alt_bg or "rgba(0, 0, 0, 0)" in alt_bg:
                        visual_signals.append(f"Preferred action styled as prominent {pref_tag.upper()} while alternative is rendered as plain text link")
                        interaction_signals.append("asymmetric_element_hierarchy")
                        confidence = max(confidence, 80)

                # Check 3: Font Size Disparity (>= 1.4x)
                if pref_font >= 16 and alt_font <= 12 and (pref_font / max(alt_font, 1)) >= 1.35:
                    visual_signals.append(f"Font size disparity ({pref_font}px vs {alt_font}px)")
                    confidence = max(confidence, 75)

                # Check 4: Low Contrast De-emphasis
                if self._is_low_contrast_style(alt_bg, alt_txt_color):
                    visual_signals.append("Alternative choice rendered in low-contrast muted gray text without button styling")
                    confidence = max(confidence, 85)

                if visual_signals or interaction_signals:
                    flagged_interferences.append({
                        "primary_action": pref_text,
                        "alternative_action": alt_text,
                        "visual_signals": visual_signals,
                        "layout_signals": layout_signals,
                        "interaction_signals": interaction_signals,
                        "confidence": confidence,
                        "selector": pref.get("selector") or alt.get("selector")
                    })

                    ev_ref1 = self._find_matching_evidence(evidence_record, selector=pref.get("selector"), text_snippet=pref_text)
                    if ev_ref1:
                        matched_evidence.append(ev_ref1)
                    ev_ref2 = self._find_matching_evidence(evidence_record, selector=alt.get("selector"), text_snippet=alt_text)
                    if ev_ref2 and ev_ref2 not in matched_evidence:
                        matched_evidence.append(ev_ref2)

        if flagged_interferences:
            max_conf = max(f["confidence"] for f in flagged_interferences)
            sample = flagged_interferences[0]
            reason = (
                f"Potential Interface Interference detected: Misleading visual hierarchy and asymmetric prominence "
                f"between primary action '{sample['primary_action']}' and alternative choice '{sample['alternative_action']}' "
                f"({'; '.join(sample['visual_signals'][:2])})."
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
                    "flagged_count": len(flagged_interferences),
                    "interferences": flagged_interferences[:3],
                    "signals": [s for item in flagged_interferences for s in item.get("visual_signals", [])]
                }
            )

        return DetectionFinding(
            pattern=self.pattern_name,
            status="NOT_DETECTED",
            detected=False,
            confidence=0,
            reason="Interface choices, button sizes, and visual hierarchies appear balanced without deceptive visual suppression.",
            page_url=page_url,
            evidence=[],
            metadata={"flagged_count": 0}
        )
