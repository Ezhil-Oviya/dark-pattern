import unittest
from app.services.dark_patterns.ai_classifier import (
    BaseAIClassifier,
    PatternSemanticClassifier,
    get_ai_classifier,
)


class TestAIClassifier(unittest.TestCase):
    def setUp(self):
        self.classifier = get_ai_classifier()

    def test_singleton_pattern(self):
        c1 = get_ai_classifier()
        c2 = get_ai_classifier()
        self.assertIs(c1, c2)
        self.assertIsInstance(c1, BaseAIClassifier)

    def test_forced_action_coercive_classification(self):
        # Coercive account creation
        score, meta = self.classifier.classify_forced_action(
            "Create an account to continue reading this article"
        )
        self.assertGreaterEqual(score, 0.70)
        self.assertIn("coercive_account_gating", meta["signals"])
        self.assertGreaterEqual(meta["positive_similarity"], 0.45)
        self.assertGreater(meta["semantic_margin"], 0.0)

        # Forced app download
        score, meta = self.classifier.classify_forced_action(
            "Download our mobile app to continue viewing discounts"
        )
        self.assertGreaterEqual(score, 0.70)
        self.assertIn("forced_app_download", meta["signals"])

        # Mandatory notification opt-in
        score, meta = self.classifier.classify_forced_action(
            "Enable push notifications to proceed to the download"
        )
        self.assertGreaterEqual(score, 0.70)
        self.assertIn("forced_notification_optin", meta["signals"])

    def test_forced_action_with_guest_alternative(self):
        score, meta = self.classifier.classify_forced_action(
            "Create an account to continue reading",
            context={"has_alternative": True, "guest_option_present": True}
        )
        # Score is heavily penalized when an alternative exists
        self.assertLess(score, 0.30)

    def test_forced_action_legitimate_requirements(self):
        # Legal terms
        score, _ = self.classifier.classify_forced_action(
            "I accept the Terms and Conditions and Privacy Policy"
        )
        self.assertLess(score, 0.25)

        # Shipping address
        score, _ = self.classifier.classify_forced_action(
            "Shipping Address: Street, City, Zip Code"
        )
        self.assertLess(score, 0.20)

    def test_basket_sneaking_addon_classification(self):
        # Extended warranty
        score, meta = self.classifier.classify_basket_sneaking(
            "Add 2-Year Extended Warranty Care Pack - ₹499"
        )
        self.assertGreaterEqual(score, 0.75)
        self.assertIn("extended_warranty", meta["signals"])
        self.assertGreaterEqual(meta["positive_similarity"], 0.45)
        self.assertGreater(meta["semantic_margin"], 0.0)

        # Device protection plan
        score, meta = self.classifier.classify_basket_sneaking(
            "Device Accidental Damage Protection Plan - $9.99"
        )
        self.assertGreaterEqual(score, 0.75)
        self.assertIn("device_protection_plan", meta["signals"])

        # Charity donation
        score, meta = self.classifier.classify_basket_sneaking(
            "Donate ₹50 to Green Earth Foundation with this purchase"
        )
        self.assertGreaterEqual(score, 0.75)
        self.assertIn("charitable_donation_addon", meta["signals"])

    def test_basket_sneaking_legitimate_exclusions(self):
        # Terms & Conditions
        score, _ = self.classifier.classify_basket_sneaking(
            "I agree to the Terms of Service and Privacy Policy"
        )
        self.assertLess(score, 0.25)

        # GST tax
        score, _ = self.classifier.classify_basket_sneaking(
            "Goods and Services Tax (GST 18%) - ₹180"
        )
        self.assertLess(score, 0.20)

        # Standard shipping
        score, _ = self.classifier.classify_basket_sneaking(
            "Standard Ground Shipping - ₹40"
        )
        self.assertLess(score, 0.20)

    def test_empty_and_malformed_input_safety(self):
        score, meta = self.classifier.classify_forced_action("")
        self.assertEqual(score, 0.0)

        score, meta = self.classifier.classify_forced_action(None)
        self.assertEqual(score, 0.0)

        score, meta = self.classifier.classify_basket_sneaking("")
        self.assertEqual(score, 0.0)

        score, meta = self.classifier.classify_basket_sneaking(None)
        self.assertEqual(score, 0.0)


if __name__ == "__main__":
    unittest.main()

