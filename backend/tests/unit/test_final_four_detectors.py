import sys
import unittest
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.models.detection_model import DetectionFinding
from app.services.dark_patterns.bait_and_switch_detector import BaitAndSwitchDetector
from app.services.dark_patterns.confirmshaming_detector import ConfirmshamingDetector
from app.services.dark_patterns.detection_service import (
    ACTIVE_DETECTORS,
    ALL_PATTERNS,
    aggregate_detection_findings,
    run_dark_pattern_detection,
)
from app.services.dark_patterns.drip_pricing_detector import DripPricingDetector
from app.services.dark_patterns.false_urgency_detector import FalseUrgencyDetector


class TestFinalFourDetectors(unittest.TestCase):
    """
    Comprehensive test suite for the Final Four Dark Pattern Detectors:
    1. False Urgency
    2. Drip Pricing / Hidden Costs
    3. Bait and Switch
    4. Confirmshaming
    """

    def setUp(self):
        self.urgency_detector = FalseUrgencyDetector()
        self.drip_detector = DripPricingDetector()
        self.bait_detector = BaitAndSwitchDetector()
        self.shame_detector = ConfirmshamingDetector()

    # --- 1. FALSE URGENCY TESTS ---
    def test_false_urgency_timer_detected(self):
        extracted_data = {
            "url": "https://example.com/deal",
            "urgency_elements": [
                {"text": "Deal expires in 12:45 mins left", "tag": "div", "classes": "deal-timer", "selector": "#timer"}
            ]
        }
        evidence_record = {
            "page_url": "https://example.com/deal",
            "evidence_items": [
                {"evidence_id": "ev_t1", "category": "urgency_elements", "text": "Deal expires in 12:45 mins left", "selector": "#timer"}
            ]
        }
        finding = self.urgency_detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)
        self.assertGreaterEqual(finding.confidence, 85)
        self.assertIn("Potential False Urgency detected", finding.reason)

    def test_false_urgency_scarcity_detected(self):
        extracted_data = {
            "url": "https://example.com/product",
            "urgency_elements": [
                {"text": "Hurry! Only 2 items left in stock", "tag": "span", "classes": "scarcity", "selector": ".stock-warn"}
            ]
        }
        evidence_record = {"page_url": "https://example.com/product", "evidence_items": []}
        finding = self.urgency_detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)
        self.assertIn("scarcity", finding.reason.lower())

    def test_false_urgency_generic_sale_not_detected(self):
        extracted_data = {
            "url": "https://example.com/sale",
            "urgency_elements": [
                {"text": "Special offer available", "tag": "p", "classes": "promo", "selector": "#promo"}
            ]
        }
        evidence_record = {"page_url": "https://example.com/sale", "evidence_items": []}
        finding = self.urgency_detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "NOT_DETECTED")
        self.assertFalse(finding.detected)
        self.assertEqual(finding.confidence, 0)

    # --- 2. DRIP PRICING TESTS ---
    def test_drip_pricing_mandatory_fee_detected(self):
        extracted_data = {
            "url": "https://example.com/checkout",
            "prices": [
                {"raw_text": "₹1,299", "detected_price": "₹1,299", "context": "Base Ticket Price", "selector": ".base-price"},
                {"raw_text": "₹150", "detected_price": "₹150", "context": "Mandatory Platform Fee ₹150", "selector": ".plat-fee"}
            ],
            "visible_text": [
                {"tag": "p", "text": "A non-refundable mandatory convenience fee of ₹150 will be added at checkout.", "selector": "#fee-note"}
            ]
        }
        evidence_record = {
            "page_url": "https://example.com/checkout",
            "evidence_items": [
                {"evidence_id": "ev_p1", "category": "prices", "text": "Mandatory Platform Fee ₹150", "selector": ".plat-fee"}
            ]
        }
        finding = self.drip_detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)
        self.assertGreaterEqual(finding.confidence, 80)
        self.assertIn("Drip Pricing", finding.reason)

    def test_drip_pricing_transparent_prices_not_detected(self):
        extracted_data = {
            "url": "https://example.com/product",
            "prices": [
                {"raw_text": "₹999", "detected_price": "₹999", "context": "Inclusive of all taxes", "selector": ".mrp"}
            ],
            "visible_text": [
                {"tag": "p", "text": "All taxes included. Free shipping nationwide.", "selector": ".tax-info"}
            ]
        }
        evidence_record = {"page_url": "https://example.com/product", "evidence_items": []}
        finding = self.drip_detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "NOT_DETECTED")
        self.assertFalse(finding.detected)
        self.assertEqual(finding.confidence, 0)

    def test_drip_pricing_no_prices_insufficient_evidence(self):
        extracted_data = {
            "url": "https://example.com/about",
            "prices": [],
            "visible_text": [{"tag": "h1", "text": "About Our Company", "selector": "h1"}]
        }
        evidence_record = {"page_url": "https://example.com/about", "evidence_items": []}
        finding = self.drip_detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "INSUFFICIENT_EVIDENCE")
        self.assertFalse(finding.detected)

    # --- 3. BAIT AND SWITCH TESTS ---
    def test_bait_and_switch_advertised_discrepancy_detected(self):
        extracted_data = {
            "url": "https://example.com/offers",
            "links": [
                {"text": "Get Free Trial", "href": "/signup", "selector": "#free-btn"}
            ],
            "prices": [
                {"raw_text": "₹4,999/year", "detected_price": "₹4,999", "selector": ".price-tag"}
            ],
            "visible_text": [
                {"tag": "p", "text": "Out of stock, switch to premium plan instead", "selector": "#switch-msg"}
            ]
        }
        evidence_record = {
            "page_url": "https://example.com/offers",
            "evidence_items": [
                {"evidence_id": "ev_sw1", "category": "visible_text", "text": "Out of stock, switch to premium plan instead", "selector": "#switch-msg"}
            ]
        }
        finding = self.bait_detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)
        self.assertIn("Bait and Switch", finding.reason)

    def test_bait_and_switch_consistent_offer_not_detected(self):
        extracted_data = {
            "url": "https://example.com/product",
            "links": [
                {"text": "Buy Book for ₹499", "href": "/book", "selector": "#book-link"}
            ],
            "prices": [
                {"raw_text": "₹499", "detected_price": "₹499", "selector": ".price"}
            ],
            "visible_text": [
                {"tag": "p", "text": "Hardcover edition in stock", "selector": ".desc"}
            ]
        }
        evidence_record = {"page_url": "https://example.com/product", "evidence_items": []}
        finding = self.bait_detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "NOT_DETECTED")
        self.assertFalse(finding.detected)

    def test_bait_and_switch_empty_content_insufficient_evidence(self):
        extracted_data = {
            "url": "https://example.com/blank",
            "links": [],
            "prices": [],
            "visible_text": []
        }
        evidence_record = {"page_url": "https://example.com/blank", "evidence_items": []}
        finding = self.bait_detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "INSUFFICIENT_EVIDENCE")

    # --- 4. CONFIRMSHAMING TESTS ---
    def test_confirmshaming_guilt_decline_detected(self):
        extracted_data = {
            "url": "https://example.com/modal",
            "buttons": [
                {"text": "Yes, Claim My 50% Off!", "tag": "button", "selector": "#accept-btn"},
                {"text": "No thanks, I hate discounts and prefer paying full price", "tag": "button", "selector": "#shame-btn"}
            ],
            "links": []
        }
        evidence_record = {
            "page_url": "https://example.com/modal",
            "evidence_items": [
                {"evidence_id": "ev_sh1", "category": "buttons", "text": "No thanks, I hate discounts and prefer paying full price", "selector": "#shame-btn"}
            ]
        }
        finding = self.shame_detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)
        self.assertIn("Confirmshaming", finding.reason)

    def test_confirmshaming_neutral_decline_not_detected(self):
        extracted_data = {
            "url": "https://example.com/modal",
            "buttons": [
                {"text": "Subscribe to Newsletter", "tag": "button", "selector": "#sub-btn"},
                {"text": "No thanks", "tag": "button", "selector": "#close-btn"},
                {"text": "Cancel", "tag": "button", "selector": "#cancel-btn"}
            ],
            "links": [
                {"text": "Maybe later", "href": "#", "selector": "#later-link"}
            ]
        }
        evidence_record = {"page_url": "https://example.com/modal", "evidence_items": []}
        finding = self.shame_detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "NOT_DETECTED")
        self.assertFalse(finding.detected)

    # --- 5. DETECTION SERVICE & REGISTRY TESTS ---
    def test_registry_contains_final_four(self):
        self.assertEqual(len(ACTIVE_DETECTORS), 4)
        self.assertEqual(ALL_PATTERNS, [
            "False Urgency",
            "Drip Pricing",
            "Bait and Switch",
            "Confirmshaming",
        ])

    def test_run_dark_pattern_detection_returns_all_four(self):
        extracted_data = {
            "url": "https://example.com/test",
            "urgency_elements": [{"text": "Ends in 05:00", "classes": "timer", "selector": "#t"}],
            "prices": [{"raw_text": "₹100", "detected_price": "₹100", "context": "Mandatory Platform fee", "selector": "#p"}],
            "links": [],
            "visible_text": [],
            "buttons": [{"text": "No, I don't want to save money", "selector": "#b"}]
        }
        evidence_record = {"page_url": "https://example.com/test", "evidence_items": []}
        results = run_dark_pattern_detection(extracted_data, evidence_record)
        self.assertEqual(len(results), 4)
        pattern_names = [r["pattern"] for r in results]
        self.assertIn("False Urgency", pattern_names)
        self.assertIn("Drip Pricing", pattern_names)
        self.assertIn("Bait and Switch", pattern_names)
        self.assertIn("Confirmshaming", pattern_names)
        self.assertNotIn("Basket Sneaking", pattern_names)

    def test_aggregate_detection_findings_all_four_patterns(self):
        page_records = [
            {
                "page_index": 0,
                "url": "https://example.com/p1",
                "depth": 0,
                "detections": [
                    {"pattern": "False Urgency", "status": "DETECTED", "detected": True, "confidence": 90, "reason": "Timer found", "evidence": [{"text": "timer"}]},
                    {"pattern": "Drip Pricing", "status": "NOT_DETECTED", "detected": False, "confidence": 0, "reason": "No hidden fees"},
                    {"pattern": "Bait and Switch", "status": "INSUFFICIENT_EVIDENCE", "detected": False, "confidence": 0, "reason": "No data"},
                    {"pattern": "Confirmshaming", "status": "NOT_DETECTED", "detected": False, "confidence": 0, "reason": "Neutral buttons"},
                ]
            }
        ]
        aggregated = aggregate_detection_findings(page_records)
        self.assertEqual(len(aggregated), 4)
        patterns_found = {a["pattern"]: a["status"] for a in aggregated}
        self.assertEqual(patterns_found["False Urgency"], "DETECTED")
        self.assertEqual(patterns_found["Drip Pricing"], "NOT_DETECTED")
        self.assertEqual(patterns_found["Bait and Switch"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(patterns_found["Confirmshaming"], "NOT_DETECTED")


if __name__ == "__main__":
    unittest.main()
