import unittest
from app.services.dark_patterns.confirmshaming_detector import ConfirmshamingDetector
from app.services.dark_patterns.detection_service import (
    ALL_PATTERNS,
    aggregate_detection_findings,
    run_dark_pattern_detection,
)
from app.services.dark_patterns.false_urgency_detector import FalseUrgencyDetector
from app.services.dark_patterns.forced_action_detector import ForcedActionDetector
from app.services.dark_patterns.basket_sneaking_detector import BasketSneakingDetector


class TestHybridDetectors(unittest.TestCase):
    """
    Test suite verifying the Hybrid Detection Architecture:
    - Rule-based layer: False Urgency, Confirmshaming
    - AI-assisted layer: Forced Action, Basket Sneaking
    - Full pipeline execution and cross-page aggregation
    """

    def setUp(self):
        self.false_urgency = FalseUrgencyDetector()
        self.confirmshaming = ConfirmshamingDetector()
        self.forced_action = ForcedActionDetector()
        self.basket_sneaking = BasketSneakingDetector()

    def test_rule_based_false_urgency_preserved(self):
        """Verify existing rule-based False Urgency remains functional and unchanged."""
        extracted = {
            "url": "https://example.com/item",
            "urgency_elements": [
                {
                    "text": "Hurry! Only 2 items left in stock - Deal ends in 05:00",
                    "selector": "#timer-banner",
                    "pattern_type": "timer"
                }
            ]
        }
        finding = self.false_urgency.detect(extracted, {})
        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)
        self.assertGreaterEqual(finding.confidence, 90)

    def test_rule_based_confirmshaming_preserved(self):
        """Verify existing rule-based Confirmshaming remains functional and unchanged."""
        extracted = {
            "url": "https://example.com/deal",
            "buttons": [
                {"text": "Claim 50% Discount Now", "is_visible": True, "selector": "#btn-accept"},
                {"text": "No, I prefer paying full price", "is_visible": True, "selector": "#btn-decline"}
            ],
            "links": [],
            "modals": []
        }
        finding = self.confirmshaming.detect(extracted, {})
        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)
        self.assertGreaterEqual(finding.confidence, 85)

    def test_ai_assisted_forced_action_pipeline(self):
        """Verify AI-assisted Forced Action returns model_score and validation_status."""
        extracted = {
            "url": "https://example.com/content",
            "forms": [],
            "checkboxes": [],
            "modals": [
                {
                    "text": "Sign up before continuing to access the dashboard",
                    "selector": "#gating-modal",
                    "is_dismissible": False,
                }
            ],
            "buttons": [{"text": "Sign Up", "selector": "#signup-btn"}],
            "links": []
        }
        finding = self.forced_action.detect(extracted, {})
        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)
        self.assertIsNotNone(finding.model_score)
        self.assertGreaterEqual(finding.model_score, 0.70)
        self.assertEqual(finding.validation_status, "PASSED")

    def test_ai_assisted_basket_sneaking_pipeline(self):
        """Verify AI-assisted Basket Sneaking returns model_score and validation_status."""
        extracted = {
            "url": "https://example.com/checkout",
            "checkboxes": [
                {
                    "name": "protection",
                    "checked": True,
                    "label": "Add 2-Year Accidental Damage Protection - ₹799",
                    "selector": "#cb-protection"
                }
            ],
            "cart_items": [{"name": "Smart Watch", "price": "₹4,999"}]
        }
        finding = self.basket_sneaking.detect(extracted, {})
        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)
        self.assertIsNotNone(finding.model_score)
        self.assertGreaterEqual(finding.model_score, 0.70)
        self.assertEqual(finding.validation_status, "PASSED")

    def test_full_detection_service_execution(self):
        """Verify run_dark_pattern_detection executes all 8 detectors cleanly."""
        extracted = {
            "url": "https://example.com/page",
            "urgency_elements": [],
            "buttons": [{"text": "Submit", "selector": "#submit"}],
            "links": [],
            "forms": [],
            "checkboxes": [],
            "modals": [],
            "cart_items": []
        }
        results = run_dark_pattern_detection(extracted, {})
        self.assertEqual(len(results), 8)
        pattern_names = [r["pattern"] for r in results]
        for pat in ALL_PATTERNS:
            self.assertIn(pat, pattern_names)

    def test_cross_page_aggregation_with_hybrid_findings(self):
        """Verify cross-page aggregation properly rolls up rule-based and AI-assisted findings."""
        page_records = [
            {
                "page_index": 0,
                "url": "https://example.com/home",
                "depth": 0,
                "detections": [
                    {
                        "pattern": "False Urgency",
                        "status": "DETECTED",
                        "detected": True,
                        "confidence": 95,
                        "reason": "Countdown timer found",
                        "evidence": [{"text": "05:00 left", "selector": "#timer"}]
                    },
                    {
                        "pattern": "Forced Action",
                        "status": "DETECTED",
                        "detected": True,
                        "model_score": 0.94,
                        "validation_status": "PASSED",
                        "confidence": 90,
                        "reason": "Forced sign up found",
                        "evidence": [{"text": "Sign up to continue", "selector": "#modal"}]
                    }
                ]
            }
        ]
        aggregated = aggregate_detection_findings(page_records)
        self.assertEqual(len(aggregated), 8)

        fu = next(a for a in aggregated if a["pattern"] == "False Urgency")
        self.assertEqual(fu["status"], "DETECTED")
        self.assertEqual(fu["confidence"], 95)

        fa = next(a for a in aggregated if a["pattern"] == "Forced Action")
        self.assertEqual(fa["status"], "DETECTED")
        self.assertEqual(fa["confidence"], 90)
        self.assertEqual(fa.get("model_score"), 0.94)


if __name__ == "__main__":
    unittest.main()
