import json
import sys
import unittest
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.services.dark_patterns.bait_and_switch_detector import BaitAndSwitchDetector
from app.services.dark_patterns.confirmshaming_detector import ConfirmshamingDetector
from app.services.dark_patterns.detection_service import (
    ACTIVE_DETECTORS,
    ALL_PATTERNS,
    run_dark_pattern_detection,
)
from app.services.dark_patterns.drip_pricing_detector import DripPricingDetector
from app.services.dark_patterns.false_urgency_detector import FalseUrgencyDetector


class TestReview2Stabilization(unittest.TestCase):
    """
    Review 2 stabilization tests for the Final Four Dark Pattern architecture:
    1. False Urgency (Demonstration working detector)
    2. Drip Pricing
    3. Bait and Switch
    4. Confirmshaming
    """

    def setUp(self):
        self.urgency_detector = FalseUrgencyDetector()
        self.drip_detector = DripPricingDetector()
        self.bait_detector = BaitAndSwitchDetector()
        self.shame_detector = ConfirmshamingDetector()

    # ----------------------------------------------------
    # 1. FALSE URGENCY TESTS
    # ----------------------------------------------------
    def test_urgency_countdown_timer(self):
        """Countdown timer present -> Detected."""
        extracted_data = {
            "url": "https://store.example/flash-sale",
            "urgency_elements": [
                {
                    "text": "04:35 left before deal ends",
                    "pattern_type": "timer",
                    "tag": "span",
                    "classes": "deal-timer",
                    "selector": "#timer"
                }
            ]
        }
        evidence_record = {
            "page_url": "https://store.example/flash-sale",
            "evidence_items": [
                {
                    "evidence_id": "ev_timer_123",
                    "evidence_type": "extracted_data",
                    "category": "urgency_elements",
                    "selector": "#timer",
                    "text": "04:35 left before deal ends",
                    "artifact_path": "artifacts/Store/extracted.json"
                }
            ]
        }
        res = self.urgency_detector.detect(extracted_data, evidence_record)
        self.assertTrue(res.detected)
        self.assertEqual(res.status, "DETECTED")
        self.assertGreaterEqual(res.confidence, 85)
        self.assertEqual(len(res.evidence), 1)
        self.assertEqual(res.evidence[0].evidence_id, "ev_timer_123")

    def test_urgency_explicit_scarcity(self):
        """Explicit scarcity 'Only 2 left at this price' -> Detected."""
        extracted_data = {
            "url": "https://store.example/product",
            "urgency_elements": [
                {
                    "text": "Only 2 left at this price",
                    "pattern_type": "scarcity",
                    "tag": "p",
                    "classes": "scarcity",
                    "selector": "p.scarcity"
                }
            ]
        }
        evidence_record = {
            "page_url": "https://store.example/product",
            "evidence_items": [
                {
                    "evidence_id": "ev_scarcity_456",
                    "evidence_type": "extracted_data",
                    "category": "urgency_elements",
                    "selector": "p.scarcity",
                    "text": "Only 2 left at this price",
                    "artifact_path": "artifacts/Store/extracted.json"
                }
            ]
        }
        res = self.urgency_detector.detect(extracted_data, evidence_record)
        self.assertTrue(res.detected)
        self.assertEqual(res.status, "DETECTED")
        self.assertGreaterEqual(res.confidence, 80)
        self.assertEqual(len(res.evidence), 1)
        self.assertEqual(res.evidence[0].evidence_id, "ev_scarcity_456")

    def test_urgency_generic_promo_text(self):
        """Generic promotional text 'Special offer available' -> Not Detected."""
        extracted_data = {
            "url": "https://store.example/home",
            "urgency_elements": [
                {
                    "text": "Special offer available",
                    "pattern_type": None,
                    "tag": "span",
                    "classes": "promo",
                    "selector": "span.promo"
                }
            ]
        }
        evidence_record = {"page_url": "https://store.example/home", "evidence_items": []}
        res = self.urgency_detector.detect(extracted_data, evidence_record)
        self.assertFalse(res.detected)
        self.assertEqual(res.status, "NOT_DETECTED")
        self.assertEqual(res.confidence, 0)
        self.assertEqual(len(res.evidence), 0)

    # ----------------------------------------------------
    # 2. DRIP PRICING TESTS
    # ----------------------------------------------------
    def test_drip_pricing_mandatory_fee(self):
        """Mandatory booking fee revealed -> Detected."""
        extracted_data = {
            "url": "https://store.example/tickets",
            "prices": [{"raw_text": "₹500", "detected_price": "₹500", "context": "Base Ticket", "selector": "#t1"}],
            "visible_text": [{"tag": "div", "text": "Mandatory booking fee of ₹50 applied", "selector": "#fee"}]
        }
        evidence_record = {
            "page_url": "https://store.example/tickets",
            "evidence_items": [
                {"evidence_id": "ev_fee_1", "category": "visible_text", "text": "Mandatory booking fee of ₹50 applied", "selector": "#fee"}
            ]
        }
        res = self.drip_detector.detect(extracted_data, evidence_record)
        self.assertTrue(res.detected)
        self.assertEqual(res.status, "DETECTED")
        self.assertEqual(len(res.evidence), 1)

    # ----------------------------------------------------
    # 3. BAIT AND SWITCH TESTS
    # ----------------------------------------------------
    def test_bait_and_switch_detection(self):
        """Switch to higher-priced alternative message -> Detected."""
        extracted_data = {
            "url": "https://store.example/shop",
            "links": [{"text": "View Product", "href": "/p1"}],
            "prices": [{"raw_text": "₹1,000", "detected_price": "₹1,000"}],
            "visible_text": [{"tag": "p", "text": "Out of stock, switch to premium model", "selector": "#sw"}]
        }
        evidence_record = {
            "page_url": "https://store.example/shop",
            "evidence_items": [{"evidence_id": "ev_sw_1", "category": "visible_text", "text": "Out of stock, switch to premium model", "selector": "#sw"}]
        }
        res = self.bait_detector.detect(extracted_data, evidence_record)
        self.assertTrue(res.detected)
        self.assertEqual(res.status, "DETECTED")

    # ----------------------------------------------------
    # 4. CONFIRMSHAMING TESTS
    # ----------------------------------------------------
    def test_confirmshaming_detection(self):
        """Guilt opt-out text -> Detected."""
        extracted_data = {
            "url": "https://store.example/optin",
            "buttons": [{"text": "No, I don't want to save money", "selector": "#no-btn"}],
            "links": []
        }
        evidence_record = {
            "page_url": "https://store.example/optin",
            "evidence_items": [{"evidence_id": "ev_sh_1", "category": "buttons", "text": "No, I don't want to save money", "selector": "#no-btn"}]
        }
        res = self.shame_detector.detect(extracted_data, evidence_record)
        self.assertTrue(res.detected)
        self.assertEqual(res.status, "DETECTED")

    # ----------------------------------------------------
    # 5. PIPELINE INTEGRITY & API RESPONSE
    # ----------------------------------------------------
    def test_pipeline_multi_detector_dispatch(self):
        """Tests that run_dark_pattern_detection runs all active detectors."""
        extracted_data = {
            "url": "https://store.example/multi",
            "urgency_elements": [],
            "prices": [],
            "links": [],
            "visible_text": [],
            "buttons": []
        }
        evidence_record = {
            "page_url": "https://store.example/multi",
            "evidence_items": []
        }
        results = run_dark_pattern_detection(extracted_data, evidence_record)
        self.assertEqual(len(results), 8)
        patterns = [r["pattern"] for r in results]
        self.assertIn("False Urgency", patterns)
        self.assertIn("Drip Pricing", patterns)
        self.assertIn("Bait and Switch", patterns)
        self.assertIn("Confirmshaming", patterns)
        self.assertIn("SaaS Billing", patterns)
        self.assertIn("Interface Interference", patterns)
        self.assertIn("Forced Action", patterns)
        self.assertIn("Basket Sneaking", patterns)

        for r in results:
            self.assertIn("pattern", r)
            self.assertIn("status", r)
            self.assertIn("detected", r)
            self.assertIn("confidence", r)
            self.assertIn("reason", r)
            self.assertIn("page_url", r)
            self.assertIn("evidence", r)
            self.assertIn("metadata", r)



if __name__ == "__main__":
    unittest.main()
