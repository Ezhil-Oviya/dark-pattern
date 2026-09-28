import collections
import json
import logging
import re
import time
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from playwright.sync_api import sync_playwright

from app.models.evidence_model import AuditSummary, PageSummary
from app.services.automation.audit_session_manager import AuditSession, session_manager
from app.services.automation.data_extractor import extract_page_data
from app.services.dark_patterns.detection_service import (
    aggregate_detection_findings,
    run_dark_pattern_detection,
)
from app.services.evidence.evidence_service import create_evidence_record
from app.services.evidence.mongodb_evidence_service import (
    save_audit_to_mongodb,
    store_artifact_in_gridfs,
)

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path("artifacts")


def _safe_store_gridfs(content: bytes, filename: str, content_type: str, metadata: dict = None) -> str:
    try:
        return store_artifact_in_gridfs(content, filename, content_type, metadata)
    except Exception as e:
        logger.warning(f"Could not persist '{filename}' to GridFS (will use local fallback): {e}")
        return ""


# Common tracking parameters to strip during URL normalization
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "ref",
    "ref_",
    "_ga",
    "ncid",
}

# Non-HTML file extensions to ignore during crawling
IGNORED_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".ico",
    ".zip",
    ".tar",
    ".gz",
    ".mp4",
    ".mp3",
    ".avi",
    ".mov",
    ".css",
    ".js",
    ".json",
    ".xml",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
}

# Sensitive / non-auditable path patterns to avoid during normal BFS queue expansion
EXCLUDED_PATH_PATTERNS = [
    r"/logout",
    r"/login",
    r"/signin",
    r"/signout",
    r"/auth",
    r"/cart",
    r"/checkout",
    r"/account",
    r"/my-account",
    r"/password",
    r"/reset-password",
    r"/signup",
    r"/register",
]

# Authentication URL patterns for dual-layer checkpoint detection
AUTH_URL_PATTERNS = [
    r"/login",
    r"/signin",
    r"/sign-in",
    r"/log-in",
    r"/account/login",
    r"/users/sign_in",
    r"/auth",
    r"/session/new",
    r"/my-account/login",
    r"/customer/account/login",
]

# Generic candidate selectors for e-commerce Product -> Cart workflow
GENERIC_ADD_TO_CART_SELECTORS = [
    'button:has-text("Add to Cart")',
    'button:has-text("Add to Bag")',
    'button:has-text("Add to Basket")',
    'button:has-text("ADD TO CART")',
    'button:has-text("ADD TO BAG")',
    'a:has-text("Add to Cart")',
    'a:has-text("Add to Bag")',
    'input[value*="Add to Cart" i]',
    'input[value*="Add to Bag" i]',
    '[aria-label*="Add to Cart" i]',
    '[aria-label*="Add to Bag" i]',
    "#add-to-cart-button",
    ".add-to-cart",
    ".btn-add-to-cart",
    '[data-testid*="add-to-cart"]',
    '[data-testid*="add-to-bag"]',
]

GENERIC_CART_SELECTORS = [
    'a:has-text("View Cart")',
    'a:has-text("Go to Cart")',
    'a:has-text("View Bag")',
    'a:has-text("Go to Bag")',
    'a:has-text("Cart")',
    'a:has-text("Bag")',
    'button:has-text("View Cart")',
    'button:has-text("Go to Cart")',
    'button:has-text("View Bag")',
    'a[href*="/cart"]',
    'a[href*="/bag"]',
    'a[href*="/basket"]',
    '#cart',
    '.cart-icon',
    '[data-testid*="cart-button"]',
    '[data-testid*="shopping-bag"]',
]

GENERIC_PRODUCT_LINK_SELECTORS = [
    'a[href*="/p/"]',
    'a[href*="/product/"]',
    'a[href*="/product-"]',
    'a[href*="/dp/"]',
    'a[href*="/buy/"]',
    'a[href*="/item/"]',
    '.product-card a',
    '.product-item a',
    '[data-testid*="product"] a',
    'a:has([class*="price"])',
]


def _normalize_url(href: str, base_url: str, allowed_domain: str) -> Optional[str]:
    """
    Normalizes a discovered URL, resolves relative paths, strips tracking parameters
    and fragments, and ensures it belongs to the allowed same domain.
    """
    if not href or href.strip().startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
        return None

    try:
        joined = urllib.parse.urljoin(base_url, href.strip())
        parsed = urllib.parse.urlparse(joined)

        if parsed.scheme.lower() not in ("http", "https"):
            return None

        original_netloc = parsed.netloc.lower()
        hostname = parsed.hostname.lower() if parsed.hostname else original_netloc

        clean_allowed = allowed_domain.replace("www.", "").lower()
        clean_hostname = hostname.replace("www.", "")

        if clean_hostname != clean_allowed:
            return None

        path_lower = parsed.path.lower()
        if any(path_lower.endswith(ext) for ext in IGNORED_EXTENSIONS):
            return None

        if any(re.search(pat, path_lower) for pat in EXCLUDED_PATH_PATTERNS):
            return None

        query_params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=False)
        cleaned_params = [
            (k, v) for k, v in query_params if k.lower() not in TRACKING_PARAMS
        ]
        new_query = urllib.parse.urlencode(cleaned_params)

        path = parsed.path
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]
        elif not path:
            path = "/"

        normalized = urllib.parse.urlunparse(
            (parsed.scheme.lower(), original_netloc, path, "", new_query, "")
        )
        return normalized
    except Exception as e:
        logger.debug(f"Error normalizing URL '{href}': {e}")
        return None


def detect_authentication_required(page, url: str) -> Tuple[bool, str]:
    """
    Dual-layer authentication detection:
    1. URL signals (/login, /signin, query params like next=/login)
    2. DOM/Content signals (visible password fields, login forms, gating text)
    """
    try:
        parsed = urllib.parse.urlparse(url)
        path_lower = parsed.path.lower()
        query_lower = parsed.query.lower()

        # 1. URL pattern matching
        for pat in AUTH_URL_PATTERNS:
            if re.search(pat, path_lower):
                return True, f"Authentication URL pattern detected ('{pat}' in path '{path_lower}')"

        if any(k in query_lower for k in ["redirect_to=login", "next=/login", "return_to=", "login_required"]):
            return True, f"Authentication redirect parameter in URL query: '{parsed.query}'"

        # 2. DOM signals
        dom_signals = page.evaluate("""() => {
            const hasVisiblePassword = Array.from(document.querySelectorAll('input[type="password"]')).some(el => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
            });

            const hasLoginForm = Array.from(document.querySelectorAll('form')).some(f => {
                const act = (f.getAttribute('action') || '').toLowerCase();
                const idOrClass = ((f.id || '') + ' ' + (f.className || '')).toLowerCase();
                return /login|signin|sign-in|auth/i.test(act + ' ' + idOrClass);
            });

            const pageText = (document.body ? document.body.innerText : '').slice(0, 2000);
            const authTextMatch = /(?:sign\\s+in\\s+to\\s+continue|log\\s*in\\s+to\\s+your\\s+account|login\\s+to\\s+continue|enter\\s+(?:your\\s+)?(?:mobile\\s+number|email|phone)\\s+to\\s+(?:sign\\s*in|log\\s*in)|login\\s+with\\s+otp|please\\s+log\\s*in|login\\s+or\\s+signup)/i.test(pageText);

            return {
                hasVisiblePassword,
                hasLoginForm,
                authTextMatch
            };
        }""")

        if dom_signals.get("hasVisiblePassword"):
            return True, "Visible password input field detected on page (DOM signal)"
        if dom_signals.get("hasLoginForm") and dom_signals.get("authTextMatch"):
            return True, "Login form and authentication gating text detected in DOM"
    except Exception as e:
        logger.debug(f"Auth detection evaluation warning: {e}")

    return False, ""


def detect_authentication_success(page, start_login_url: str = "") -> Tuple[bool, str]:
    """
    Evaluates whether the user has successfully completed authentication.
    Checks:
    1. Login form / password fields disappeared
    2. URL navigated away from login/auth endpoints
    3. Account/Profile/Logout elements appeared
    """
    try:
        current_url = page.url
        parsed = urllib.parse.urlparse(current_url)
        path_lower = parsed.path.lower()

        # If still explicitly on a login path, authentication is not complete
        for pat in AUTH_URL_PATTERNS:
            if re.search(pat, path_lower) and not re.search(r"/account(?:/|$)", path_lower):
                return False, f"Still on login URL path: {path_lower}"

        eval_result = page.evaluate("""() => {
            const visiblePasswordCount = Array.from(document.querySelectorAll('input[type="password"]')).filter(el => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
            }).length;

            const logoutPresent = Array.from(document.querySelectorAll('a, button, [role="button"], span, div')).some(el => {
                const txt = (el.innerText || '').trim();
                return /^(?:log\\s*out|sign\\s*out|my\\s+account|my\\s+profile|your\\s+account|orders)$/i.test(txt);
            });

            const accountMenuPresent = document.querySelector('[data-testid*="user-menu"], [class*="user-menu"], [id*="account-menu"], [class*="profile-dropdown"], [class*="user-profile"]') !== null;

            return {
                visiblePasswordCount,
                logoutPresent,
                accountMenuPresent
            };
        }""")

        pw_count = eval_result.get("visiblePasswordCount", 0)
        if pw_count > 0:
            return False, f"{pw_count} password input(s) still visible on page"

        if eval_result.get("logoutPresent") or eval_result.get("accountMenuPresent"):
            return True, "User account / profile / logout navigation element detected in DOM"

        if start_login_url and current_url != start_login_url:
            return True, f"Navigated away from login URL to {current_url}"

        is_login_path = any(re.search(pat, path_lower) for pat in AUTH_URL_PATTERNS)
        if not is_login_path and pw_count == 0:
            return True, f"Page URL '{current_url}' is not a login page and has no password inputs"
    except Exception as e:
        logger.debug(f"Auth success check warning: {e}")

    return False, "Authentication state inconclusive"


def handle_authentication_checkpoint(
    page,
    session: AuditSession,
    current_url: str,
    timeout_sec: int = 300,
    check_immediately: bool = True
) -> bool:
    """
    Pauses the crawl when authentication is required and awaits manual login in the visible browser session.
    Automatically detects successful login or responds to manual [Resume Audit] API trigger.
    """
    if check_immediately:
        is_req, reason = detect_authentication_required(page, current_url)
        if not is_req:
            return True
    else:
        reason = "Website configuration specifies login is required"

    logger.info(f"[CHECKPOINT] Authentication Required at {current_url}: {reason}")
    session.request_authentication(current_url, reason)

    start_wait = time.time()
    while time.time() - start_wait < timeout_sec:
        # Check if user clicked manual Resume button via API
        if session.resume_event.is_set():
            # Verify if authentication actually succeeded
            auth_ok, auth_msg = detect_authentication_success(page, start_login_url=current_url)
            if auth_ok:
                logger.info(f"[CHECKPOINT] User manually triggered resume and authentication verified: {auth_msg}")
                session.signal_resume(source="manual_button")
                return True
            else:
                logger.warning(f"[CHECKPOINT] User triggered resume but authentication not verified: {auth_msg}. Remaining in checkpoint.")
                session.resume_event.clear()

        # Check for automatic authentication detection
        auth_ok, auth_msg = detect_authentication_success(page, start_login_url=current_url)
        if auth_ok:
            logger.info(f"[CHECKPOINT] Automatic login completion detected: {auth_msg}")
            session.signal_resume(source="automatic_detection")
            return True

        # Sleep briefly to avoid tight polling loop
        time.sleep(1.5)

    logger.warning(f"[CHECKPOINT] Authentication checkpoint timed out after {timeout_sec}s.")
    return False


def execute_cart_workflow(
    page,
    context,
    website: Dict[str, Any],
    audit_id: str,
    audit_folder: Path,
    start_time: str,
    session: AuditSession,
    page_index: int = 900
) -> Optional[Dict[str, Any]]:
    """
    Controlled E-commerce Product -> Cart Workflow for Basket Sneaking:
    1. Identify product page (or navigate to product).
    2. Identify 'Add to Cart' / 'Add to Bag' button (strictly avoiding 'Buy Now').
    3. Click Add to Cart.
    4. Wait for cart update.
    5. Navigate to Cart / Bag page.
    6. Inspect optional add-ons, warranties, insurance, subscriptions, preselected checkboxes.
    7. Capture initial vs final preselection state.
    8. Run AI MiniLM classification + DOM state validation.
    9. CRITICAL SAFETY BOUNDARY: Stop strictly at cart review before payment / checkout forms.
    """
    platform = website.get("platform", "Platform")
    custom_add_selectors = website.get("add_to_cart_selectors") or []
    custom_cart_selectors = website.get("cart_selectors") or []

    logger.info(f"[CART_WORKFLOW] Starting controlled Product -> Cart workflow for {platform}")
    session.current_stage = "E-commerce Cart Workflow: Identifying product and Add to Cart"

    try:
        # Step 1: Ensure we are on a Product Page
        add_btn = None
        all_add_selectors = custom_add_selectors + GENERIC_ADD_TO_CART_SELECTORS

        for sel in all_add_selectors:
            try:
                locator = page.locator(sel).first
                if locator.is_visible(timeout=1500):
                    add_btn = locator
                    logger.info(f"[CART_WORKFLOW] Found Add to Cart button using selector: '{sel}'")
                    break
            except Exception:
                continue

        # If not already on product page, search for a product link on current page
        if not add_btn:
            logger.info("[CART_WORKFLOW] Not currently on product page. Searching for product link...")
            product_link_found = False
            for p_sel in GENERIC_PRODUCT_LINK_SELECTORS:
                try:
                    p_loc = page.locator(p_sel).first
                    if p_loc.is_visible(timeout=1500):
                        href = p_loc.get_attribute("href")
                        if href:
                            logger.info(f"[CART_WORKFLOW] Navigating to product: {href}")
                            p_loc.click()
                            page.wait_for_load_state("domcontentloaded", timeout=15000)
                            try:
                                page.wait_for_load_state("networkidle", timeout=5000)
                            except Exception:
                                pass
                            product_link_found = True
                            break
                except Exception:
                    continue

            if product_link_found:
                # Re-check for Add to Cart button on the newly opened product page
                for sel in all_add_selectors:
                    try:
                        locator = page.locator(sel).first
                        if locator.is_visible(timeout=2000):
                            add_btn = locator
                            logger.info(f"[CART_WORKFLOW] Found Add to Cart button on product page: '{sel}'")
                            break
                    except Exception:
                        continue

        if not add_btn:
            logger.warning("[CART_WORKFLOW] Could not locate an 'Add to Cart' button. Skipping cart workflow.")
            return None

        # Step 2: Handle possible Authentication Checkpoint on Product Page
        if website.get("login_required") or detect_authentication_required(page, page.url)[0]:
            checkpoint_passed = handle_authentication_checkpoint(page, session, page.url)
            if not checkpoint_passed:
                logger.warning("[CART_WORKFLOW] Authentication checkpoint not completed.")
                return None

        # Step 3: Click Add to Cart
        session.current_stage = "E-commerce Cart Workflow: Clicking Add to Cart"
        logger.info("[CART_WORKFLOW] Clicking 'Add to Cart' button...")
        add_btn.click()
        page.wait_for_timeout(2500)

        # Step 4: Navigate to Cart / Bag
        session.current_stage = "E-commerce Cart Workflow: Navigating to Cart"
        cart_navigated = False
        all_cart_selectors = custom_cart_selectors + GENERIC_CART_SELECTORS

        for c_sel in all_cart_selectors:
            try:
                c_loc = page.locator(c_sel).first
                if c_loc.is_visible(timeout=1500):
                    logger.info(f"[CART_WORKFLOW] Clicking Cart navigation element: '{c_sel}'")
                    c_loc.click()
                    page.wait_for_load_state("domcontentloaded", timeout=15000)
                    try:
                        page.wait_for_load_state("networkidle", timeout=5000)
                    except Exception:
                        pass
                    cart_navigated = True
                    break
            except Exception:
                continue

        if not cart_navigated:
            # Fallback direct cart URL navigation
            cart_url = urllib.parse.urljoin(page.url, "/cart")
            logger.info(f"[CART_WORKFLOW] Direct fallback navigation to {cart_url}")
            try:
                page.goto(cart_url, wait_until="domcontentloaded", timeout=15000)
                cart_navigated = True
            except Exception as e:
                logger.warning(f"[CART_WORKFLOW] Could not navigate directly to cart: {e}")

        # Step 5: Handle Auth Checkpoint on Cart Page if gated
        if detect_authentication_required(page, page.url)[0]:
            checkpoint_passed = handle_authentication_checkpoint(page, session, page.url)
            if not checkpoint_passed:
                logger.warning("[CART_WORKFLOW] Cart login checkpoint not completed.")
                return None

        # Step 6: Extract and Inspect Cart Page
        session.current_stage = "E-commerce Cart Workflow: Inspecting Cart for Basket Sneaking"
        cart_url = page.url
        logger.info(f"[CART_WORKFLOW] Inspecting Cart Page: {cart_url}")

        page_dir = audit_folder / "cart_inspection"
        page_dir.mkdir(parents=True, exist_ok=True)

        screenshot_path = page_dir / "screenshot.png"
        dom_path = page_dir / "dom.html"
        extracted_path = page_dir / "extracted.json"
        evidence_path = page_dir / "evidence.json"

        # Capture Cart Screenshot
        screenshot_bytes = page.screenshot(full_page=True)
        with open(screenshot_path, "wb") as f:
            f.write(screenshot_bytes)

        screenshot_file_id = _safe_store_gridfs(
            content=screenshot_bytes,
            filename=f"{audit_id}_cart_screenshot.png",
            content_type="image/png",
            metadata={"audit_id": audit_id, "page_index": page_index, "url": cart_url}
        )

        # Capture Cart DOM
        html_content = page.content()
        with open(dom_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        dom_file_id = _safe_store_gridfs(
            content=html_content.encode("utf-8"),
            filename=f"{audit_id}_cart_dom.html",
            content_type="text/html",
            metadata={"audit_id": audit_id, "page_index": page_index, "url": cart_url}
        )

        # Extract structured data
        extracted_data = extract_page_data(page)

        # Flag all checkboxes on cart load as preselected if checked before user interaction
        for cb in extracted_data.get("checkboxes", []):
            if cb.get("checked"):
                cb["preselected_before_interaction"] = True
                cb["selection_origin"] = "preselected"

        extracted_json_bytes = json.dumps(extracted_data, indent=2, ensure_ascii=False).encode("utf-8")
        with open(extracted_path, "wb") as f:
            f.write(extracted_json_bytes)

        extracted_file_id = _safe_store_gridfs(
            content=extracted_json_bytes,
            filename=f"{audit_id}_cart_extracted.json",
            content_type="application/json",
            metadata={"audit_id": audit_id, "page_index": page_index, "url": cart_url}
        )

        # Build evidence record
        evidence_record = create_evidence_record(
            website=website,
            audit_time=start_time,
            screenshot_path=screenshot_path,
            dom_path=dom_path,
            extracted_path=extracted_path,
            evidence_path=evidence_path,
            extracted_data=extracted_data,
            audit_id=audit_id,
            crawl_depth=1,
            page_index=page_index,
        )

        evidence_json_bytes = json.dumps(evidence_record, indent=2, ensure_ascii=False).encode("utf-8")
        with open(evidence_path, "wb") as f:
            f.write(evidence_json_bytes)

        evidence_file_id = _safe_store_gridfs(
            content=evidence_json_bytes,
            filename=f"{audit_id}_cart_evidence.json",
            content_type="application/json",
            metadata={"audit_id": audit_id, "page_index": page_index, "url": cart_url}
        )

        # Run dark pattern detection (especially Basket Sneaking AI)
        cart_detections = run_dark_pattern_detection(
            extracted_data=extracted_data,
            evidence_record=evidence_record
        )

        findings_count = sum(1 for d in cart_detections if d.get("detected", False))

        artifact_endpoints = {
            "screenshot": f"api/v1/automation/artifact/{screenshot_file_id}" if screenshot_file_id else f"artifacts/{platform}/{audit_id}/cart_inspection/screenshot.png",
            "dom": f"api/v1/automation/artifact/{dom_file_id}" if dom_file_id else f"artifacts/{platform}/{audit_id}/cart_inspection/dom.html",
            "extracted_json": f"api/v1/automation/artifact/{extracted_file_id}" if extracted_file_id else f"artifacts/{platform}/{audit_id}/cart_inspection/extracted.json",
            "evidence_json": f"api/v1/automation/artifact/{evidence_file_id}" if evidence_file_id else f"artifacts/{platform}/{audit_id}/cart_inspection/evidence.json",
        }

        page_summary_item = {
            "audit_id": audit_id,
            "page_index": page_index,
            "folder": "cart_inspection",
            "url": cart_url,
            "title": "Shopping Cart Inspection",
            "depth": 1,
            "status": "success",
            "error": None,
            "evidence_count": len(evidence_record.get("evidence_items", [])),
            "findings_count": findings_count,
            "artifacts": artifact_endpoints,
            "detections": cart_detections,
        }

        logger.info(f"[CART_WORKFLOW] Cart inspection complete. Detections count: {findings_count}")
        return {
            "page_summary": page_summary_item,
            "evidence_items": evidence_record.get("evidence_items", []),
            "page_record": {
                "page_index": page_index,
                "url": cart_url,
                "depth": 1,
                "detections": cart_detections,
            }
        }

    except Exception as e:
        logger.error(f"[CART_WORKFLOW] Error during cart workflow: {e}", exc_info=True)
        return None


def run_crawler(website: Dict[str, Any], audit_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Executes BFS multi-page website crawling, interactive authentication checkpoints,
    and controlled E-commerce Product -> Cart workflows for Basket Sneaking detection.
    """
    platform = website.get("platform", "Platform")
    start_url = website.get("url", "").strip()
    configured_depth = int(website.get("crawl_depth", 0))
    max_pages = int(website.get("max_pages", 50))
    login_required = bool(website.get("login_required", False))
    # Headless mode: If login_required is True, launch headed so user can interact!
    headless = False if login_required else bool(website.get("headless", True))
    cart_workflow_enabled = bool(website.get("cart_workflow_enabled", True))
    category = (website.get("category") or "Ecommerce").lower()
    website_id = str(website.get("id") or website.get("_id") or "")

    start_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    if not audit_id:
        audit_id = f"audit_{platform.lower().replace(' ', '_')}_{start_time}"

    audit_folder = ARTIFACTS_DIR / platform / audit_id
    audit_folder.mkdir(parents=True, exist_ok=True)

    # Initialize AuditSession
    session = session_manager.create_session(audit_id, website)

    parsed_start = urllib.parse.urlparse(start_url)
    start_domain = (parsed_start.hostname or parsed_start.netloc).lower()
    normalized_start = _normalize_url(start_url, start_url, start_domain) or start_url

    logger.info(
        f"Starting Audit '{audit_id}' for {platform} at {normalized_start} "
        f"(Depth: {configured_depth}, Max Pages: {max_pages}, Headless: {headless}, LoginRequired: {login_required})"
    )

    queue = collections.deque([{"url": normalized_start, "depth": 0}])
    queued_urls: Set[str] = {normalized_start}
    visited_urls: Set[str] = set()

    pages_summary: List[Dict[str, Any]] = []
    page_records: List[Dict[str, Any]] = []
    all_evidence_items_to_persist: List[Dict[str, Any]] = []

    actual_max_depth_reached = 0
    pages_successful = 0
    pages_failed = 0
    total_evidence_items = 0
    cart_workflow_executed = False

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()

            page_index = 0

            try:
                # 1. BFS Multi-Page Crawl Loop
                while queue and len(visited_urls) < max_pages:
                    current = queue.popleft()
                    current_url = current["url"]
                    current_depth = current["depth"]

                    if current_url in visited_urls:
                        continue
                    if current_depth > configured_depth:
                        continue

                    visited_urls.add(current_url)
                    actual_max_depth_reached = max(actual_max_depth_reached, current_depth)
                    session.current_url = current_url
                    session.page_index = page_index
                    session.current_stage = f"Crawling page {page_index + 1}/{max_pages}: {current_url}"

                    page_folder_name = f"page_{page_index:03d}"
                    page_dir = audit_folder / page_folder_name
                    page_dir.mkdir(parents=True, exist_ok=True)

                    screenshot_path = page_dir / "screenshot.png"
                    dom_path = page_dir / "dom.html"
                    extracted_path = page_dir / "extracted.json"
                    evidence_path = page_dir / "evidence.json"

                    logger.info(f"Crawling [depth={current_depth}] ({page_index + 1}/{max_pages}): {current_url}")

                    try:
                        # 1. Navigate to target page
                        page.goto(current_url, wait_until="domcontentloaded", timeout=45000)
                        try:
                            page.wait_for_load_state("networkidle", timeout=8000)
                        except Exception:
                            pass

                        # 2. Check for Authentication Checkpoint
                        if page_index == 0 and login_required:
                            handle_authentication_checkpoint(page, session, page.url, check_immediately=False)
                        else:
                            is_auth, _ = detect_authentication_required(page, page.url)
                            if is_auth:
                                handle_authentication_checkpoint(page, session, page.url, check_immediately=True)

                        final_url = page.url
                        page_title = page.title() or ""

                        # 3. Capture Screenshot
                        screenshot_bytes = page.screenshot(full_page=True)
                        with open(screenshot_path, "wb") as f:
                            f.write(screenshot_bytes)

                        screenshot_file_id = _safe_store_gridfs(
                            content=screenshot_bytes,
                            filename=f"{audit_id}_page_{page_index:03d}_screenshot.png",
                            content_type="image/png",
                            metadata={"audit_id": audit_id, "page_index": page_index, "url": final_url}
                        )

                        # 4. Rendered DOM
                        html_content = page.content()
                        with open(dom_path, "w", encoding="utf-8") as f:
                            f.write(html_content)

                        dom_file_id = _safe_store_gridfs(
                            content=html_content.encode("utf-8"),
                            filename=f"{audit_id}_page_{page_index:03d}_dom.html",
                            content_type="text/html",
                            metadata={"audit_id": audit_id, "page_index": page_index, "url": final_url}
                        )

                        # 5. Structured Data Extraction (Module 3)
                        extracted_data = extract_page_data(page)

                        extracted_json_bytes = json.dumps(extracted_data, indent=2, ensure_ascii=False).encode("utf-8")
                        with open(extracted_path, "wb") as f:
                            f.write(extracted_json_bytes)

                        extracted_file_id = _safe_store_gridfs(
                            content=extracted_json_bytes,
                            filename=f"{audit_id}_page_{page_index:03d}_extracted.json",
                            content_type="application/json",
                            metadata={"audit_id": audit_id, "page_index": page_index, "url": final_url}
                        )

                        # 6. Evidence Record Creation (Module 4)
                        evidence_record = create_evidence_record(
                            website=website,
                            audit_time=start_time,
                            screenshot_path=screenshot_path,
                            dom_path=dom_path,
                            extracted_path=extracted_path,
                            evidence_path=evidence_path,
                            extracted_data=extracted_data,
                            audit_id=audit_id,
                            crawl_depth=current_depth,
                            page_index=page_index,
                        )

                        evidence_json_bytes = json.dumps(evidence_record, indent=2, ensure_ascii=False).encode("utf-8")
                        with open(evidence_path, "wb") as f:
                            f.write(evidence_json_bytes)

                        evidence_file_id = _safe_store_gridfs(
                            content=evidence_json_bytes,
                            filename=f"{audit_id}_page_{page_index:03d}_evidence.json",
                            content_type="application/json",
                            metadata={"audit_id": audit_id, "page_index": page_index, "url": final_url}
                        )

                        # 7. Dark Pattern Detection (Module 5)
                        page_detections = run_dark_pattern_detection(
                            extracted_data=extracted_data,
                            evidence_record=evidence_record,
                        )

                        # 8. Extract Internal Links for Next Depth Level
                        if current_depth < configured_depth and len(visited_urls) < max_pages:
                            links = extracted_data.get("links", [])
                            for link_item in links:
                                href = link_item.get("href")
                                if href:
                                    norm = _normalize_url(href, final_url, start_domain)
                                    if norm and norm not in visited_urls and norm not in queued_urls:
                                        queued_urls.add(norm)
                                        queue.append({"url": norm, "depth": current_depth + 1})

                        ev_items = evidence_record.get("evidence_items", [])
                        ev_count = len(ev_items)
                        total_evidence_items += ev_count
                        all_evidence_items_to_persist.extend(ev_items)

                        findings_count = sum(1 for d in page_detections if d.get("detected", False))
                        pages_successful += 1

                        artifact_endpoints = {
                            "screenshot": f"api/v1/automation/artifact/{screenshot_file_id}" if screenshot_file_id else f"artifacts/{platform}/{audit_id}/{page_folder_name}/screenshot.png",
                            "dom": f"api/v1/automation/artifact/{dom_file_id}" if dom_file_id else f"artifacts/{platform}/{audit_id}/{page_folder_name}/dom.html",
                            "extracted_json": f"api/v1/automation/artifact/{extracted_file_id}" if extracted_file_id else f"artifacts/{platform}/{audit_id}/{page_folder_name}/extracted.json",
                            "evidence_json": f"api/v1/automation/artifact/{evidence_file_id}" if evidence_file_id else f"artifacts/{platform}/{audit_id}/{page_folder_name}/evidence.json",
                        }

                        page_summary_item = {
                            "audit_id": audit_id,
                            "page_index": page_index,
                            "folder": page_folder_name,
                            "url": final_url,
                            "title": page_title,
                            "depth": current_depth,
                            "status": "success",
                            "error": None,
                            "evidence_count": ev_count,
                            "findings_count": findings_count,
                            "artifacts": artifact_endpoints,
                            "detections": page_detections,
                        }
                        pages_summary.append(page_summary_item)

                        page_records.append({
                            "page_index": page_index,
                            "url": final_url,
                            "depth": current_depth,
                            "detections": page_detections,
                        })

                    except Exception as e:
                        logger.warning(f"Error crawling {current_url} at depth {current_depth}: {e}")
                        pages_failed += 1
                        pages_summary.append({
                            "audit_id": audit_id,
                            "page_index": page_index,
                            "folder": page_folder_name,
                            "url": current_url,
                            "title": "Failed Page",
                            "depth": current_depth,
                            "status": "failed",
                            "error": str(e),
                            "evidence_count": 0,
                            "findings_count": 0,
                            "artifacts": {},
                            "detections": [],
                        })

                    page_index += 1

                # 2. Controlled E-commerce Product -> Cart Workflow (for Basket Sneaking)
                if cart_workflow_enabled and (category in ("ecommerce", "retail", "shopping") or website.get("cart_workflow_enabled")):
                    cart_result = execute_cart_workflow(
                        page=page,
                        context=context,
                        website=website,
                        audit_id=audit_id,
                        audit_folder=audit_folder,
                        start_time=start_time,
                        session=session,
                        page_index=page_index
                    )
                    if cart_result:
                        cart_workflow_executed = True
                        pages_summary.append(cart_result["page_summary"])
                        page_records.append(cart_result["page_record"])
                        cart_ev = cart_result["evidence_items"]
                        all_evidence_items_to_persist.extend(cart_ev)
                        total_evidence_items += len(cart_ev)
                        if cart_result["page_summary"]["status"] == "success":
                            pages_successful += 1

            finally:
                context.close()
                browser.close()

    except Exception as e:
        logger.error(f"Fatal error in Playwright runner for audit '{audit_id}': {e}", exc_info=True)
        session.fail_session(audit_id, str(e))
        raise

    end_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # 3. Aggregate dark pattern findings across all crawled pages (including cart inspection)
    dark_pattern_summary = aggregate_detection_findings(page_records)
    total_dark_pattern_findings = sum(
        d.get("total_instances", 0) for d in dark_pattern_summary if d.get("detected", False)
    )

    # 4. Build complete AuditSummary
    audit_summary = {
        "audit_id": audit_id,
        "website_id": website_id,
        "platform": platform,
        "start_url": start_url,
        "configured_crawl_depth": configured_depth,
        "actual_max_depth_reached": actual_max_depth_reached,
        "max_pages_limit": max_pages,
        "pages_discovered": len(queued_urls),
        "pages_crawled": len(pages_summary),
        "pages_successful": pages_successful,
        "pages_failed": pages_failed,
        "total_evidence_items": total_evidence_items,
        "total_dark_pattern_findings": total_dark_pattern_findings,
        "start_time": start_time,
        "end_time": end_time,
        "status": "completed",
        "authentication_required": session.authentication_required,
        "authentication_status": session.authentication_status,
        "cart_workflow_executed": cart_workflow_executed,
        "dark_pattern_summary": dark_pattern_summary,
        "pages": pages_summary,
    }

    # Complete session in session manager
    session_manager.complete_session(audit_id, audit_summary)

    # 5. Persist entire audit session to MongoDB
    try:
        save_audit_to_mongodb(
            audit_summary=audit_summary,
            pages_data=pages_summary,
            evidence_items_list=all_evidence_items_to_persist
        )
    except Exception as e:
        logger.error(f"Failed to persist audit to MongoDB: {e}", exc_info=True)

    # 6. Write summary to local file backup
    summary_path = audit_folder / "audit_summary.json"
    try:
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(audit_summary, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to persist local audit_summary.json: {e}")

    logger.info(
        f"Audit '{audit_id}' completed and stored. Crawled {len(pages_summary)} pages "
        f"({pages_successful} successful, {pages_failed} failed). "
        f"Auth Required: {session.authentication_required}, Cart Workflow: {cart_workflow_executed}, "
        f"Total Evidence Items: {total_evidence_items}, Total Findings: {total_dark_pattern_findings}."
    )

    return audit_summary
