import logging
import re
from typing import Any, Dict, List, Optional

from app.models.detection_model import DetectionEvidenceRef, DetectionFinding
from app.services.dark_patterns.base_detector import BaseDetector

logger = logging.getLogger(__name__)

# Keywords indicating optional add-ons, insurances, warranties, donations, memberships, tips, or extra services
ADDON_KEYWORDS = [
    r"extended\s*warranty",
    r"warranty",
    r"care\s*pack",
    r"device\s*protection",
    r"protection\s*plan",
    r"protect\s*(my|your)?\s*purchase",
    r"insurance",
    r"delivery\s*protection",
    r"package\s*protection",
    r"accidental\s*damage",
    r"service\s*plan",
    r"donate",
    r"donation",
    r"charity\s*contribution",
    r"tip\s*(for|to)?\s*(delivery|driver|staff|order)?",
    r"gratuity",
    r"gift\s*wrap",
    r"express\s*handling",
    r"priority\s*(processing|shipping|delivery)",
    r"add-on",
    r"addon",
    r"membership\s*(plan|fee|pass)?",
    r"subscription\s*(pass|service|addon)?",
    r"contribution",
]

# Keywords indicating mandatory legal terms or account settings that must NOT be flagged as basket sneaking
MANDATORY_EXCLUSIONS = [
    r"terms\s*(and|&)\s*conditions",
    r"terms\s*of\s*service",
    r"terms\s*of\s*use",
    r"privacy\s*policy",
    r"i\s*agree",
    r"agree\s*to",
    r"age\s*verification",
    r"over\s*18",
    r"remember\s*me",
    r"keep\s*me\s*signed\s*in",
    r"save\s*(this)?\s*card",
    r"billing\s*address\s*same",
    r"ship\s*to\s*different",
    r"subscribe\s*to\s*newsletter",
    r"email\s*updates",
    r"sms\s*alerts",
]

# Mandatory fee keywords (taxes, standard shipping) that are legitimate and must NOT be classified as basket sneaking
LEGITIMATE_FEE_EXCLUSIONS = [
    r"\bgst\b",
    r"\bvat\b",
    r"\btax(es)?\b",
    r"sales\s*tax",
    r"standard\s*shipping",
    r"delivery\s*charge",
    r"shipping\s*fee",
    r"subtotal",
    r"total\s*payable",
]

# Keywords indicating pure recommendations that are NOT added to cart
RECOMMENDATION_KEYWORDS = [
    r"you\s*may\s*(also)?\s*like",
    r"recommended\s*(for\s*you)?",
    r"customers\s*(also)?\s*(bought|viewed)",
    r"frequently\s*bought\s*together",
    r"similar\s*products",
    r"sponsored\s*products",
]

PRICE_PATTERN = re.compile(
    r"(?:₹|Rs\.?|INR|\$|€|£)?\s*\d+(?:[\.,]\d+)?(?:\s*(?:₹|Rs\.?|INR|USD|EUR|GBP))?",
    re.IGNORECASE
)


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
        Evaluates Basket Sneaking using a multi-layered detection model:
        1. LEVEL 1: Explicit preselection of optional add-on checkboxes / toggles.
        2. LEVEL 2: Unsolicited items or add-ons placed in cart / basket structures.
        3. LEVEL 3: Verified clean cart or purchase controls without preselected add-ons (NOT_DETECTED).
        4. LEVEL 4: Insufficient cart / checkout interaction data (INSUFFICIENT_EVIDENCE).
        5. LEVEL 5: Blocked cart / auth required (NOT_EVALUATED).
        """
        page_url = extracted_data.get("url") or evidence_record.get("page_url", "")
        evidence_items = evidence_record.get("evidence_items", [])
        artifact_path = evidence_record.get("artifacts", {}).get("extracted_json", "") or ""

        # Map existing evidence items by category & selector
        cb_evidence_map = {
            ev.get("selector"): ev
            for ev in evidence_items
            if ev.get("category") == "checkboxes"
        }
        cart_evidence_map = {
            ev.get("selector"): ev
            for ev in evidence_items
            if ev.get("category") == "cart_items"
        }

        detected_evidence: List[DetectionEvidenceRef] = []
        detection_reasons: List[str] = []

        # ======================================================================
        # 1. EVALUATE CART INTERACTION RESULTS (Strongest Direct Evidence)
        # ======================================================================
        cart_interaction = extracted_data.get("cart_interaction")
        if cart_interaction and isinstance(cart_interaction, dict):
            cart_status = cart_interaction.get("status")

            if cart_status == "success":
                unsolicited_items = cart_interaction.get("unsolicited_items", [])
                if unsolicited_items:
                    for idx, it in enumerate(unsolicited_items):
                        it_name = it.get("name", "Unsolicited Add-on")
                        it_price = it.get("price", "")
                        it_sel = it.get("selector", "cart")
                        detected_evidence.append(
                            DetectionEvidenceRef(
                                evidence_id=f"ev_cart_unsolicited_{idx}",
                                evidence_type="extracted_data",
                                category="cart_items",
                                selector=it_sel,
                                text=it_name,
                                artifact_path=artifact_path,
                                context=f"Unsolicited item added to cart: '{it_name}' ({it_price})" if it_price else f"Unsolicited item in cart: '{it_name}'"
                            )
                        )
                        detection_reasons.append(f"Unsolicited add-on '{it_name}' was automatically inserted into the shopping cart")

            elif cart_status in ("login_required", "login_timeout"):
                return DetectionFinding(
                    pattern=self.pattern_name,
                    status="NOT_EVALUATED",
                    detected=False,
                    confidence=0,
                    reason=(
                        "Basket Sneaking evaluation required authentication. "
                        "Login was required to inspect the shopping cart on this website."
                    ),
                    page_url=page_url,
                    evidence=[],
                    metadata={"reason_code": "LOGIN_REQUIRED", "cart_status": cart_status}
                )

            elif cart_status in ("blocked", "inaccessible"):
                detail_msg = cart_interaction.get("message", "Shopping cart flow could not be navigated.")
                return DetectionFinding(
                    pattern=self.pattern_name,
                    status="NOT_EVALUATED",
                    detected=False,
                    confidence=0,
                    reason=f"Basket Sneaking evaluation could not access cart flow: {detail_msg}",
                    page_url=page_url,
                    evidence=[],
                    metadata={"reason_code": "CART_INACCESSIBLE"}
                )

        # ======================================================================
        # 2. LEVEL 1: EVALUATE PRESELECTED CHECKBOXES (Optional Add-ons)
        # ======================================================================
        checkboxes = list(extracted_data.get("checkboxes", []))

        # Also extract checkboxes from forms if not already collected
        for form in extracted_data.get("forms", []):
            for inp in form.get("inputs", []):
                if inp.get("type") == "checkbox":
                    checkboxes.append(inp)

        for cb in checkboxes:
            is_checked = cb.get("checked", False) or cb.get("default_checked", False)
            if not is_checked:
                continue

            raw_label = (cb.get("label") or cb.get("name") or "").strip()
            surrounding = (cb.get("surrounding_text") or "").strip()
            full_text = f"{raw_label} {surrounding}".strip()
            full_text_lower = full_text.lower()

            # False Positive Filter 1: Exclude mandatory terms and account options
            if any(re.search(pat, full_text_lower) for pat in MANDATORY_EXCLUSIONS):
                continue

            # False Positive Filter 2: Exclude standard taxes / shipping
            if any(re.search(pat, full_text_lower) for pat in LEGITIMATE_FEE_EXCLUSIONS):
                continue

            # Check for matching optional add-on keywords
            matched_kw = None
            for kw in ADDON_KEYWORDS:
                if re.search(kw, full_text_lower):
                    matched_kw = kw
                    break

            if matched_kw:
                ev_item = cb_evidence_map.get(cb.get("selector"))
                ev_id = ev_item.get("evidence_id") if ev_item else f"ev_bs_cb_{len(detected_evidence)}"
                rel_artifact = ev_item.get("artifact_path", "") if ev_item else artifact_path

                # Extract price if present in context
                price_match = PRICE_PATTERN.search(full_text)
                detected_price = price_match.group(0).strip() if price_match else ""

                item_label = raw_label or surrounding[:60]
                detected_evidence.append(
                    DetectionEvidenceRef(
                        evidence_id=ev_id,
                        evidence_type="extracted_data",
                        category="checkboxes",
                        selector=cb.get("selector"),
                        text=item_label,
                        tag="input",
                        artifact_path=rel_artifact,
                        context=f"Preselected add-on checkbox ({matched_kw}): '{item_label}'" + (f" (+{detected_price})" if detected_price else "")
                    )
                )
                detection_reasons.append(
                    f"Optional add-on '{item_label}' was preselected by default without explicit user selection"
                )

        # ======================================================================
        # 3. LEVEL 2: EVALUATE STRUCTURED CART / ADD-ON ITEMS IN DOM
        # ======================================================================
        cart_items = extracted_data.get("cart_items", [])
        for item in cart_items:
            txt = (item.get("name") or item.get("text") or item.get("raw_text") or item.get("title") or "").strip()
            txt_lower = txt.lower()
            is_addon = item.get("is_addon", False)
            is_checked = item.get("is_checked", False)
            classes_lower = (item.get("classes") or "").lower()

            # Ignore recommendations that are not preselected / added
            if any(re.search(rkw, txt_lower) or re.search(rkw, classes_lower) for rkw in RECOMMENDATION_KEYWORDS):
                if not is_checked:
                    continue

            # Ignore mandatory exclusions
            if any(re.search(pat, txt_lower) for pat in MANDATORY_EXCLUSIONS):
                continue
            if any(re.search(pat, txt_lower) for pat in LEGITIMATE_FEE_EXCLUSIONS):
                continue

            # Check if this item qualifies as an unsolicited/preselected add-on
            if is_addon or is_checked or any(re.search(kw, txt_lower) for kw in ADDON_KEYWORDS):
                sel = item.get("selector", "")
                ev_item = cart_evidence_map.get(sel)
                ev_id = ev_item.get("evidence_id") if ev_item else f"ev_bs_cart_{len(detected_evidence)}"
                rel_artifact = ev_item.get("artifact_path", "") if ev_item else artifact_path

                # Avoid duplicate evidence
                if not any(d.selector == sel for d in detected_evidence if sel):
                    detected_evidence.append(
                        DetectionEvidenceRef(
                            evidence_id=ev_id,
                            evidence_type="extracted_data",
                            category="cart_items",
                            selector=sel,
                            text=txt[:80],
                            tag=item.get("tag", "div"),
                            artifact_path=rel_artifact,
                            context=f"Unsolicited / pre-added basket item: '{txt[:60]}'"
                        )
                    )
                    detection_reasons.append(
                        f"Optional product/service '{txt[:50]}' was automatically introduced into the basket"
                    )

        # ======================================================================
        # 4. DECISION SYNTHESIS & STATUS SEMANTICS
        # ======================================================================
        if detected_evidence:
            # Calculate explainable confidence score
            confidence = 80
            if any("unsolicited" in d.context.lower() for d in detected_evidence):
                confidence += 15
            if any("price" in d.context.lower() or "₹" in d.context or "$" in d.context for d in detected_evidence):
                confidence += 5
            confidence = min(confidence, 95)

            unique_reasons = list(dict.fromkeys(detection_reasons))
            combined_reason = (
                f"Potential Basket Sneaking detected: {len(detected_evidence)} unsolicited or preselected "
                f"item(s) found. {'; '.join(unique_reasons[:2])}."
            )

            return DetectionFinding(
                pattern=self.pattern_name,
                status="DETECTED",
                detected=True,
                confidence=confidence,
                reason=combined_reason,
                page_url=page_url,
                evidence=detected_evidence,
                metadata={
                    "detected_items_count": len(detected_evidence),
                    "evidence_categories": list(set(d.category for d in detected_evidence)),
                }
            )

        # If cart or purchase controls were present and verified clean
        has_cart_data = bool(cart_items or (cart_interaction and cart_interaction.get("status") == "success"))
        has_checkbox_data = bool(checkboxes and any(not cb.get("checked") for cb in checkboxes))
        has_purchase_forms = bool(extracted_data.get("forms") or extracted_data.get("prices"))

        if has_cart_data or (has_checkbox_data and has_purchase_forms):
            return DetectionFinding(
                pattern=self.pattern_name,
                status="NOT_DETECTED",
                detected=False,
                confidence=0,
                reason=(
                    "Cart and purchase controls evaluated; no preselected add-on items, automatic warranties, "
                    "donations, or unsolicited fees found in the shopping basket."
                ),
                page_url=page_url,
                evidence=[],
                metadata={"clean_cart": True, "controls_evaluated": True}
            )

        # If relevant cart/checkout controls were absent or insufficient
        return DetectionFinding(
            pattern=self.pattern_name,
            status="INSUFFICIENT_EVIDENCE",
            detected=False,
            confidence=0,
            reason=(
                "Insufficient cart or checkout interaction data available on this page to evaluate Basket Sneaking."
            ),
            page_url=page_url,
            evidence=[],
            metadata={"insufficient_cart_context": True}
        )

