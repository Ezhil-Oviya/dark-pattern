import unittest
from app.services.dark_patterns.forced_action_detector import ForcedActionDetector


class TestForcedActionDetector(unittest.TestCase):
    def setUp(self):
        self.detector = ForcedActionDetector()

    def test_case_1_create_account_to_continue_detected(self):
        """Test Case 1: 'Create an account to continue' with no alternative is DETECTED."""
        extracted = {
            "url": "https://example.com/article/123",
            "forms": [],
            "checkboxes": [],
            "modals": [
                {
                    "text": "Create an account to continue reading this article and access research papers",
                    "selector": "#gating-overlay",
                    "is_dismissible": False,
                }
            ],
            "buttons": [
                {"text": "Create Account", "selector": "#btn-create"}
            ],
            "links": []
        }
        finding = self.detector.detect(extracted, {})
        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)
        self.assertIsNotNone(finding.model_score)
        self.assertGreaterEqual(finding.model_score, 0.70)
        self.assertGreaterEqual(finding.confidence, 75)
        self.assertEqual(finding.validation_status, "PASSED")
        self.assertIn("forced action", finding.reason.lower())

    def test_case_2_continue_as_guest_not_detected(self):
        """Test Case 2: 'Continue as guest' provides alternative path -> NOT_DETECTED."""
        extracted = {
            "url": "https://example.com/checkout",
            "forms": [],
            "checkboxes": [],
            "modals": [
                {
                    "text": "Sign in to your account to continue checkout",
                    "selector": "#login-modal"
                }
            ],
            "buttons": [
                {"text": "Sign In", "selector": "#btn-signin"},
                {"text": "Continue as guest", "selector": "#btn-guest"}
            ],
            "links": []
        }
        finding = self.detector.detect(extracted, {})
        self.assertEqual(finding.status, "NOT_DETECTED")
        self.assertFalse(finding.detected)
        self.assertEqual(finding.confidence, 0)
        self.assertEqual(finding.validation_status, "PASSED")

    def test_case_3_neutral_create_account_insufficient_evidence(self):
        """Test Case 3: 'Create an account' by itself lacks coercive context -> INSUFFICIENT_EVIDENCE."""
        extracted = {
            "url": "https://example.com/home",
            "forms": [],
            "checkboxes": [],
            "modals": [],
            "buttons": [
                {"text": "Create an account", "selector": "#header-signup-btn"}
            ],
            "links": []
        }
        finding = self.detector.detect(extracted, {})
        self.assertEqual(finding.status, "INSUFFICIENT_EVIDENCE")
        self.assertFalse(finding.detected)
        self.assertEqual(finding.confidence, 0)

    def test_case_4_neutral_login_content_not_detected_or_insufficient(self):
        """Test Case 4: Standard login form with standard inputs -> NOT_DETECTED / INSUFFICIENT_EVIDENCE."""
        extracted = {
            "url": "https://example.com/login",
            "forms": [
                {
                    "action": "/login",
                    "inputs": [
                        {"name": "username", "required": True, "label": "Username"},
                        {"name": "password", "required": True, "label": "Password"}
                    ]
                }
            ],
            "checkboxes": [],
            "modals": [],
            "buttons": [
                {"text": "Log In", "selector": "#btn-login"}
            ]
        }
        finding = self.detector.detect(extracted, {})
        self.assertIn(finding.status, ("NOT_DETECTED", "INSUFFICIENT_EVIDENCE"))
        self.assertFalse(finding.detected)
        self.assertEqual(finding.confidence, 0)

    def test_legitimate_required_checkout_not_detected(self):
        """Standard shipping and payment forms are legitimate."""
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
        """Mandatory marketing consent checkbox -> DETECTED."""
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
        self.assertIsNotNone(finding.model_score)
        self.assertGreaterEqual(finding.model_score, 0.70)
        self.assertEqual(finding.validation_status, "PASSED")
        self.assertEqual(len(finding.evidence), 1)

    def test_blocking_gating_modal_detected(self):
        """Blocking gating modal overlay -> DETECTED."""
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
        self.assertGreaterEqual(finding.model_score, 0.70)

    def test_insufficient_evidence_when_no_forms_or_modals(self):
        """Page with only generic static text returns INSUFFICIENT_EVIDENCE."""
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
        self.assertEqual(finding.confidence, 0)

    def test_malformed_and_empty_inputs_resilience(self):
        """Detector does not crash when presented with empty or malformed dictionaries."""
        finding = self.detector.detect({}, {})
        self.assertEqual(finding.status, "INSUFFICIENT_EVIDENCE")
        self.assertFalse(finding.detected)


if __name__ == "__main__":
    unittest.main()
