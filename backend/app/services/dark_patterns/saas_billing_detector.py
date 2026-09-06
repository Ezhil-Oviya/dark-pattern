import logging
import re
from typing import Any, Dict, List, Optional

from app.models.detection_model import DetectionEvidenceRef, DetectionFinding
from app.services.dark_patterns.base_detector import BaseDetector

logger = logging.getLogger(__name__)


class SaaSBillingDetector(BaseDetector):
    """
    Detector for SaaS Billing / Subscription Trap dark patterns.

    Identifies potentially manipulative subscription and recurring billing flows:
    - Hidden or obscured auto-renewal terms
    - Billing frequency obfuscation (e.g., displaying low monthly breakdown while locking into annual charge)
    - Free trial converting automatically to paid recurring subscription without clear disclosure
    - Asymmetric cancellation barriers (e.g., requiring phone calls, emails, or multi-step retention walls to cancel)
    - Deceptive 'Cancel Anytime' claims coupled with hidden lock-in or cancellation penalties

    Distinguishes legitimate transparent subscription models from manipulative practices.
    """

    @property
    def pattern_name(self) -> str:
        return "SaaS Billing"

    # Manipulative billing & subscription trap indicators
    MANIPULATIVE_PATTERNS = {
        "HIDDEN_AUTO_RENEWAL": [
            r"\brenews?\s+automatically\s+at\s+regular\s+(?:rate|price)\s+without\s+notice\b",
            r"\bauto[- ]renew(?:s|al|ing)?\s+(?:is\s+mandatory|cannot\s+be\s+turned\s+off|is\s+required)\b",
            r"\bnon[- ]refundable\s+(?:annual|recurring|monthly)\s+commitment\b",
            r"\bautomatically\s+billed\s+(?:annually|yearly)\s+after\s+(?:trial|promotional\s+period)\b",
            r"\bby\s+clicking.*you\s+agree\s+to\s+(?:recurring|continuous)\s+monthly\s+charges\b",
        ],
        "FREQUENCY_OBFUSCATION": [
            r"(?:\$|₹|€|£)?\s*\d+(?:\.\d{2})?\s*(?:\/|\s*per\s*)mo(?:nth)?\s*[\(\*]?\s*billed\s+(?:annually|yearly|as\s+one\s+payment)\b",
            r"\bonly\s+(?:\$|₹|€|£)\d+(?:\.\d{2})?\s*per\s+month\s*[\(\*]?\s*billed\s+(?:yearly|annually)\b",
            r"\bintroductory\s+rate\s+increases\s+to\s+(?:\$|₹|€|£)\d+\s+after\s+first\s+month\b",
        ],
        "DECEPTIVE_TRIAL": [
            r"\b(?:start|try)\s+(?:your\s+)?free\s+trial.*(?:credit\s+card\s+required|auto[- ]converts\s+to\s+paid)\b",
            r"\bfree\s+trial\s+converts\s+to\s+(?:paid|premium)\s+subscription\s+automatically\b",
            r"\bfirst\s+\d+\s+days\s+free,\s+then\s+(?:\$|₹|€|£)\d+\/(?:mo|month|yr|year)\b",
            r"\bcard\s+will\s+be\s+charged\s+immediately\s+after\s+trial\s+expires\b",
        ],
        "CANCELLATION_BARRIER": [
            r"\bto\s+cancel,?\s+call\s+(?:us\s+at|our\s+customer\s+service|support)\b",
            r"\bcancellation\s+requires\s+(?:calling|speaking\s+with\s+an\s+agent|written\s+notice)\b",
            r"\bcancel\s+by\s+calling\s+(?:1-\d{3}|\+?\d{10,12})\b",
            r"\bcancellation\s+only\s+available\s+via\s+phone\s+support\b",
            r"\bcancellation\s+fee\s+of\s+(?:\$|₹|€|£)?\d+\s+applies\b",
            r"\bearly\s+termination\s+fee\b",
            r"\bmust\s+contact\s+support\s+at\s+least\s+\d+\s+days\s+prior\s+to\s+renewal\b",
        ],
    }

    # Legitimate transparent subscription disclosures (Clean practice exclusions)
    TRANSPARENT_EXCLUSIONS = [
        r"^\s*cancel\s+anytime\s+in\s+(?:your\s+)?(?:account|settings|dashboard)\s*$",
        r"^\s*1[- ]click\s+cancellation\s*$",
        r"^\s*no\s+credit\s+card\s+required\s*$",
        r"^\s*no\s+automatic\s+renewal\s*$",
        r"^\s*cancel\s+online\s+anytime\s*$",
        r"^\s*we\s+will\s+remind\s+you\s+\d+\s+days\s+before\s+renewal\s*$",
    ]

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
            if cat in ("subscription_signals", "visible_text", "prices", "buttons", "links"):
                if selector and item.get("selector") == selector:
                    return DetectionEvidenceRef(
                        evidence_id=item.get("evidence_id", ""),
                        evidence_type=item.get("evidence_type", "extracted_data"),
                        category=cat or "subscription_signals",
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
                        category=cat or "subscription_signals",
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
        visible_text = extracted_data.get("visible_text", [])
        sub_signals = extracted_data.get("subscription_signals", [])
        prices = extracted_data.get("prices", [])
        buttons = extracted_data.get("buttons", [])
        links = extracted_data.get("links", [])

        # Check if page contains any subscription, pricing, or billing terms
        has_sub_terms = bool(sub_signals)
        has_recurring_keywords = any(
            re.search(r"\b(?:per\s+month|\/mo|\/year|billed\s+annually|subscription|recurring|auto[- ]renew|free\s+trial|membership)\b", t.get("text", ""), re.IGNORECASE)
            for t in visible_text
        )

        if not has_sub_terms and not has_recurring_keywords and not prices:
            return DetectionFinding(
                pattern=self.pattern_name,
                status="INSUFFICIENT_EVIDENCE",
                detected=False,
                confidence=0,
                reason="No subscription plans, recurring billing terms, or pricing controls found on this page to evaluate SaaS Billing.",
                page_url=page_url,
                evidence=[],
                metadata={"reason_code": "NO_SUBSCRIPTION_DATA"}
            )

        flagged_issues: List[Dict[str, Any]] = []
        matched_evidence: List[DetectionEvidenceRef] = []

        # 1. Scan subscription signals & visible text blocks
        candidate_blocks = sub_signals + visible_text
        for block in candidate_blocks:
            txt = (block.get("text") or "").strip()
            if not txt:
                continue

            # Check against manipulative categories
            for cat_name, patterns in self.MANIPULATIVE_PATTERNS.items():
                for pat in patterns:
                    if re.search(pat, txt, re.IGNORECASE):
                        # Ensure not a transparent exclusion
                        if not any(re.search(exc, txt, re.IGNORECASE) for exc in self.TRANSPARENT_EXCLUSIONS):
                            conf = {
                                "CANCELLATION_BARRIER": 90,
                                "HIDDEN_AUTO_RENEWAL": 85,
                                "FREQUENCY_OBFUSCATION": 80,
                                "DECEPTIVE_TRIAL": 80,
                            }.get(cat_name, 75)

                            flagged_issues.append({
                                "text": txt[:120],
                                "category": cat_name,
                                "selector": block.get("selector"),
                                "confidence": conf
                            })

                            ev_ref = self._find_matching_evidence(
                                evidence_record,
                                selector=block.get("selector"),
                                text_snippet=txt[:50]
                            )
                            if ev_ref:
                                matched_evidence.append(ev_ref)
                            break

        # 2. Check for asymmetric cancellation controls across links/buttons
        # (e.g. signup is 1-click CTA button while cancellation requires phone/contact support)
        has_signup_button = any(
            re.search(r"\b(?:subscribe|start\s+membership|join\s+now|get\s+started|upgrade|start\s+trial)\b", b.get("text", ""), re.IGNORECASE)
            for b in buttons
        )
        cancellation_mentions = [
            t.get("text", "") for t in visible_text
            if re.search(r"\b(?:cancel|cancellation|terminate|unsubscribe)\b", t.get("text", ""), re.IGNORECASE)
        ]

        phone_cancellation_found = any(
            re.search(r"\b(?:call|phone|agent|support\s+desk|customer\s+care)\b", cm, re.IGNORECASE)
            for cm in cancellation_mentions
        )

        if has_signup_button and phone_cancellation_found:
            if not any(f["category"] == "CANCELLATION_BARRIER" for f in flagged_issues):
                flagged_issues.append({
                    "text": "1-click instant subscription paired with offline/call-in cancellation requirement",
                    "category": "CANCELLATION_BARRIER",
                    "selector": None,
                    "confidence": 85
                })

        if flagged_issues:
            max_conf = max(f["confidence"] for f in flagged_issues)
            sample_issue = flagged_issues[0]["text"]
            signals = list(set(f["category"].lower().replace("_", " ") for f in flagged_issues))
            signals_str = ", ".join(signals)

            reason = (
                f"Potential SaaS Billing / Subscription Trap detected: {len(flagged_issues)} manipulative billing "
                f"signal(s) found ({signals_str}, e.g. '{sample_issue}')."
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
                    "flagged_count": len(flagged_issues),
                    "signals": signals,
                    "issues": flagged_issues[:4]
                }
            )

        return DetectionFinding(
            pattern=self.pattern_name,
            status="NOT_DETECTED",
            detected=False,
            confidence=0,
            reason="Subscription terms, billing frequency, and cancellation policies appear transparent without hidden auto-renewals or obstructive barriers.",
            page_url=page_url,
            evidence=[],
            metadata={"flagged_count": 0}
        )
