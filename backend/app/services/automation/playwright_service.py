import logging
from typing import Any, Dict

from app.services.automation.crawler_service import run_crawler

logger = logging.getLogger(__name__)


def run_browser_audit(website: Dict[str, Any]) -> Dict[str, Any]:
    """
    Unified entry point for browser automation and multi-page auditing.
    Delegates to the crawler service to perform real BFS multi-page crawling
    based on configured crawl_depth and max_pages.
    """
    return run_crawler(website)