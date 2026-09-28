import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

PRICE_REGEX = re.compile(
    r"(?:₹|rs\.?|inr|\$|€|£)\s*\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?\s*(?:₹|rs\.?|inr|usd|eur|gbp|/month|/yr|/year)",
    re.IGNORECASE,
)

GUEST_OR_SKIP_REGEX = re.compile(
    r"\b(?:continue\s+as\s+guest|guest\s+checkout|skip(?:\s+this\s+step)?|maybe\s+later|not\s+now|dismiss|no\s+thanks)\b",
    re.IGNORECASE,
)


def extract_forced_action_candidates(
    extracted_data: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Extracts high-priority candidate elements for Forced Action AI evaluation:
    - Modals & Gating Overlays
    - Required checkboxes (e.g., promotional consent)
    - Forms with mandatory unrelated input fields
    - Action buttons & navigation barriers

    Also extracts page-level context (e.g. presence of 'Continue as guest' or 'Skip').
    """
    candidates: List[Dict[str, Any]] = []

    # 1. Page-level context: Check if user has an alternative path
    has_guest_or_skip = False
    buttons = extracted_data.get("buttons", [])
    links = extracted_data.get("links", [])
    visible_texts = extracted_data.get("visible_text", [])

    for el in buttons + links:
        txt = (el.get("text") or "").strip()
        if txt and GUEST_OR_SKIP_REGEX.search(txt):
            has_guest_or_skip = True
            break

    if not has_guest_or_skip:
        for vt in visible_texts:
            txt = (vt.get("text") or "").strip()
            if txt and GUEST_OR_SKIP_REGEX.search(txt):
                has_guest_or_skip = True
                break

    page_context = {
        "has_alternative": has_guest_or_skip,
        "guest_option_present": has_guest_or_skip,
    }

    # 2. Modals / Gating Overlays
    for modal in extracted_data.get("modals", []):
        md_text = (modal.get("text") or "").strip()
        if md_text:
            is_dismissible = bool(modal.get("is_dismissible") or modal.get("has_close_button"))
            candidates.append({
                "category": "modals",
                "tag": modal.get("tag", "dialog"),
                "text": md_text,
                "selector": modal.get("selector", "#modal-overlay"),
                "context": {
                    "is_modal": True,
                    "is_dismissible": is_dismissible,
                    "has_alternative": has_guest_or_skip,
                },
                "raw_element": modal,
            })

    # 3. Checkboxes (Prioritize required checkboxes)
    for cb in extracted_data.get("checkboxes", []):
        is_req = cb.get("required") is True
        label = (cb.get("label") or "").strip()
        surrounding = (cb.get("surrounding_text") or "").strip()
        full_text = f"{label} {surrounding}".strip()

        if full_text:
            candidates.append({
                "category": "checkboxes",
                "tag": "input",
                "text": full_text,
                "selector": cb.get("selector", "input[type='checkbox']"),
                "context": {
                    "is_required": is_req,
                    "checked": cb.get("checked", False),
                    "has_alternative": has_guest_or_skip,
                },
                "raw_element": cb,
            })

    # 4. Forms with required input fields
    for form in extracted_data.get("forms", []):
        form_action = (form.get("action") or "").lower()
        required_inputs = [
            inp for inp in form.get("inputs", [])
            if inp.get("required") and inp.get("is_visible") is not False
        ]
        for inp in required_inputs:
            inp_name = (inp.get("name") or "") + " " + (inp.get("label") or "") + " " + (inp.get("placeholder") or "")
            inp_name = inp_name.strip()
            if inp_name:
                candidates.append({
                    "category": "forms",
                    "tag": "input",
                    "text": f"Mandatory field '{inp_name}' in form action '{form_action}'",
                    "selector": inp.get("selector") or form.get("selector", "form"),
                    "context": {
                        "is_required": True,
                        "form_action": form_action,
                        "input_name": inp_name,
                        "has_alternative": has_guest_or_skip,
                    },
                    "raw_element": inp,
                })

    # 5. Buttons & Action Links with coercive intent
    for btn in buttons + links:
        txt = (btn.get("text") or "").strip()
        if txt and len(txt) <= 120:
            if re.search(r"\b(?:continue|proceed|view|download|unlock|access|register|sign\s+up|create\s+account)\b", txt, re.IGNORECASE):
                candidates.append({
                    "category": "buttons" if btn.get("tag") in ("button", "input") else "links",
                    "tag": btn.get("tag", "button"),
                    "text": txt,
                    "selector": btn.get("selector", "button"),
                    "context": {
                        "is_interactive": True,
                        "has_alternative": has_guest_or_skip,
                    },
                    "raw_element": btn,
                })

    logger.debug(f"[AI] Extracted {len(candidates)} Forced Action candidate(s) (guest_alt={has_guest_or_skip})")
    return candidates, page_context


def extract_basket_sneaking_candidates(
    extracted_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Extracts high-priority candidate elements for Basket Sneaking AI evaluation:
    - Checkboxes & toggles (with checked status and prices)
    - Cart items & unsolicited products
    - Price-bearing optional services, warranties, insurance
    """
    candidates: List[Dict[str, Any]] = []

    # 1. Direct Unsolicited Cart Items from Cart Interaction (Strongest Direct Evidence)
    cart_interaction = extracted_data.get("cart_interaction")
    if cart_interaction and isinstance(cart_interaction, dict):
        unsolicited = cart_interaction.get("unsolicited_items", [])
        for idx, item in enumerate(unsolicited):
            it_name = item.get("name") or item.get("text") or "Unsolicited Cart Item"
            it_price = item.get("price", "")
            full_text = f"{it_name} {it_price}".strip()
            candidates.append({
                "category": "cart_items",
                "tag": "div",
                "text": full_text,
                "selector": item.get("selector") or f"#unsolicited-cart-item-{idx}",
                "is_checked": True,
                "initial_state": "checked",
                "final_state": "checked",
                "preselected_before_interaction": True,
                "selection_origin": item.get("selection_origin", "preselected"),
                "input_type": item.get("type", "cart_item"),
                "price": it_price,
                "has_price": bool(it_price),
                "is_unsolicited_cart": True,
                "surrounding_dom": item.get("surrounding_text", ""),
                "context": {
                    "is_cart_item": True,
                    "is_preselected": True,
                    "unsolicited": True,
                    "initial_state": "checked",
                },
                "raw_element": item,
            })

    # 2. Checkboxes & Toggles (Checked and Unchecked)
    checkboxes = list(extracted_data.get("checkboxes", []))
    for form in extracted_data.get("forms", []):
        for inp in form.get("inputs", []):
            if inp.get("type") == "checkbox" and inp not in checkboxes:
                checkboxes.append(inp)

    for cb in checkboxes:
        raw_checked = cb.get("checked")
        raw_default = cb.get("default_checked")
        if raw_checked is None and raw_default is None:
            is_checked = None
            initial_state = "unknown"
        else:
            is_checked = bool(raw_checked or raw_default)
            initial_state = "checked" if is_checked else "unchecked"

        label = (cb.get("label") or cb.get("name") or "").strip()
        surrounding = (cb.get("surrounding_text") or "").strip()
        full_text = f"{label} {surrounding}".strip()

        if not full_text:
            continue

        price_match = PRICE_REGEX.search(full_text)
        detected_price = price_match.group(0).strip() if price_match else ""

        user_selected = cb.get("selection_origin") == "user_selected" or cb.get("user_selected") is True
        preselected = (is_checked is True) and not user_selected
        selection_origin = "user_selected" if user_selected else ("preselected" if is_checked else ("voluntary" if is_checked is False else "unknown"))

        candidates.append({
            "category": "checkboxes",
            "tag": "input",
            "text": full_text,
            "selector": cb.get("selector", "input[type='checkbox']"),
            "is_checked": is_checked,
            "initial_state": initial_state,
            "final_state": "checked" if is_checked else ("unchecked" if is_checked is False else "unknown"),
            "preselected_before_interaction": preselected,
            "selection_origin": selection_origin,
            "input_type": cb.get("type", "checkbox"),
            "price": detected_price,
            "has_price": bool(detected_price),
            "is_unsolicited_cart": False,
            "surrounding_dom": surrounding,
            "context": {
                "is_checkbox": True,
                "is_checked": is_checked,
                "initial_state": initial_state,
                "preselected_before_interaction": preselected,
                "selection_origin": selection_origin,
                "has_price": bool(detected_price),
                "detected_price": detected_price,
                "required": cb.get("required", False),
            },
            "raw_element": cb,
        })

    # 3. Structured Cart Items in DOM
    for idx, item in enumerate(extracted_data.get("cart_items", [])):
        txt = (item.get("name") or item.get("text") or item.get("raw_text") or item.get("title") or "").strip()
        if not txt:
            continue

        is_addon = bool(item.get("is_addon"))
        is_checked = bool(item.get("is_checked", True))  # If in cart list, treat as present
        price_match = PRICE_REGEX.search(txt)
        detected_price = price_match.group(0).strip() if price_match else (item.get("price") or "")

        user_selected = item.get("selection_origin") == "user_selected"
        preselected = is_checked and not user_selected
        selection_origin = "user_selected" if user_selected else ("preselected" if is_checked else "unknown")

        candidates.append({
            "category": "cart_items",
            "tag": item.get("tag", "div"),
            "text": txt,
            "selector": item.get("selector") or f".cart-item-{idx}",
            "is_checked": is_checked,
            "initial_state": "checked" if is_checked else "unchecked",
            "final_state": "checked" if is_checked else "unchecked",
            "preselected_before_interaction": preselected,
            "selection_origin": selection_origin,
            "input_type": item.get("type", "cart_item"),
            "price": detected_price,
            "has_price": bool(detected_price),
            "is_unsolicited_cart": is_addon,
            "surrounding_dom": item.get("surrounding_text", ""),
            "context": {
                "is_cart_item": True,
                "is_addon": is_addon,
                "is_checked": is_checked,
                "initial_state": "checked" if is_checked else "unchecked",
                "preselected_before_interaction": preselected,
                "selection_origin": selection_origin,
                "has_price": bool(detected_price),
            },
            "raw_element": item,
        })

    logger.debug(f"[AI] Extracted {len(candidates)} Basket Sneaking candidate(s)")
    return candidates
