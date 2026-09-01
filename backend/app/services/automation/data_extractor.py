import logging
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)

EXTRACTION_SCRIPT = """
() => {
    function isElementVisible(el) {
        if (!el) return false;
        try {
            const style = window.getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
                return false;
            }
            const rect = el.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0;
        } catch (e) {
            return false;
        }
    }

    function getCssSelector(el) {
        if (!el || el.nodeType !== Node.ELEMENT_NODE) return '';
        if (el.id) return '#' + el.id;
        const parts = [];
        let current = el;
        while (current && current.nodeType === Node.ELEMENT_NODE && parts.length < 4) {
            let tag = current.tagName.toLowerCase();
            if (current.id) {
                parts.unshift('#' + current.id);
                break;
            }
            let selector = tag;
            if (current.className && typeof current.className === 'string') {
                const classes = current.className.trim().split(/\\s+/).filter(c => c && !c.includes(':') && !c.includes('/')).slice(0, 2);
                if (classes.length > 0) {
                    selector += '.' + classes.join('.');
                }
            }
            let parent = current.parentElement;
            if (parent) {
                const siblings = Array.from(parent.children).filter(c => c.tagName === current.tagName);
                if (siblings.length > 1) {
                    const index = siblings.indexOf(current) + 1;
                    selector += `:nth-of-type(${index})`;
                }
            }
            parts.unshift(selector);
            current = current.parentElement;
        }
        return parts.join(' > ');
    }

    // 1. Metadata
    const metadata = {
        url: window.location.href,
        title: document.title || '',
        timestamp: new Date().toISOString()
    };

    // 2. Visible Text Blocks
    const textSet = new Set();
    const visibleTextBlocks = [];
    const textElements = document.querySelectorAll('h1, h2, h3, h4, h5, h6, p, li, blockquote, [role="heading"], article, section');
    for (const el of textElements) {
        if (visibleTextBlocks.length >= 80) break;
        if (isElementVisible(el)) {
            const txt = (el.innerText || '').trim();
            if (txt.length >= 3 && txt.length <= 500 && !textSet.has(txt)) {
                textSet.add(txt);
                visibleTextBlocks.push({
                    tag: el.tagName.toLowerCase(),
                    text: txt
                });
            }
        }
    }

    // 3. Buttons
    const buttons = [];
    const buttonElements = document.querySelectorAll('button, input[type="button"], input[type="submit"], [role="button"], a.btn, a.button, a[class*="btn"], a[class*="button"]');
    for (const el of buttonElements) {
        if (buttons.length >= 60) break;
        const visible = isElementVisible(el);
        const text = (el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('title') || '').trim();
        if (text || el.id) {
            buttons.push({
                text: text,
                tag: el.tagName.toLowerCase(),
                type: el.getAttribute('type') || (el.tagName.toLowerCase() === 'button' ? 'button' : ''),
                id: el.id || '',
                classes: typeof el.className === 'string' ? el.className.trim() : '',
                is_visible: visible,
                is_disabled: el.disabled || el.getAttribute('aria-disabled') === 'true',
                selector: getCssSelector(el)
            });
        }
    }

    // 4. Links
    const links = [];
    const linkElements = document.querySelectorAll('a[href]');
    for (const el of linkElements) {
        if (links.length >= 80) break;
        const href = el.getAttribute('href');
        const text = (el.innerText || el.getAttribute('aria-label') || '').trim();
        if (href && (text || isElementVisible(el))) {
            links.push({
                text: text,
                href: href,
                id: el.id || '',
                classes: typeof el.className === 'string' ? el.className.trim() : '',
                is_visible: isElementVisible(el),
                selector: getCssSelector(el)
            });
        }
    }

    // 5. Forms
    const forms = [];
    const formElements = document.querySelectorAll('form');
    for (const el of formElements) {
        if (forms.length >= 20) break;
        const inputs = [];
        const inputElements = el.querySelectorAll('input, select, textarea');
        for (const inp of inputElements) {
            const inputType = (inp.getAttribute('type') || 'text').toLowerCase();
            const inputName = inp.getAttribute('name') || '';
            const inputId = inp.id || '';
            const inputAuto = inp.getAttribute('autocomplete') || '';
            const isSensitive = /password|pwd|token|secret|cvv|card|otp|auth|ssn|credit|pin/i.test(inputType + ' ' + inputName + ' ' + inputId + ' ' + inputAuto);

            let value = '';
            if (isSensitive || inputType === 'password' || inputType === 'hidden') {
                value = '[MASKED]';
            } else if (inp.value && inp.value.length < 50) {
                value = inp.value;
            }

            let labelText = '';
            if (inp.id) {
                const labelEl = document.querySelector(`label[for="${inp.id}"]`);
                if (labelEl) labelText = (labelEl.innerText || '').trim();
            }
            if (!labelText && inp.closest('label')) {
                labelText = (inp.closest('label').innerText || '').trim();
            }

            inputs.push({
                tag: inp.tagName.toLowerCase(),
                type: inputType,
                name: inp.getAttribute('name') || '',
                placeholder: inp.getAttribute('placeholder') || '',
                label: labelText,
                required: inp.required || inp.getAttribute('aria-required') === 'true',
                is_visible: isElementVisible(inp),
                value: value
            });
        }

        forms.push({
            id: el.id || '',
            name: el.getAttribute('name') || '',
            action: el.getAttribute('action') || '',
            method: (el.getAttribute('method') || 'GET').toUpperCase(),
            inputs: inputs,
            selector: getCssSelector(el)
        });
    }

    // 6. Checkboxes (Basket Sneaking Indicator)
    const checkboxes = [];
    const checkboxElements = document.querySelectorAll('input[type="checkbox"]');
    for (const el of checkboxElements) {
        let labelText = '';
        if (el.id) {
            const labelEl = document.querySelector(`label[for="${el.id}"]`);
            if (labelEl) labelText = (labelEl.innerText || '').trim();
        }
        if (!labelText && el.closest('label')) {
            labelText = (el.closest('label').innerText || '').trim();
        }
        const parentText = (el.parentElement ? el.parentElement.innerText : '').trim();

        checkboxes.push({
            id: el.id || '',
            name: el.getAttribute('name') || '',
            label: labelText || parentText.slice(0, 100),
            checked: !!el.checked,
            default_checked: !!el.defaultChecked || el.hasAttribute('checked'),
            is_visible: isElementVisible(el),
            is_disabled: el.disabled || el.getAttribute('aria-disabled') === 'true',
            selector: getCssSelector(el),
            surrounding_text: parentText.slice(0, 150)
        });
    }

    // 7. Price-related Elements (requires actual numeric digits)
    const prices = [];
    const priceRegex = /(?:₹|Rs\\.?|INR|\\$|€|£)\\s*\\d[\\d,]*(?:\\.\\d{1,2})?|\\b\\d[\\d,]*(?:\\.\\d{1,2})?\\s*(?:₹|Rs\\.?|INR|USD|EUR|GBP)\\b/i;
    const priceCandidates = document.querySelectorAll('[class*="price"], [class*="amount"], [class*="cost"], [class*="total"], [class*="mrp"], [class*="discount"], [id*="price"], [id*="amount"], span, div, p, b, strong');
    const seenPrices = new Set();
    for (const el of priceCandidates) {
        if (prices.length >= 60) break;
        if (!isElementVisible(el)) continue;
        const txt = (el.innerText || '').trim();
        if (priceRegex.test(txt) && txt.length <= 100) {
            const match = txt.match(priceRegex);
            const detected = match ? match[0] : txt;
            const key = `${detected}_${el.tagName}`;
            if (!seenPrices.has(key)) {
                seenPrices.add(key);
                let currency = 'INR';
                if (detected.includes('$')) currency = 'USD';
                else if (detected.includes('€')) currency = 'EUR';
                else if (detected.includes('£')) currency = 'GBP';
                else if (detected.includes('₹') || /Rs|INR/i.test(detected)) currency = 'INR';

                prices.push({
                    raw_text: txt,
                    detected_price: detected,
                    currency: currency,
                    tag: el.tagName.toLowerCase(),
                    classes: typeof el.className === 'string' ? el.className.trim() : '',
                    selector: getCssSelector(el),
                    context: (el.parentElement ? el.parentElement.innerText : '').slice(0, 120).trim()
                });
            }
        }
    }

    // 8. Cart / Basket-related Elements
    const cartItems = [];
    const cartCandidates = document.querySelectorAll('[class*="cart"], [class*="basket"], [class*="bag"], [id*="cart"], [id*="basket"], [class*="addon"], [class*="insurance"], [class*="donation"], [class*="warranty"], [class*="protection"], [data-testid*="cart"]');
    const seenCartEls = new Set();
    for (const el of cartCandidates) {
        if (cartItems.length >= 40) break;
        if (!isElementVisible(el)) continue;
        const txt = (el.innerText || '').trim();
        if (txt.length >= 3 && txt.length <= 300) {
            const selector = getCssSelector(el);
            if (!seenCartEls.has(selector)) {
                seenCartEls.add(selector);
                const isAddon = /addon|add-on|insurance|donate|donation|warranty|protection|fee|tip|extra/i.test(el.className + ' ' + txt);
                const isChecked = el.querySelector('input[type="checkbox"]:checked') !== null;
                cartItems.push({
                    tag: el.tagName.toLowerCase(),
                    text: txt,
                    is_addon: isAddon,
                    is_checked: isChecked,
                    classes: typeof el.className === 'string' ? el.className.trim() : '',
                    selector: selector
                });
            }
        }
    }

    // 9. Urgency-related Elements (False Urgency Indicator)
    const urgencyElements = [];
    const urgencyKeywords = /only\\s+\\d+\\s+left|in\\s+high\\s+demand|selling\\s+fast|hurry|limited\\s+time|flash\\s+sale|deal\\s+of\\s+the\\s+day|expires\\s+in|ends\\s+in|almost\\s+gone|few\\s+left|lightning\\s+deal|stock\\s+running\\s+out|claim(ed|ing)?\\s+\\d+%/i;
    const timerRegex = /\\b\\d{1,2}\\s*:\\s*\\d{2}(?:\\s*:\\s*\\d{2})?\\b|\\b\\d+\\s*(?:mins?|minutes?|hours?|hrs?|seconds?|secs?)\\s*left\\b|\\b\\d+\\s*days?\\s*left\\b/i;
    const urgencyCandidates = document.querySelectorAll('[class*="timer"], [class*="countdown"], [class*="urgency"], [class*="deal"], [class*="scarcity"], [class*="alert"], [id*="timer"], [id*="countdown"], p, span, div, b, strong, em');
    const seenUrgency = new Set();
    for (const el of urgencyCandidates) {
        if (urgencyElements.length >= 50) break;
        if (!isElementVisible(el)) continue;
        const txt = (el.innerText || '').trim();
        if (txt.length >= 3 && txt.length <= 200) {
            let pType = null;
            if (timerRegex.test(txt) || /timer|countdown/i.test(el.className + ' ' + el.id)) {
                pType = 'timer';
            } else if (urgencyKeywords.test(txt)) {
                pType = 'scarcity';
            }
            if (pType) {
                const key = `${pType}_${txt}`;
                if (!seenUrgency.has(key)) {
                    seenUrgency.add(key);
                    urgencyElements.push({
                        text: txt,
                        pattern_type: pType,
                        tag: el.tagName.toLowerCase(),
                        classes: typeof el.className === 'string' ? el.className.trim() : '',
                        selector: getCssSelector(el)
                    });
                }
            }
        }
    }

    // 10. General Relevant DOM / Modals (excluding body and html tags)
    const modals = [];
    const modalCandidates = document.querySelectorAll('dialog, [role="dialog"], [class*="modal"], [class*="popup"], [class*="overlay"]');
    for (const el of modalCandidates) {
        if (modals.length >= 10) break;
        const tag = el.tagName.toLowerCase();
        if (tag === 'body' || tag === 'html') continue;
        if (isElementVisible(el)) {
            modals.push({
                tag: tag,
                id: el.id || '',
                classes: typeof el.className === 'string' ? el.className.trim() : '',
                text: (el.innerText || '').slice(0, 200).trim(),
                selector: getCssSelector(el)
            });
        }
    }

    return {
        url: metadata.url,
        title: metadata.title,
        timestamp: metadata.timestamp,
        visible_text: visibleTextBlocks,
        buttons: buttons,
        links: links,
        forms: forms,
        checkboxes: checkboxes,
        prices: prices,
        cart_items: cartItems,
        urgency_elements: urgencyElements,
        modals: modals,
        summary: {
            total_text_blocks: visibleTextBlocks.length,
            total_buttons: buttons.length,
            total_links: links.length,
            total_forms: forms.length,
            total_checkboxes: checkboxes.length,
            total_prices: prices.length,
            total_cart_items: cartItems.length,
            total_urgency_elements: urgencyElements.length,
            total_modals: modals.length
        }
    };
}
"""


def extract_page_data(page) -> Dict[str, Any]:
    """
    Extracts structured page data from an active Playwright page instance.
    Executes in-browser JavaScript extraction and returns structured data.
    Safely falls back if any unexpected page structure or exception occurs.
    """
    try:
        data = page.evaluate(EXTRACTION_SCRIPT)
        if isinstance(data, dict):
            return data
    except Exception as e:
        logger.warning(f"Error during in-browser structured data extraction: {e}")

    try:
        url = page.url
        title = page.title()
    except Exception:
        url = ""
        title = ""

    return {
        "url": url,
        "title": title,
        "timestamp": datetime.now().isoformat(),
        "visible_text": [],
        "buttons": [],
        "links": [],
        "forms": [],
        "checkboxes": [],
        "prices": [],
        "cart_items": [],
        "urgency_elements": [],
        "modals": [],
        "summary": {
            "total_text_blocks": 0,
            "total_buttons": 0,
            "total_links": 0,
            "total_forms": 0,
            "total_checkboxes": 0,
            "total_prices": 0,
            "total_cart_items": 0,
            "total_urgency_elements": 0,
            "total_modals": 0,
        },
    }
