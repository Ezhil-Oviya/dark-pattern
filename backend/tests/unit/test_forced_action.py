import unittest
from app.services.dark_patterns.forced_action_detector import ForcedActionDetector


class TestForcedActionDetector(unittest.TestCase):
    def setUp(self):
        self.detector = ForcedActionDetector()

    def test_legitimate_required_checkout_not_detected(self):
        extracted = {
            "url": "https://example.com/checkout",
            "forms": [
                {
                    "action": "/api/checkout",
                    "inputs": [
                        {"name": "shipping_address", "required": True, "label": "Shipping Address"},
                        {"name": "card_number", "required": True, "label": "Card Number"}
                    ]
                }
            ],
            "checkboxes": [
                {
                    "label": "I accept the Terms and Conditions and Privacy Policy",
                    "required": True,
                    "selector": "#terms-check"
                }
            ],
            "modals": []
        }
        finding = self.detector.detect(extracted, {})
        self.assertEqual(finding.status, "NOT_DETECTED")
        self.assertFalse(finding.detected)
        self.assertEqual(finding.confidence, 0)

    def test_forced_promotional_checkbox_detected(self):
        extracted = {
            "url": "https://example.com/register",
            "forms": [
                {
                    "action": "/register",
                    "inputs": [
                        {"name": "email", "required": True, "label": "Email"}
                    ]
                }
            ],
            "checkboxes": [
                {
                    "label": "I agree to receive promotional marketing emails and daily partner deals",
                    "required": True,
                    "selector": "#marketing-consent-required"
                }
            ],
            "modals": []
        }
        evidence = {
            "evidence_items": [
                {
                    "category": "checkboxes",
                    "selector": "#marketing-consent-required",
                    "text": "I agree to receive promotional marketing emails and daily partner deals"
                }
            ]
        }
        finding = self.detector.detect(extracted, evidence)
        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)
        self.assertGreaterEqual(finding.confidence, 80)
        self.assertIn("forced action", finding.reason.lower())
        self.assertEqual(len(finding.evidence), 1)

    def test_blocking_gating_modal_detected(self):
        extracted = {
            "url": "https://example.com/article",
            "forms": [],
            "checkboxes": [],
            "modals": [
                {
                    "text": "Please sign up or register to continue reading this article and view pricing details",
                    "selector": "#blocking-wall-dialog"
                }
            ]
        }
        evidence = {
            "evidence_items": [
                {
                    "category": "modals",
                    "selector": "#blocking-wall-dialog",
                    "text": "Please sign up or register to continue reading"
                }
            ]
        }
        finding = self.detector.detect(extracted, evidence)
        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)
        self.assertGreaterEqual(finding.confidence, 75)

    def test_insufficient_evidence_when_no_forms_or_modals(self):
        extracted = {
            "url": "https://example.com/blog",
            "forms": [],
            "checkboxes": [],
            "modals": [],
            "visible_text": [{"text": "Welcome to our blog post."}]
        }
        finding = self.detector.detect(extracted, {})
        self.assertEqual(finding.status, "INSUFFICIENT_EVIDENCE")
        self.assertFalse(finding.detected)


if __name__ == "__main__":
    unittest.main()
