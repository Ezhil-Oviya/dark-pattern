import unittest
from app.services.dark_patterns.saas_billing_detector import SaaSBillingDetector


class TestSaaSBillingDetector(unittest.TestCase):
    def setUp(self):
        self.detector = SaaSBillingDetector()

    def test_normal_subscription_not_detected(self):
        extracted = {
            "url": "https://example.com/pricing",
            "subscription_signals": [
                {"text": "$10 per month. Cancel anytime in your account settings.", "selector": "#plan-monthly"}
            ],
            "visible_text": [
                {"text": "Transparent monthly subscription with 1-click cancellation online anytime."}
            ],
            "prices": [{"raw_text": "$10/mo", "detected_price": "$10", "currency": "USD"}],
            "buttons": [{"text": "Subscribe Monthly", "selector": "#btn-sub"}]
        }
        evidence = {
            "page_url": "https://example.com/pricing",
            "evidence_items": [
                {"category": "subscription_signals", "selector": "#plan-monthly", "text": "$10 per month."}
            ]
        }
        finding = self.detector.detect(extracted, evidence)
        self.assertEqual(finding.status, "NOT_DETECTED")
        self.assertFalse(finding.detected)
        self.assertEqual(finding.confidence, 0)

    def test_hidden_auto_renewal_detected(self):
        extracted = {
            "url": "https://example.com/checkout",
            "subscription_signals": [
                {"text": "Renews automatically at regular rate without notice", "selector": ".fineprint"}
            ],
            "visible_text": [
                {"text": "By clicking you agree to continuous recurring monthly charges"}
            ],
            "prices": [{"raw_text": "$5", "detected_price": "$5", "currency": "USD"}],
            "buttons": [{"text": "Start Now", "selector": "#btn-start"}]
        }
        evidence = {
            "page_url": "https://example.com/checkout",
            "evidence_items": [
                {"category": "subscription_signals", "selector": ".fineprint", "text": "Renews automatically at regular rate without notice"}
            ]
        }
        finding = self.detector.detect(extracted, evidence)
        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)
        self.assertGreaterEqual(finding.confidence, 75)
        self.assertTrue("auto-renewal" in finding.reason.lower() or "auto renewal" in finding.reason.lower())

    def test_frequency_obfuscation_detected(self):
        extracted = {
            "url": "https://example.com/pro",
            "subscription_signals": [
                {"text": "$5/month (billed annually as one payment)", "selector": ".tier-price"}
            ],
            "prices": [{"raw_text": "$5/mo", "detected_price": "$5", "currency": "USD"}],
            "buttons": [{"text": "Get Pro", "selector": "#btn-pro"}]
        }
        evidence = {"evidence_items": []}
        finding = self.detector.detect(extracted, evidence)
        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)
        self.assertGreaterEqual(finding.confidence, 75)

    def test_deceptive_free_trial_detected(self):
        extracted = {
            "url": "https://example.com/trial",
            "subscription_signals": [
                {"text": "Start your free trial (credit card required, auto-converts to paid)", "selector": "#trial-box"}
            ],
            "buttons": [{"text": "Start Free Trial", "selector": "#btn-trial"}]
        }
        finding = self.detector.detect(extracted, {})
        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)

    def test_cancellation_barrier_phone_only(self):
        extracted = {
            "url": "https://example.com/terms",
            "subscription_signals": [
                {"text": "To cancel, call our customer service at 1-800-555-0199 during business hours", "selector": "#cancel-terms"}
            ],
            "buttons": [{"text": "Join Now", "selector": "#btn-join"}]
        }
        finding = self.detector.detect(extracted, {})
        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)
        self.assertGreaterEqual(finding.confidence, 85)

    def test_insufficient_evidence_when_no_billing_data(self):
        extracted = {
            "url": "https://example.com/about",
            "visible_text": [{"text": "About our company mission and engineering values."}],
            "buttons": [{"text": "Contact Us", "selector": "#btn-contact"}],
            "prices": [],
            "subscription_signals": []
        }
        finding = self.detector.detect(extracted, {})
        self.assertEqual(finding.status, "INSUFFICIENT_EVIDENCE")
        self.assertFalse(finding.detected)
        self.assertEqual(finding.confidence, 0)


if __name__ == "__main__":
    unittest.main()
