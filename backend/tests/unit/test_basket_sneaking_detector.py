import sys
import unittest
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.models.detection_model import DetectionFinding
from app.services.dark_patterns.basket_sneaking_detector import BasketSneakingDetector
from app.services.dark_patterns.detection_service import (
    ACTIVE_DETECTORS,
    ALL_PATTERNS,
    aggregate_detection_findings,
    run_dark_pattern_detection,
)


class TestBasketSneakingDetector(unittest.TestCase):
    """
    Comprehensive test suite for the Basket Sneaking Dark Pattern Detector:
    1. Preselected add-on checkboxes (warranties, care packs, donations, insurance, tips).
    2. Unsolicited line items added to shopping carts.
    3. Clean carts / non-sneaky checkout flows (NOT_DETECTED).
    4. Pages without cart / purchase elements (INSUFFICIENT_EVIDENCE).
    5. False positive handling (Mandatory legal terms, taxes, shipping, unselected recommendations).
    6. System integration with detection runner and aggregator.
    """

    def setUp(self):
        self.detector = BasketSneakingDetector()

    # --- 1. PRESELECTED ADD-ON CHECKBOXES ---

    def test_preselected_warranty_checkbox_detected(self):
        extracted_data = {
            "url": "https://example.com/checkout",
            "checkboxes": [
                {
                    "name": "warranty_opt",
                    "id": "chk_warranty",
                    "checked": True,
                    "default_checked": True,
                    "label": "Add 2-Year Extended Device Protection Plan (₹499)",
                    "surrounding_text": "Protect your purchase with our 2-Year Extended Device Protection Plan for ₹499",
                    "selector": "#chk_warranty",
                }
            ],
            "cart_items": [
                {"name": "Smartphone XYZ", "price": "₹19,999", "quantity": 1}
            ],
        }
        evidence_record = {
            "page_url": "https://example.com/checkout",
            "evidence_items": [
                {
                    "evidence_id": "ev_bsk_1",
                    "category": "checkboxes",
                    "text": "Add 2-Year Extended Device Protection Plan (₹499)",
                    "selector": "#chk_warranty",
                }
            ],
        }

        finding = self.detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)
        self.assertGreaterEqual(finding.confidence, 80)
        self.assertIn("Basket Sneaking", finding.reason)
        self.assertIn("protection plan", finding.reason.lower())
        self.assertGreaterEqual(len(finding.evidence), 1)

    def test_preselected_donation_checkbox_detected(self):
        extracted_data = {
            "url": "https://example.com/cart",
            "forms": [
                {
                    "action": "/checkout",
                    "inputs": [
                        {
                            "type": "checkbox",
                            "name": "donation",
                            "checked": True,
                            "label": "Add ₹20 donation to Earth Foundation",
                            "selector": "input[name='donation']",
                        }
                    ],
                }
            ],
            "cart_items": [{"name": "Book Title", "price": "₹350"}],
        }
        evidence_record = {"page_url": "https://example.com/cart", "evidence_items": []}

        finding = self.detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)
        self.assertIn("Basket Sneaking", finding.reason)

    def test_preselected_insurance_in_visible_text(self):
        extracted_data = {
            "url": "https://example.com/order-summary",
            "cart_items": [{"name": "Flight Ticket", "price": "₹4,500"}],
            "checkboxes": [
                {
                    "name": "travel_insure",
                    "checked": True,
                    "label": "Travel Insurance Included (₹299 per passenger)",
                    "selector": "#insure_chk",
                }
            ],
        }
        evidence_record = {"page_url": "https://example.com/order-summary", "evidence_items": []}

        finding = self.detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)
        self.assertIn("insurance", finding.reason.lower())

    # --- 2. UNSOLICITED CART ADDITIONS ---

    def test_unsolicited_cart_item_detected(self):
        extracted_data = {
            "url": "https://example.com/cart",
            "cart_items": [
                {"name": "Wireless Headphones", "price": "₹2,999", "quantity": 1},
                {
                    "name": "Auto-added Gift Wrap & Greeting Card",
                    "price": "₹99",
                    "quantity": 1,
                    "is_addon": True,
                    "selector": ".cart-addon-item",
                },
            ],
            "cart_breakdown": {
                "subtotal": "₹2,999",
                "items": ["Wireless Headphones", "Auto-added Gift Wrap & Greeting Card"],
            },
        }
        evidence_record = {
            "page_url": "https://example.com/cart",
            "evidence_items": [
                {
                    "evidence_id": "ev_cart_1",
                    "category": "cart_items",
                    "text": "Auto-added Gift Wrap & Greeting Card ₹99",
                    "selector": ".cart-addon-item",
                }
            ],
        }

        finding = self.detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)
        self.assertGreaterEqual(finding.confidence, 80)
        self.assertIn("unsolicited", finding.reason.lower())

    def test_unsolicited_free_trial_membership_in_cart(self):
        extracted_data = {
            "url": "https://example.com/checkout",
            "cart_items": [
                {"name": "Sneakers", "price": "₹3,499"},
                {"name": "VIP Club Membership (Auto-renews at ₹299/mo)", "price": "₹0.00"},
            ],
        }
        evidence_record = {"page_url": "https://example.com/checkout", "evidence_items": []}

        finding = self.detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)

    # --- 3. CLEAN CARTS (NOT_DETECTED) ---

    def test_clean_cart_with_unchecked_optional_addons_not_detected(self):
        extracted_data = {
            "url": "https://example.com/cart",
            "cart_items": [
                {"name": "Ergonomic Office Chair", "price": "₹8,999", "quantity": 1}
            ],
            "checkboxes": [
                {
                    "name": "add_warranty",
                    "checked": False,
                    "default_checked": False,
                    "label": "Add 3-Year Extended Warranty for ₹799",
                    "selector": "#opt_warranty",
                }
            ],
            "cart_breakdown": {
                "subtotal": "₹8,999",
                "total": "₹8,999",
            },
        }
        evidence_record = {"page_url": "https://example.com/cart", "evidence_items": []}

        finding = self.detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "NOT_DETECTED")
        self.assertFalse(finding.detected)
        self.assertEqual(finding.confidence, 0)
        self.assertIn("no preselected", finding.reason.lower())

    def test_clean_cart_with_standard_checkout_not_detected(self):
        extracted_data = {
            "url": "https://example.com/checkout",
            "cart_items": [
                {"name": "Running Shoes", "price": "₹2,499", "quantity": 1}
            ],
            "prices": [
                {"detected_price": "₹2,499", "context": "Subtotal"},
                {"detected_price": "₹2,499", "context": "Total"},
            ],
        }
        evidence_record = {"page_url": "https://example.com/checkout", "evidence_items": []}

        finding = self.detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "NOT_DETECTED")
        self.assertFalse(finding.detected)

    # --- 4. INSUFFICIENT EVIDENCE ---

    def test_non_ecommerce_article_page_insufficient_evidence(self):
        extracted_data = {
            "url": "https://example.com/about-us",
            "title": "About Our Company",
            "visible_text": [
                {"tag": "h1", "text": "About Us"},
                {"tag": "p", "text": "We are committed to transparent e-commerce practices."},
            ],
            "cart_items": [],
            "checkboxes": [],
            "forms": [],
        }
        evidence_record = {"page_url": "https://example.com/about-us", "evidence_items": []}

        finding = self.detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "INSUFFICIENT_EVIDENCE")
        self.assertFalse(finding.detected)
        self.assertIn("Insufficient cart", finding.reason)

    # --- 5. FALSE POSITIVE PREVENTION ---

    def test_mandatory_terms_and_conditions_checkbox_not_basket_sneaking(self):
        extracted_data = {
            "url": "https://example.com/checkout",
            "cart_items": [{"name": "Laptop", "price": "₹55,000"}],
            "checkboxes": [
                {
                    "name": "agree_terms",
                    "checked": True,
                    "label": "I agree to the Terms & Conditions and Privacy Policy",
                    "selector": "#terms",
                }
            ],
        }
        evidence_record = {"page_url": "https://example.com/checkout", "evidence_items": []}

        finding = self.detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "NOT_DETECTED")
        self.assertFalse(finding.detected)

    def test_mandatory_gst_tax_not_basket_sneaking(self):
        extracted_data = {
            "url": "https://example.com/cart",
            "cart_items": [
                {"name": "Camera", "price": "₹32,000"},
                {"name": "GST (18%)", "price": "₹5,760"},
            ],
        }
        evidence_record = {"page_url": "https://example.com/cart", "evidence_items": []}

        finding = self.detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "NOT_DETECTED")
        self.assertFalse(finding.detected)

    def test_standard_shipping_fee_not_basket_sneaking(self):
        extracted_data = {
            "url": "https://example.com/cart",
            "cart_items": [
                {"name": "T-Shirt", "price": "₹499"},
                {"name": "Standard Delivery Shipping Fee", "price": "₹40"},
            ],
        }
        evidence_record = {"page_url": "https://example.com/cart", "evidence_items": []}

        finding = self.detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "NOT_DETECTED")
        self.assertFalse(finding.detected)

    def test_unselected_product_recommendation_not_basket_sneaking(self):
        extracted_data = {
            "url": "https://example.com/product/123",
            "cart_items": [{"name": "Phone", "price": "₹15,000"}],
            "checkboxes": [
                {
                    "name": "frequently_bought",
                    "checked": False,
                    "default_checked": False,
                    "label": "Frequently bought together: Screen Protector ₹199",
                    "selector": ".rec-chk",
                }
            ],
        }
        evidence_record = {"page_url": "https://example.com/product/123", "evidence_items": []}

        finding = self.detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "NOT_DETECTED")
        self.assertFalse(finding.detected)

    # --- 6. AGGREGATION & SERVICE INTEGRATION ---

    def test_basket_sneaking_in_detection_service_runner(self):
        extracted_data = {
            "url": "https://example.com/checkout",
            "checkboxes": [
                {
                    "name": "donation",
                    "checked": True,
                    "label": "Add ₹50 optional donation to child care",
                    "selector": "#donation_chk",
                }
            ],
            "cart_items": [{"name": "Watch", "price": "₹1,999"}],
        }
        evidence_record = {"page_url": "https://example.com/checkout", "evidence_items": []}

        findings = run_dark_pattern_detection(extracted_data, evidence_record)
        self.assertEqual(len(findings), 8)

        bsk_finding = next((f for f in findings if f["pattern"] == "Basket Sneaking"), None)
        self.assertIsNotNone(bsk_finding)
        self.assertEqual(bsk_finding["status"], "DETECTED")
        self.assertTrue(bsk_finding["detected"])
        self.assertGreaterEqual(bsk_finding["confidence"], 75)

    def test_basket_sneaking_aggregation_across_pages(self):
        page_records = [
            {
                "page_index": 0,
                "url": "https://example.com/home",
                "depth": 0,
                "detections": [
                    {
                        "pattern": "Basket Sneaking",
                        "status": "INSUFFICIENT_EVIDENCE",
                        "detected": False,
                        "confidence": 0,
                        "reason": "No cart items",
                        "evidence": [],
                    }
                ],
            },
            {
                "page_index": 1,
                "url": "https://example.com/cart",
                "depth": 1,
                "detections": [
                    {
                        "pattern": "Basket Sneaking",
                        "status": "DETECTED",
                        "detected": True,
                        "confidence": 85,
                        "reason": "Preselected warranty item found",
                        "evidence": [
                            {
                                "text": "Preselected 1-year warranty",
                                "selector": "#chk_war",
                            }
                        ],
                    }
                ],
            },
        ]

        aggregated = aggregate_detection_findings(page_records)
        bsk_agg = next((a for a in aggregated if a["pattern"] == "Basket Sneaking"), None)

        self.assertIsNotNone(bsk_agg)
        self.assertEqual(bsk_agg["status"], "DETECTED")
        self.assertTrue(bsk_agg["detected"])
        self.assertEqual(bsk_agg["confidence"], 85)
        self.assertEqual(bsk_agg["pages_affected_count"], 1)
        self.assertEqual(bsk_agg["total_instances"], 1)


if __name__ == "__main__":
    unittest.main()
