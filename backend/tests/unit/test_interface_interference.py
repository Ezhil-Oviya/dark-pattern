import unittest
from app.services.dark_patterns.interface_interference_detector import InterfaceInterferenceDetector


class TestInterfaceInterferenceDetector(unittest.TestCase):
    def setUp(self):
        self.detector = InterfaceInterferenceDetector()

    def test_symmetric_balanced_ui_not_detected(self):
        extracted = {
            "url": "https://example.com/consent",
            "buttons": [
                {
                    "text": "Accept All",
                    "tag": "button",
                    "selector": "#btn-accept",
                    "is_visible": True,
                    "metrics": {
                        "width": 140,
                        "height": 45,
                        "font_size": "14px",
                        "bg_color": "rgb(37, 99, 235)",
                        "text_color": "rgb(255, 255, 255)"
                    }
                },
                {
                    "text": "Reject All",
                    "tag": "button",
                    "selector": "#btn-reject",
                    "is_visible": True,
                    "metrics": {
                        "width": 140,
                        "height": 45,
                        "font_size": "14px",
                        "bg_color": "rgb(229, 231, 235)",
                        "text_color": "rgb(17, 24, 39)"
                    }
                }
            ],
            "links": []
        }
        finding = self.detector.detect(extracted, {})
        self.assertEqual(finding.status, "NOT_DETECTED")
        self.assertFalse(finding.detected)
        self.assertEqual(finding.confidence, 0)

    def test_severe_area_disparity_detected(self):
        extracted = {
            "url": "https://example.com/checkout",
            "buttons": [
                {
                    "text": "Accept All & Upgrade",
                    "tag": "button",
                    "selector": "#btn-accept",
                    "is_visible": True,
                    "metrics": {
                        "width": 280,
                        "height": 60,
                        "font_size": "18px",
                        "bg_color": "rgb(22, 163, 74)",
                        "text_color": "rgb(255, 255, 255)"
                    }
                }
            ],
            "links": [
                {
                    "text": "Skip",
                    "tag": "a",
                    "selector": "#link-skip",
                    "is_visible": True,
                    "metrics": {
                        "width": 40,
                        "height": 18,
                        "font_size": "11px",
                        "bg_color": "rgba(0, 0, 0, 0)",
                        "text_color": "#9ca3af"
                    }
                }
            ]
        }
        evidence = {
            "evidence_items": [
                {"category": "buttons", "selector": "#btn-accept", "text": "Accept All & Upgrade"},
                {"category": "links", "selector": "#link-skip", "text": "Skip"}
            ]
        }
        finding = self.detector.detect(extracted, evidence)
        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)
        self.assertGreaterEqual(finding.confidence, 80)
        self.assertIn("visual hierarchy", finding.reason.lower())
        self.assertGreater(len(finding.evidence), 0)

    def test_low_contrast_de_emphasis_detected(self):
        extracted = {
            "url": "https://example.com/cookie-banner",
            "buttons": [
                {
                    "text": "Agree and Continue",
                    "tag": "button",
                    "selector": "#btn-agree",
                    "is_visible": True,
                    "metrics": {
                        "width": 200,
                        "height": 50,
                        "font_size": "16px",
                        "bg_color": "#2563eb",
                        "text_color": "#ffffff"
                    }
                }
            ],
            "links": [
                {
                    "text": "Decline Non-Essential",
                    "tag": "a",
                    "selector": "#btn-decline-link",
                    "is_visible": True,
                    "metrics": {
                        "width": 100,
                        "height": 20,
                        "font_size": "12px",
                        "bg_color": "rgba(0, 0, 0, 0)",
                        "text_color": "rgb(156, 163, 175)"
                    }
                }
            ]
        }
        finding = self.detector.detect(extracted, {})
        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)

    def test_insufficient_evidence_when_single_button(self):
        extracted = {
            "url": "https://example.com/view",
            "buttons": [{"text": "Submit Search", "is_visible": True}],
            "links": [],
            "modals": []
        }
        finding = self.detector.detect(extracted, {})
        self.assertEqual(finding.status, "INSUFFICIENT_EVIDENCE")
        self.assertFalse(finding.detected)


if __name__ == "__main__":
    unittest.main()
