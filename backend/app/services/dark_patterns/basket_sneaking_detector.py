import logging
import re
from typing import Any, Dict, List, Optional

from app.models.detection_model import DetectionEvidenceRef, DetectionFinding
from app.services.dark_patterns.base_detector import BaseDetector

logger = logging.getLogger(__name__)

# Keywords indicating optional add-ons, insurances, warranties, donations, or accessories
ADDON_KEYWORDS = [
    r"warranty",
    r"extended warranty",
    r"care pack",
    r"protect",
    r"protection plan",
    r"insurance",
    r"donate",
    r"donation",
    r"tip",
    r"gift wrap",
    r"express handling",
    r"priority processing",
    r"add-on",
    r"addon",
    r"membership",
    r"subscription",
]

# Keywords indicating mandatory legal terms that should NOT be flagged as basket sneaking
MANDATORY_EXCLUSIONS = [
    r"terms\s*(and|&)\s*conditions",
    r"terms\s*of\s*service",
    r"privacy\s*policy",
    r"i\s*agree",
    r"agree\s*to",
    r"age\s*verification",
    r"over\s*18",
    r"remember\s*me",
    r"keep\s*me\s*signed\s*in",
]


class BasketSneakingDetector(BaseDetector):
    @property
    def pattern_name(self) -> str:
        return "Basket Sneaking"

    def detect(
        self,
        extracted_data: Dict[str, Any],
        evidence_record: Dict[str, Any]
    ) -> DetectionFinding:
        """
        Evaluates Basket Sneaking using a 3-state evaluation model:
        1. DETECTED: Confirmed unsolicited item added to cart during interaction.
        2. NOT_DETECTED: Cart interaction succeeded and verified clean cart.
        3. NOT_EVALUATED: No cart interaction performed, or cart flow was blocked/required login,
           or only static candidate checkboxes were found without cart confirmation.
        """
        page_url = extracted_data.get("url") or evidence_record.get("page_url", "")
        cart_interaction = extracted_data.get("cart_interaction")

        # 1. EVALUATE VIA CART INTERACTION (Strongest Evidence)
        if cart_interaction and isinstance(cart_interaction, dict):
            cart_status = cart_interaction.get("status")

            if cart_status == "success":
                unsolicited_items = cart_interaction.get("unsolicited_items", [])
                if unsolicited_items:
                    # Confirmed Basket Sneaking in Cart!
                    item_names = [it.get("name", "Extra Item") for it in unsolicited_items]
                    evidence_refs = []
                    for idx, it in enumerate(unsolicited_items):
                        evidence_refs.append(
                            DetectionEvidenceRef(
                                evidence_id=f"ev_cart_bs_{idx}",
                                evidence_type="extracted_data",
                                category="cart_items",
                                selector=it.get("selector", "cart"),
                                text=it.get("name", ""),
                                artifact_path=evidence_record.get("artifacts", {}).get("extracted_json", "") or "",
                                context=f"Unsolicited add-on in cart: {it.get('name')} (+{it.get('price', '')})"
                            )
                        )

                    return DetectionFinding(
                        pattern=self.pattern_name,
                        status="DETECTED",
                        detected=True,
                        confidence=95,
                        reason=(
                            f"Confirmed Basket Sneaking: {len(unsolicited_items)} unsolicited item(s) "
                            f"({', '.join(item_names)}) were automatically placed into the shopping cart."
                        ),
                        page_url=page_url,
                        evidence=evidence_refs,
                        metadata={
                            "cart_interaction_verified": True,
                            "unsolicited_count": len(unsolicited_items),
                            "items": unsolicited_items
                        }
                    )
                else:
                    # Verified clean cart after safe interaction
                    return DetectionFinding(
                        pattern=self.pattern_name,
                        status="NOT_DETECTED",
                        detected=False,
                        confidence=0,
                        reason=(
                            "Cart interaction completed; no unsolicited items, auto-added warranties, "
                            "or sneak-in accessories were found in the shopping cart."
                        ),
                        page_url=page_url,
                        evidence=[],
                        metadata={"cart_interaction_verified": True, "clean_cart": True}
                    )

            elif cart_status in ("login_required", "login_timeout"):
                msg = (
                    "Basket Sneaking requires cart interaction evidence. Authentication was required "
                    "but manual login was not completed within the allowed time."
                    if cart_status == "login_timeout"
                    else "Basket Sneaking requires cart interaction evidence. Authentication / login "
                    "was required to access the shopping cart on this website."
                )
                return DetectionFinding(
                    pattern=self.pattern_name,
                    status="NOT_EVALUATED",
                    detected=False,
                    confidence=0,
                    reason=msg,
                    page_url=page_url,
                    evidence=[],
                    metadata={"reason_code": "LOGIN_REQUIRED", "cart_status": cart_status}
                )

            elif cart_status in ("blocked", "inaccessible", "not_found"):
                detail_msg = cart_interaction.get("message", "Shopping cart flow could not be navigated.")
                return DetectionFinding(
                    pattern=self.pattern_name,
                    status="NOT_EVALUATED",
                    detected=False,
                    confidence=0,
                    reason=f"Basket Sneaking requires cart interaction evidence. {detail_msg}",
                    page_url=page_url,
                    evidence=[],
                    metadata={"reason_code": "CART_INACCESSIBLE"}
                )

        # 2. EVALUATE STATIC CHECKBOXES (Candidate / Suspicious Signals)
        checkboxes = extracted_data.get("checkboxes", [])
        evidence_items = evidence_record.get("evidence_items", [])

        # Map checkbox evidence by text/selector
        cb_evidence_map = {
            ev.get("selector"): ev
            for ev in evidence_items
            if ev.get("category") == "checkboxes"
        }

        suspicious_checkboxes = []
        for cb in checkboxes:
            is_checked = cb.get("checked", False) or cb.get("default_checked", False)
            if not is_checked:
                continue

            text_content = (
                (cb.get("label") or "") + " " + (cb.get("surrounding_text") or "")
            ).strip().lower()

            # Ignore mandatory consent/terms
            if any(re.search(pat, text_content) for pat in MANDATORY_EXCLUSIONS):
                continue

            # Check for optional add-on keywords
            for kw in ADDON_KEYWORDS:
                if re.search(kw, text_content):
                    ev_item = cb_evidence_map.get(cb.get("selector"))
                    ev_id = ev_item.get("evidence_id") if ev_item else f"ev_static_cb_{len(suspicious_checkboxes)}"
                    rel_artifact = ev_item.get("artifact_path", "") if ev_item else ""

                    suspicious_checkboxes.append(
                        DetectionEvidenceRef(
                            evidence_id=ev_id,
                            evidence_type="extracted_data",
                            category="checkboxes",
                            selector=cb.get("selector"),
                            text=cb.get("label") or cb.get("surrounding_text"),
                            tag="input",
                            artifact_path=rel_artifact,
                            context=f"Pre-selected optional checkbox matching '{kw}'"
                        )
                    )
                    break

        if suspicious_checkboxes:
            return DetectionFinding(
                pattern=self.pattern_name,
                status="NOT_EVALUATED",
                detected=False,
                confidence=45,
                reason=(
                    f"Candidate signal: Found {len(suspicious_checkboxes)} pre-selected optional add-on "
                    f"checkbox(es) in the page DOM. Basket Sneaking cannot be confirmed without cart verification."
                ),
                page_url=page_url,
                evidence=suspicious_checkboxes,
                metadata={
                    "candidate_signal": True,
                    "signal_type": "STATIC_SUSPICIOUS_EVIDENCE",
                    "checkbox_count": len(suspicious_checkboxes)
                }
            )

        # 3. NO CART INTERACTION AND NO SUSPICIOUS SIGNALS -> NOT_EVALUATED
        return DetectionFinding(
            pattern=self.pattern_name,
            status="NOT_EVALUATED",
            detected=False,
            confidence=0,
            reason=(
                "Basket Sneaking requires cart interaction evidence. This audit did not perform a "
                "successful add-to-cart/cart inspection workflow on this page."
            ),
            page_url=page_url,
            evidence=[],
            metadata={"reason_code": "NO_INTERACTION_PERFORMED"}
        )
