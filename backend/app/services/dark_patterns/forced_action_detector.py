import logging
import re
import uuid
from typing import Any, Dict, List, Optional

from app.models.detection_model import DetectionEvidenceRef, DetectionFinding
from app.services.dark_patterns.ai_classifier import get_ai_classifier
from app.services.dark_patterns.base_detector import BaseDetector
from app.services.dark_patterns.candidate_extractor import extract_forced_action_candidates

logger = logging.getLogger(__name__)


class ForcedActionDetector(BaseDetector):
    """
    AI-Assisted Hybrid Detector for Forced Action dark patterns.

    Architecture:
    1. Candidate Extraction (Prioritizes modals, forms, required checkboxes, and gating buttons).
    2. AI/NLP Semantic Classification Layer (Evaluates coercive continuation intent and context).
    3. DOM & Evidence Deterministic Validation Layer (Validates absence of guest/skip alternatives,
       filters legitimate legal/payment prerequisites, checks mandatory DOM state).
    4. Explainable Finding Synthesis (Output includes separate model_score, confidence, and evidence refs).
    """

    @property
    def pattern_name(self) -> str:
        return "Forced Action"

    # Legitimate necessary terms that must NOT be flagged as Forced Action
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

    def __init__(self):
        self.ai_classifier = get_ai_classifier()

    def _is_legitimate_prerequisite(self, text: str) -> bool:
        """Checks if requirement is standard legally required consent or shipping/payment input."""
        lower = text.lower().strip()
        return any(re.search(pat, lower) for pat in self.LEGITIMATE_REQUIRED_TERMS)

    def _find_matching_evidence(
        self,
        evidence_record: Dict[str, Any],
        candidate: Dict[str, Any],
        page_url: str,
        page_index: int = 0,
    ) -> Optional[DetectionEvidenceRef]:
        """Locates existing EvidenceItem or creates a traceable DetectionEvidenceRef."""
        selector = candidate.get("selector")
        text_snippet = candidate.get("text") or ""
        cat = candidate.get("category", "forms")
        items = evidence_record.get("evidence_items", []) if evidence_record else []

        # 1. Match from evidence_items if available
        for item in items:
            if selector and item.get("selector") == selector:
                return DetectionEvidenceRef(
                    evidence_id=item.get("evidence_id", ""),
                    evidence_type=item.get("evidence_type", "extracted_data"),
                    category=item.get("category", cat),
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
                    category=item.get("category", cat),
                    selector=item.get("selector"),
                    text=item.get("text"),
                    tag=item.get("tag"),
                    artifact_path=item.get("artifact_path", ""),
                    context=item.get("context"),
                )

        # 2. Trace artifact path
        artifacts = evidence_record.get("artifacts") or {} if evidence_record else {}
        extracted_artifact = ""
        if isinstance(artifacts, dict):
            extracted_artifact = artifacts.get("extracted_json") or artifacts.get("evidence_json") or ""
        elif hasattr(artifacts, "extracted_json"):
            extracted_artifact = artifacts.extracted_json or ""

        return DetectionEvidenceRef(
            evidence_id=f"ev_p{page_index}_fa_{uuid.uuid4().hex[:4]}",
            evidence_type="extracted_data",
            category=cat,
            selector=selector,
            text=text_snippet[:100],
            tag=candidate.get("tag", "div"),
            artifact_path=str(extracted_artifact),
            context=f"Forced Action indicator on {page_url}",
        )

    def detect(
        self,
        extracted_data: Dict[str, Any],
        evidence_record: Dict[str, Any]
    ) -> DetectionFinding:
        page_url = extracted_data.get("url") or evidence_record.get("page_url", "")
        page_index = evidence_record.get("page_index", 0) if evidence_record else 0

        # PHASE 1: Candidate Extraction
        try:
            candidates, page_context = extract_forced_action_candidates(extracted_data)
        except Exception as e:
            logger.error(f"[AI] Error in Forced Action candidate extraction: {e}", exc_info=True)
            candidates, page_context = [], {"has_alternative": False}

        if not candidates:
            return DetectionFinding(
                pattern=self.pattern_name,
                status="INSUFFICIENT_EVIDENCE",
                detected=False,
                confidence=0,
                model_score=0.0,
                validation_status="SKIPPED",
                reason="No interactive forms, required checkboxes, or modal gating elements found on this page to evaluate Forced Action.",
                page_url=page_url,
                evidence=[],
                metadata={"reason_code": "NO_FORM_OR_MODAL_ELEMENTS", "candidates_evaluated": 0}
            )

        logger.info(f"[AI] Forced Action candidates: {len(candidates)}")

        flagged_candidates: List[Dict[str, Any]] = []
        matched_evidence: List[DetectionEvidenceRef] = []
        highest_model_score = 0.0
        neutral_candidate_present = False

        # PHASE 2: AI/NLP Semantic Classification
        for cand in candidates:
            cand_text = cand.get("text", "")
            if not cand_text or self._is_legitimate_prerequisite(cand_text):
                continue

            try:
                model_score, ai_meta = self.ai_classifier.classify_forced_action(
                    cand_text,
                    context=cand.get("context", {})
                )
            except Exception as e:
                logger.warning(f"[AI] AI classifier error for candidate '{cand_text[:30]}': {e}")
                model_score, ai_meta = 0.0, {"signals": []}

            if model_score > highest_model_score:
                highest_model_score = model_score

            logger.info(f"[AI] Forced Action score for '{cand_text[:40]}...': {model_score}")

            # Context awareness: If score is strong and coercive
            if model_score >= 0.70:
                # PHASE 3: DOM / Context Validation
                # Validate that no guest / alternative path was available
                has_alt = page_context.get("has_alternative", False) or cand.get("context", {}).get("has_alternative", False)
                is_dismissible = cand.get("context", {}).get("is_dismissible", False)

                if has_alt or is_dismissible:
                    logger.info("[AI] DOM validation: FAILED (Alternative path or dismissible control detected)")
                    continue

                # DOM Validation PASSED
                logger.info("[AI] DOM validation: PASSED")
                # Calculate evidence-backed confidence (calibrated between 75 and 95)
                det_confidence = int(min(95, max(75, round(model_score * 100))))

                flagged_candidates.append({
                    "text": cand_text,
                    "model_score": model_score,
                    "confidence": det_confidence,
                    "signals": ai_meta.get("signals", []),
                    "selector": cand.get("selector"),
                    "category": cand.get("category"),
                })

                ev_ref = self._find_matching_evidence(
                    evidence_record,
                    candidate=cand,
                    page_url=page_url,
                    page_index=page_index
                )
                if ev_ref:
                    matched_evidence.append(ev_ref)

            elif 0.15 <= model_score < 0.70:
                neutral_candidate_present = True

        # PHASE 4: Decision Synthesis
        if flagged_candidates:
            max_conf = max(c["confidence"] for c in flagged_candidates)
            best_model_score = max(c["model_score"] for c in flagged_candidates)
            sample_text = flagged_candidates[0]["text"][:80]
            signals_summary = ", ".join(
                set(s.replace("_", " ") for c in flagged_candidates for s in c["signals"])
            ) or "unnecessary mandatory action"

            reason = (
                f"Potential Forced Action detected: Website coerces user into an unnecessary mandatory action "
                f"without an alternative path ({signals_summary}, e.g. '{sample_text}'). "
                f"AI semantic score: {best_model_score:.2f}."
            )

            logger.info(f"[DETECTION] Final status: DETECTED (Forced Action, score={best_model_score}, conf={max_conf})")
            return DetectionFinding(
                pattern=self.pattern_name,
                status="DETECTED",
                detected=True,
                model_score=best_model_score,
                validation_status="PASSED",
                confidence=max_conf,
                reason=reason,
                page_url=page_url,
                evidence=matched_evidence,
                metadata={
                    "flagged_count": len(flagged_candidates),
                    "model_score": best_model_score,
                    "signals": [c["signals"] for c in flagged_candidates],
                    "actions": flagged_candidates[:3],
                }
            )

        if page_context.get("has_alternative"):
            logger.info("[DETECTION] Final status: NOT_DETECTED (Guest or voluntary alternative available)")
            return DetectionFinding(
                pattern=self.pattern_name,
                status="NOT_DETECTED",
                detected=False,
                model_score=highest_model_score,
                validation_status="PASSED",
                confidence=0,
                reason="User interaction contains voluntary pathways (e.g. 'Continue as guest' or dismissible skip option); no forced gating detected.",
                page_url=page_url,
                evidence=[],
                metadata={"guest_alternative_present": True, "model_score": highest_model_score}
            )

        if neutral_candidate_present:
            logger.info("[DETECTION] Final status: INSUFFICIENT_EVIDENCE (Neutral authentication context without coercive gating)")
            return DetectionFinding(
                pattern=self.pattern_name,
                status="INSUFFICIENT_EVIDENCE",
                detected=False,
                model_score=highest_model_score,
                validation_status="SKIPPED",
                confidence=0,
                reason="Authentication or form elements were present but lacked sufficient evidence of coercive mandatory gating.",
                page_url=page_url,
                evidence=[],
                metadata={"neutral_candidate": True, "model_score": highest_model_score}
            )

        logger.info("[DETECTION] Final status: NOT_DETECTED (Voluntary form interactions)")
        return DetectionFinding(
            pattern=self.pattern_name,
            status="NOT_DETECTED",
            detected=False,
            model_score=highest_model_score,
            validation_status="PASSED",
            confidence=0,
            reason="Form requirements and user interactions appear voluntary and strictly relevant to requested functionality.",
            page_url=page_url,
            evidence=[],
            metadata={"flagged_count": 0, "model_score": highest_model_score}
        )
