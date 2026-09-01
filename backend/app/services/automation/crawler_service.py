import collections
import json
import logging
import re
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from playwright.sync_api import sync_playwright

from app.models.evidence_model import AuditSummary, PageSummary
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

# Sensitive / non-auditable path patterns to avoid during normal crawling
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


def run_crawler(website: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes real BFS multi-page website crawling up to configured crawl_depth and max_pages.
    Extracts structured DOM data, builds traceable evidence records, runs the Final Four
    dark pattern detectors, and persists all audit data and GridFS artifacts to MongoDB.
    """
    platform = website.get("platform", "Platform")
    start_url = website.get("url", "").strip()
    configured_depth = int(website.get("crawl_depth", 0))
    max_pages = int(website.get("max_pages", 50))
    headless = bool(website.get("headless", True))
    website_id = str(website.get("id") or website.get("_id") or "")

    start_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    audit_id = f"audit_{platform.lower().replace(' ', '_')}_{start_time}"
    audit_folder = ARTIFACTS_DIR / platform / audit_id
    audit_folder.mkdir(parents=True, exist_ok=True)

    parsed_start = urllib.parse.urlparse(start_url)
    start_domain = (parsed_start.hostname or parsed_start.netloc).lower()

    normalized_start = _normalize_url(start_url, start_url, start_domain) or start_url

    logger.info(
        f"Starting BFS Audit '{audit_id}' for {platform} at {normalized_start} "
        f"(Crawl Depth: {configured_depth}, Max Pages: {max_pages}, Headless: {headless})"
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

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        page_index = 0

        try:
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

                    final_url = page.url
                    page_title = page.title() or ""

                    # 2. Screenshot
                    screenshot_bytes = page.screenshot(full_page=True)
                    with open(screenshot_path, "wb") as f:
                        f.write(screenshot_bytes)

                    # Store screenshot in GridFS
                    screenshot_file_id = store_artifact_in_gridfs(
                        content=screenshot_bytes,
                        filename=f"{audit_id}_page_{page_index:03d}_screenshot.png",
                        content_type="image/png",
                        metadata={"audit_id": audit_id, "page_index": page_index, "url": final_url}
                    )

                    # 3. Rendered DOM
                    html_content = page.content()
                    with open(dom_path, "w", encoding="utf-8") as f:
                        f.write(html_content)

                    # Store DOM in GridFS
                    dom_file_id = store_artifact_in_gridfs(
                        content=html_content.encode("utf-8"),
                        filename=f"{audit_id}_page_{page_index:03d}_dom.html",
                        content_type="text/html",
                        metadata={"audit_id": audit_id, "page_index": page_index, "url": final_url}
                    )

                    # 4. Structured Data Extraction (Module 3)
                    extracted_data = extract_page_data(page)

                    extracted_json_bytes = json.dumps(extracted_data, indent=2, ensure_ascii=False).encode("utf-8")
                    with open(extracted_path, "wb") as f:
                        f.write(extracted_json_bytes)

                    # Store extracted JSON in GridFS
                    extracted_file_id = store_artifact_in_gridfs(
                        content=extracted_json_bytes,
                        filename=f"{audit_id}_page_{page_index:03d}_extracted.json",
                        content_type="application/json",
                        metadata={"audit_id": audit_id, "page_index": page_index, "url": final_url}
                    )

                    # 5. Evidence Record Creation (Module 4)
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

                    # Store evidence JSON in GridFS
                    evidence_file_id = store_artifact_in_gridfs(
                        content=evidence_json_bytes,
                        filename=f"{audit_id}_page_{page_index:03d}_evidence.json",
                        content_type="application/json",
                        metadata={"audit_id": audit_id, "page_index": page_index, "url": final_url}
                    )

                    # 6. Dark Pattern Detection (Module 5) on this page
                    page_detections = run_dark_pattern_detection(
                        extracted_data=extracted_data,
                        evidence_record=evidence_record,
                    )

                    # 7. Extract Internal Links for Next Depth Level
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

                    # Construct MongoDB GridFS artifact streaming references
                    artifact_endpoints = {
                        "screenshot": f"api/v1/automation/artifact/{screenshot_file_id}",
                        "dom": f"api/v1/automation/artifact/{dom_file_id}",
                        "extracted_json": f"api/v1/automation/artifact/{extracted_file_id}",
                        "evidence_json": f"api/v1/automation/artifact/{evidence_file_id}",
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
        finally:
            context.close()
            browser.close()

    end_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # 8. Aggregate dark pattern findings across all crawled pages
    dark_pattern_summary = aggregate_detection_findings(page_records)
    total_dark_pattern_findings = sum(
        d.get("total_instances", 0) for d in dark_pattern_summary if d.get("detected", False)
    )

    # 9. Build complete AuditSummary
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
        "dark_pattern_summary": dark_pattern_summary,
        "pages": pages_summary,
    }

    # 10. Persist entire audit session to MongoDB (audits, pages, evidence_items)
    try:
        save_audit_to_mongodb(
            audit_summary=audit_summary,
            pages_data=pages_summary,
            evidence_items_list=all_evidence_items_to_persist
        )
    except Exception as e:
        logger.error(f"Failed to persist audit to MongoDB: {e}", exc_info=True)

    # 11. Also write summary to local file for filesystem diagnostic backup
    summary_path = audit_folder / "audit_summary.json"
    try:
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(audit_summary, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to persist local audit_summary.json: {e}")

    logger.info(
        f"Audit '{audit_id}' completed and stored in MongoDB. Crawled {len(pages_summary)} pages "
        f"({pages_successful} successful, {pages_failed} failed). "
        f"Total Evidence Items: {total_evidence_items}, Total Findings: {total_dark_pattern_findings}."
    )

    return audit_summary
