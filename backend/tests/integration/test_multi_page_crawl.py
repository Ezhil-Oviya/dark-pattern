import http.server
import json
import os
import socketserver
import sys
import threading
import unittest
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.services.automation.crawler_service import run_crawler
from app.services.evidence.mongodb_evidence_service import get_audit_details_from_mongodb

# HTML pages for multi-level crawl testing
PAGES = {
    "/": """
        <html>
            <head><title>Level 0 Homepage</title></head>
            <body>
                <h1>Homepage</h1>
                <a href="/level1_a">Page 1A</a>
                <a href="/level1_b">Page 1B</a>
                <a href="/level1_a">Duplicate Link 1A</a>
                <a href="https://external-forbidden.com/exit">External Link</a>
            </body>
        </html>
    """,
    "/level1_a": """
        <html>
            <head><title>Level 1A</title></head>
            <body>
                <h1>Level 1A</h1>
                <a href="/level2_a">Page 2A</a>
                <a href="/">Back to Home</a>
            </body>
        </html>
    """,
    "/level1_b": """
        <html>
            <head><title>Level 1B</title></head>
            <body>
                <h1>Level 1B</h1>
                <span class="timer">04:35 left before deal ends</span>
                <a href="/level2_b">Page 2B</a>
            </body>
        </html>
    """,
    "/level2_a": """
        <html>
            <head><title>Level 2A</title></head>
            <body>
                <h1>Level 2A</h1>
                <a href="/level3_a">Page 3A</a>
            </body>
        </html>
    """,
    "/level2_b": """
        <html>
            <head><title>Level 2B</title></head>
            <body>
                <h1>Level 2B</h1>
                <form id="opt-form">
                    <label><input type="checkbox" name="warranty" checked defaultChecked /> Add Warranty (+₹299)</label>
                </form>
                <a href="/level3_b">Page 3B</a>
            </body>
        </html>
    """,
    "/level3_a": """
        <html>
            <head><title>Level 3A</title></head>
            <body>
                <h1>Level 3A</h1>
                <a href="/level4_a">Page 4A</a>
            </body>
        </html>
    """,
    "/level3_b": """
        <html>
            <head><title>Level 3B</title></head>
            <body>
                <h1>Level 3B</h1>
                <a href="/level4_b">Page 4B</a>
            </body>
        </html>
    """,
    "/level4_a": """
        <html>
            <head><title>Level 4A</title></head>
            <body>
                <h1>Level 4A</h1>
                <a href="/level5_should_not_crawl">Depth 5 Link</a>
            </body>
        </html>
    """,
    "/level4_b": """
        <html>
            <head><title>Level 4B</title></head>
            <body>
                <h1>Level 4B</h1>
            </body>
        </html>
    """,
    "/level5_should_not_crawl": """
        <html>
            <head><title>Level 5 Should NOT Crawl</title></head>
            <body>
                <h1>Level 5</h1>
            </body>
        </html>
    """
}


class MockServerHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        if path in PAGES:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(PAGES[path].encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


class TestMultiPageCrawlerIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = socketserver.TCPServer(("127.0.0.1", 0), MockServerHandler)
        cls.port = cls.server.server_address[1]
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_crawl_depth_0(self):
        """Test 1: Crawl Depth = 0 -> Strictly 1 page audited (homepage)."""
        website = {
            "platform": "MockDepth0",
            "url": self.base_url + "/",
            "crawl_depth": 0,
            "max_pages": 50,
            "headless": True
        }
        res = run_crawler(website)
        self.assertEqual(res["configured_crawl_depth"], 0)
        self.assertEqual(res["actual_max_depth_reached"], 0)
        self.assertEqual(res["pages_crawled"], 1)
        self.assertEqual(res["pages_successful"], 1)
        self.assertEqual(len(res["pages"]), 1)
        self.assertEqual(res["pages"][0]["depth"], 0)

    def test_crawl_depth_1(self):
        """Test 2: Crawl Depth = 1 -> Homepage + directly linked pages (Level 1A and 1B)."""
        website = {
            "platform": "MockDepth1",
            "url": self.base_url + "/",
            "crawl_depth": 1,
            "max_pages": 50,
            "headless": True
        }
        res = run_crawler(website)
        self.assertEqual(res["configured_crawl_depth"], 1)
        self.assertEqual(res["actual_max_depth_reached"], 1)
        self.assertEqual(res["pages_crawled"], 3)  # / , /level1_a, /level1_b
        depths = [p["depth"] for p in res["pages"]]
        self.assertEqual(depths, [0, 1, 1])

    def test_crawl_depth_2_and_detection(self):
        """Test 3: Crawl Depth = 2 -> Homepage -> Depth 1 -> Depth 2 with detection."""
        website = {
            "platform": "MockDepth2",
            "url": self.base_url + "/",
            "crawl_depth": 2,
            "max_pages": 50,
            "headless": True
        }
        res = run_crawler(website)
        self.assertEqual(res["configured_crawl_depth"], 2)
        self.assertEqual(res["actual_max_depth_reached"], 2)
        self.assertEqual(res["pages_crawled"], 5)

        # Verify dark pattern detections aggregated across pages
        dark_patterns = res["dark_pattern_summary"]
        self.assertEqual(len(dark_patterns), 4)

        urgency = next(p for p in dark_patterns if p["pattern"] == "False Urgency")
        drip = next(p for p in dark_patterns if p["pattern"] == "Drip Pricing")
        bait = next(p for p in dark_patterns if p["pattern"] == "Bait and Switch")
        shame = next(p for p in dark_patterns if p["pattern"] == "Confirmshaming")

        # False Urgency was detected on level1_b timer
        self.assertTrue(urgency["detected"])
        self.assertEqual(urgency["status"], "DETECTED")
        self.assertEqual(urgency["pages_affected_count"], 1)

        # Other 3 patterns evaluated clean or insufficient evidence
        self.assertFalse(drip["detected"])
        self.assertFalse(bait["detected"])
        self.assertFalse(shame["detected"])

    def test_crawl_depth_4_cutoff(self):
        """Test 4: Crawl Depth = 4 -> Depths 0, 1, 2, 3, 4 are crawled; Depth 5 is NOT crawled."""
        website = {
            "platform": "MockDepth4",
            "url": self.base_url + "/",
            "crawl_depth": 4,
            "max_pages": 50,
            "headless": True
        }
        res = run_crawler(website)
        self.assertEqual(res["configured_crawl_depth"], 4)
        self.assertEqual(res["actual_max_depth_reached"], 4)

        crawled_urls = [p["url"] for p in res["pages"]]
        self.assertFalse(any("level5_should_not_crawl" in u for u in crawled_urls))

    def test_per_page_artifacts_and_mongodb_persistence(self):
        """Test 6: Verifies audit is fully stored in MongoDB with GridFS artifacts."""
        website = {
            "platform": "MockMongoAudit",
            "url": self.base_url + "/",
            "crawl_depth": 1,
            "max_pages": 5,
            "headless": True
        }
        res = run_crawler(website)
        audit_id = res["audit_id"]

        # 1. Verify audit retrieval from MongoDB
        mongo_audit = get_audit_details_from_mongodb(audit_id)
        self.assertIsNotNone(mongo_audit)
        self.assertEqual(mongo_audit["platform"], "MockMongoAudit")
        self.assertEqual(len(mongo_audit["pages"]), 3)

        # 2. Verify artifact endpoints point to GridFS API
        for p in mongo_audit["pages"]:
            artifacts = p["artifacts"]
            self.assertTrue(artifacts["screenshot"].startswith("api/v1/automation/artifact/"))
            self.assertTrue(artifacts["dom"].startswith("api/v1/automation/artifact/"))
            self.assertTrue(artifacts["extracted_json"].startswith("api/v1/automation/artifact/"))
            self.assertTrue(artifacts["evidence_json"].startswith("api/v1/automation/artifact/"))


if __name__ == "__main__":
    unittest.main()
