import sys
import unittest
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.services.dark_patterns.confirmshaming_detector import ConfirmshamingDetector


class TestConfirmshamingDetector(unittest.TestCase):
    def setUp(self):
        self.detector = ConfirmshamingDetector()

    # CASE 1: Strong Confirmshaming (Discounts / Paying Full Price)
    def test_case_1_strong_confirmshaming_save_vs_full_price(self):
        extracted_data = {
            "url": "https://example.com/checkout",
            "buttons": [
                {"text": "Yes, Save 20%", "tag": "button", "selector": "#save-btn", "is_visible": True},
                {"text": "No, I prefer paying full price", "tag": "button", "selector": "#full-price-btn", "is_visible": True},
            ],
            "links": [],
            "modals": [],
        }
        evidence_record = {
            "page_url": "https://example.com/checkout",
            "page_index": 0,
            "evidence_items": [
                {"evidence_id": "ev_btn_1", "category": "buttons", "selector": "#full-price-btn", "text": "No, I prefer paying full price", "artifact_path": "artifacts/p0/extracted.json"}
            ],
            "artifacts": {"extracted_json": "artifacts/p0/extracted.json"}
        }

        finding = self.detector.detect(extracted_data, evidence_record)

        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)
        self.assertGreaterEqual(finding.confidence, 80)
        self.assertIn("Confirmshaming", finding.reason)
        self.assertIn("No, I prefer paying full price", finding.metadata["decline_actions"])
        self.assertEqual(len(finding.evidence), 1)
        self.assertEqual(finding.evidence[0].selector, "#full-price-btn")

    # CASE 2: Strong Confirmshaming (Device Protection / Unprotected Guilt)
    def test_case_2_strong_confirmshaming_protection(self):
        extracted_data = {
            "url": "https://example.com/warranty",
            "buttons": [
                {"text": "Protect my device", "tag": "button", "selector": "#protect-btn", "is_visible": True},
                {"text": "No, I want to stay unprotected", "tag": "button", "selector": "#unprotected-btn", "is_visible": True},
            ],
            "links": [],
            "modals": [],
        }
        evidence_record = {"page_url": "https://example.com/warranty", "evidence_items": []}

        finding = self.detector.detect(extracted_data, evidence_record)

        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)
        self.assertGreaterEqual(finding.confidence, 80)
        self.assertIn("NEGATIVE_VULNERABILITY", finding.metadata["signals"])

    # CASE 3: Neutral Refusal ("No thanks")
    def test_case_3_neutral_refusal_no_thanks(self):
        extracted_data = {
            "url": "https://example.com/newsletter",
            "buttons": [
                {"text": "Subscribe", "tag": "button", "selector": "#sub-btn", "is_visible": True},
                {"text": "No thanks", "tag": "button", "selector": "#no-thanks-btn", "is_visible": True},
            ],
            "links": [],
            "modals": [],
        }
        evidence_record = {"page_url": "https://example.com/newsletter", "evidence_items": []}

        finding = self.detector.detect(extracted_data, evidence_record)

        self.assertEqual(finding.status, "NOT_DETECTED")
        self.assertFalse(finding.detected)
        self.assertEqual(finding.confidence, 0)
        self.assertIn("neutral", finding.reason.lower())

    # CASE 4: Neutral Refusal ("Cancel")
    def test_case_4_neutral_refusal_cancel(self):
        extracted_data = {
            "url": "https://example.com/dialog",
            "buttons": [
                {"text": "Continue", "tag": "button", "selector": "#continue-btn", "is_visible": True},
                {"text": "Cancel", "tag": "button", "selector": "#cancel-btn", "is_visible": True},
            ],
            "links": [],
            "modals": [],
        }
        evidence_record = {"page_url": "https://example.com/dialog", "evidence_items": []}

        finding = self.detector.detect(extracted_data, evidence_record)

        self.assertEqual(finding.status, "NOT_DETECTED")
        self.assertFalse(finding.detected)
        self.assertEqual(finding.confidence, 0)

    # CASE 5: Neutral Refusal ("Maybe later")
    def test_case_5_neutral_refusal_maybe_later(self):
        extracted_data = {
            "url": "https://example.com/offer",
            "buttons": [
                {"text": "Get the offer", "tag": "button", "selector": "#get-offer-btn", "is_visible": True},
            ],
            "links": [
                {"text": "Maybe later", "href": "#", "selector": "#later-link", "is_visible": True},
            ],
            "modals": [],
        }
        evidence_record = {"page_url": "https://example.com/offer", "evidence_items": []}

        finding = self.detector.detect(extracted_data, evidence_record)

        self.assertEqual(finding.status, "NOT_DETECTED")
        self.assertFalse(finding.detected)
        self.assertEqual(finding.confidence, 0)

    # CASE 6: Generic Refusal ("No")
    def test_case_6_generic_refusal_no(self):
        extracted_data = {
            "url": "https://example.com/prompt",
            "buttons": [
                {"text": "Yes", "tag": "button", "selector": "#yes-btn", "is_visible": True},
                {"text": "No", "tag": "button", "selector": "#no-btn", "is_visible": True},
            ],
            "links": [],
            "modals": [],
        }
        evidence_record = {"page_url": "https://example.com/prompt", "evidence_items": []}

        finding = self.detector.detect(extracted_data, evidence_record)

        self.assertEqual(finding.status, "NOT_DETECTED")
        self.assertFalse(finding.detected)
        self.assertEqual(finding.confidence, 0)

    # CASE 7: No Opt-Out / Decline Interaction Available
    def test_case_7_no_opt_out_interaction(self):
        extracted_data = {
            "url": "https://example.com/product/123",
            "buttons": [
                {"text": "Add to Cart", "tag": "button", "selector": "#add-cart", "is_visible": True},
                {"text": "Buy Now", "tag": "button", "selector": "#buy-now", "is_visible": True},
            ],
            "links": [
                {"text": "Product Specifications", "href": "/specs", "selector": "#specs-link", "is_visible": True}
            ],
            "modals": [],
        }
        evidence_record = {"page_url": "https://example.com/product/123", "evidence_items": []}

        finding = self.detector.detect(extracted_data, evidence_record)

        self.assertEqual(finding.status, "INSUFFICIENT_EVIDENCE")
        self.assertFalse(finding.detected)
        self.assertEqual(finding.confidence, 0)
        self.assertIn("No explicit opt-out", finding.reason)

    # CASE 8: Hidden Element Manipulation Ignored
    def test_case_8_hidden_element_ignored(self):
        extracted_data = {
            "url": "https://example.com/landing",
            "buttons": [
                {"text": "Claim Deal", "tag": "button", "selector": "#claim", "is_visible": True},
                # Hidden element containing confirmshaming text
                {"text": "No, I prefer paying full price", "tag": "button", "selector": "#hidden-shame", "is_visible": False},
            ],
            "links": [
                {"text": "Close", "href": "#", "selector": "#close", "is_visible": True}
            ],
            "modals": [],
        }
        evidence_record = {"page_url": "https://example.com/landing", "evidence_items": []}

        finding = self.detector.detect(extracted_data, evidence_record)

        # Should NOT trigger DETECTED because the manipulative element was invisible (hidden)
        self.assertNotEqual(finding.status, "DETECTED")
        self.assertFalse(finding.detected)

    # CASE 9: Multiple Choices Modal (Apathy towards Savings)
    def test_case_9_multiple_choices_apathy(self):
        extracted_data = {
            "url": "https://example.com/popup",
            "buttons": [
                {"text": "Yes, save money", "tag": "button", "selector": "#yes-save", "is_visible": True},
                {"text": "No, I don't care about saving money", "tag": "button", "selector": "#no-care", "is_visible": True},
            ],
            "links": [],
            "modals": [
                {"tag": "dialog", "text": "Unlock Exclusive Discount", "selector": "#discount-modal", "is_visible": True}
            ],
        }
        evidence_record = {
            "page_url": "https://example.com/popup",
            "page_index": 0,
            "evidence_items": [
                {"evidence_id": "ev_btn_9", "category": "buttons", "selector": "#no-care", "text": "No, I don't care about saving money", "artifact_path": "artifacts/p0/extracted.json"}
            ],
        }

        finding = self.detector.detect(extracted_data, evidence_record)

        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)
        self.assertGreaterEqual(finding.confidence, 85)
        self.assertIn("GUILT_AND_APATHY", finding.metadata["signals"])

    # CASE 10: Generalization & Variations
    def test_case_10_linguistic_variations(self):
        variations = [
            ("Claim 10% Off", "I'd rather pay full price"),
            ("Unlock VIP Perks", "No, I don't want exclusive perks"),
            ("Get Protection", "I choose to stay unprotected"),
            ("Save Today", "I hate saving"),
        ]

        for pref_txt, dec_txt in variations:
            extracted_data = {
                "url": "https://example.com/deal",
                "buttons": [
                    {"text": pref_txt, "tag": "button", "selector": "#pref", "is_visible": True},
                    {"text": dec_txt, "tag": "button", "selector": "#dec", "is_visible": True},
                ],
                "links": [],
                "modals": [],
            }
            finding = self.detector.detect(extracted_data, {})
            self.assertEqual(finding.status, "DETECTED", f"Failed for variation: '{dec_txt}'")
            self.assertTrue(finding.detected)

    # CASE 11: Traceable Evidence Linking
    def test_case_11_traceable_evidence_linking(self):
        extracted_data = {
            "url": "https://example.com/cart",
            "buttons": [
                {"text": "Yes, Protect My Order", "tag": "button", "selector": "#protect-order", "is_visible": True},
                {"text": "No, let my order get damaged", "tag": "button", "selector": "#damage-order", "is_visible": True},
            ],
            "links": [],
            "modals": [],
        }
        evidence_record = {
            "page_url": "https://example.com/cart",
            "page_index": 1,
            "artifacts": {"extracted_json": "api/v1/automation/artifact/file_ext_123"},
            "evidence_items": [],
        }

        finding = self.detector.detect(extracted_data, evidence_record)

        self.assertEqual(finding.status, "DETECTED")
        self.assertEqual(len(finding.evidence), 1)
        ev = finding.evidence[0]
        self.assertEqual(ev.selector, "#damage-order")
        self.assertEqual(ev.text, "No, let my order get damaged")
        self.assertIn("file_ext_123", ev.artifact_path)


if __name__ == "__main__":
    unittest.main()
