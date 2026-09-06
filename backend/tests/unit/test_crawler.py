import sys
import unittest
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.services.automation.crawler_service import _normalize_url
from app.services.dark_patterns.detection_service import (
    aggregate_detection_findings,
    deduplicate_evidence_instances,
)


class TestCrawlerServiceLogic(unittest.TestCase):

    def test_url_normalization_and_domain_filtering(self):
        """Verifies domain restriction, fragment stripping, tracking param removal, and relative resolution."""
        base_url = "https://www.example.com/products/index.html"
        allowed_domain = "example.com"

        # Valid same-domain relative URL
        norm1 = _normalize_url("../about", base_url, allowed_domain)
        self.assertEqual(norm1, "https://www.example.com/about")

        # Strip fragment and tracking query params
        norm2 = _normalize_url("https://www.example.com/deals?utm_source=facebook&ref=123&page=2#section", base_url, allowed_domain)
        self.assertEqual(norm2, "https://www.example.com/deals?page=2")

        # Ignore external domain
        norm3 = _normalize_url("https://www.facebook.com/share", base_url, allowed_domain)
        self.assertIsNone(norm3)

        # Ignore javascript / mailto / tel
        self.assertIsNone(_normalize_url("javascript:void(0)", base_url, allowed_domain))
        self.assertIsNone(_normalize_url("mailto:support@example.com", base_url, allowed_domain))
        self.assertIsNone(_normalize_url("tel:+1234567890", base_url, allowed_domain))

        # Ignore binary files
        self.assertIsNone(_normalize_url("/downloads/brochure.pdf", base_url, allowed_domain))
        self.assertIsNone(_normalize_url("/images/logo.png", base_url, allowed_domain))

        # Ignore auth / sensitive URLs
        self.assertIsNone(_normalize_url("/auth/login", base_url, allowed_domain))
        self.assertIsNone(_normalize_url("/account/checkout", base_url, allowed_domain))

    def test_nested_dom_evidence_deduplication(self):
        """
        Test 8: Verifies nested duplicate DOM elements sharing the same text
        (e.g., 'Deal of the day' in parent, child, span) are counted as 1 instance.
        """
        nested_evidence = [
            {
                "evidence_id": "ev_1",
                "category": "urgency_elements",
                "selector": "#banner",
                "text": "Flash sale! 04:35 left before deal ends"
            },
            {
                "evidence_id": "ev_2",
                "category": "urgency_elements",
                "selector": "#banner > div.inner",
                "text": "Flash sale! 04:35 left before deal ends"
            },
            {
                "evidence_id": "ev_3",
                "category": "urgency_elements",
                "selector": "#banner > div.inner > span.timer",
                "text": "04:35 left before deal ends"
            },
            {
                "evidence_id": "ev_4",
                "category": "urgency_elements",
                "selector": "#sidebar > p.scarcity",
                "text": "Only 2 items left in stock!"
            }
        ]

        dedup_count = deduplicate_evidence_instances(nested_evidence)
        # Expected: 2 unique instances (1 for the timer banner, 1 for the stock scarcity)
        self.assertEqual(dedup_count, 2)

    def test_cross_page_detection_aggregation(self):
        """
        Verifies multi-page detection aggregation across multiple crawled pages for Final Four patterns.
        """
        page_records = [
            {
                "page_index": 0,
                "url": "https://store.example/",
                "depth": 0,
                "detections": [
                    {
                        "pattern": "False Urgency",
                        "detected": True,
                        "confidence": 90,
                        "reason": "Timer detected",
                        "evidence": [
                            {"evidence_id": "ev_timer_p0", "category": "urgency_elements", "text": "05:00 left!"}
                        ]
                    },
                    {
                        "pattern": "Drip Pricing",
                        "detected": False,
                        "confidence": 0,
                        "reason": "Upfront prices",
                        "evidence": []
                    },
                    {
                        "pattern": "Bait and Switch",
                        "detected": False,
                        "confidence": 0,
                        "reason": "Consistent offers",
                        "evidence": []
                    },
                    {
                        "pattern": "Confirmshaming",
                        "detected": False,
                        "confidence": 0,
                        "reason": "Neutral decline",
                        "evidence": []
                    },
                ]
            },
            {
                "page_index": 1,
                "url": "https://store.example/mobiles",
                "depth": 1,
                "detections": [
                    {
                        "pattern": "False Urgency",
                        "detected": True,
                        "confidence": 85,
                        "reason": "Scarcity detected",
                        "evidence": [
                            {"evidence_id": "ev_scarcity_p1", "category": "urgency_elements", "text": "Only 1 item left!"}
                        ]
                    },
                    {
                        "pattern": "Drip Pricing",
                        "detected": True,
                        "confidence": 88,
                        "reason": "Mandatory Platform Fee ₹150",
                        "evidence": [
                            {"evidence_id": "ev_fee_p1", "category": "prices", "text": "Mandatory Platform Fee ₹150"}
                        ]
                    },
                    {
                        "pattern": "Bait and Switch",
                        "detected": False,
                        "confidence": 0,
                        "reason": "Consistent offers",
                        "evidence": []
                    },
                    {
                        "pattern": "Confirmshaming",
                        "detected": False,
                        "confidence": 0,
                        "reason": "Neutral decline",
                        "evidence": []
                    },
                ]
            }
        ]

        summary = aggregate_detection_findings(page_records)
        self.assertEqual(len(summary), 8)

        urgency_res = next(s for s in summary if s["pattern"] == "False Urgency")
        self.assertTrue(urgency_res["detected"])
        self.assertEqual(urgency_res["pages_affected_count"], 2)
        self.assertEqual(len(urgency_res["affected_pages"]), 2)
        self.assertEqual(urgency_res["confidence"], 90)
        self.assertEqual(len(urgency_res["evidence"]), 2)

        drip_res = next(s for s in summary if s["pattern"] == "Drip Pricing")
        self.assertTrue(drip_res["detected"])
        self.assertEqual(drip_res["pages_affected_count"], 1)
        self.assertEqual(drip_res["affected_pages"][0]["url"], "https://store.example/mobiles")
        self.assertEqual(len(drip_res["evidence"]), 1)


if __name__ == "__main__":
    unittest.main()
