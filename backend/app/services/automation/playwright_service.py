from pathlib import Path
from datetime import datetime

from playwright.sync_api import sync_playwright


ARTIFACTS = Path("artifacts")


def run_browser_audit(website):

    platform = website["platform"]
    url = website["url"]

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    audit_folder = ARTIFACTS / platform / timestamp

    audit_folder.mkdir(parents=True, exist_ok=True)

    screenshot_path = audit_folder / "screenshot.png"
    dom_path = audit_folder / "dom.html"

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=website.get("headless", True)
        )

        page = browser.new_page()

        page.goto(
            url,
            wait_until="networkidle",
            timeout=60000
        )

        title = page.title()

        final_url = page.url

        page.screenshot(
            path=str(screenshot_path),
            full_page=True
        )

        html = page.content()

        with open(dom_path, "w", encoding="utf-8") as f:
            f.write(html)

        browser.close()

    return {

    "status":"completed",

    "platform":platform,

    "final_url":final_url,

    "audit_time":timestamp,

    "screenshot":str(screenshot_path).replace("\\","/"),

    "dom":str(dom_path).replace("\\","/")

}