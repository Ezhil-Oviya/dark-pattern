import sys
import unittest
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.services.dark_patterns.false_urgency_detector import FalseUrgencyDetector


class TestFalseUrgencyDetector(unittest.TestCase):

    def setUp(self):
        self.detector = FalseUrgencyDetector()

    def test_positive_countdown_timer(self):
        """Test 1 (Positive Strong): Countdown timer with offer ends in message."""
        extracted_data = {
            "url": "https://store.example/deal",
            "urgency_elements": [
                {
                    "text": "04:35 left before deal ends!",
                    "pattern_type": "timer",
                    "tag": "span",
                    "classes": "countdown timer",
                    "selector": "#banner > span.countdown"
                }
            ]
        }
        evidence_record = {
            "page_url": "https://store.example/deal",
            "evidence_items": [
                {
                    "evidence_id": "ev_timer_001",
                    "evidence_type": "extracted_data",
                    "category": "urgency_elements",
                    "selector": "#banner > span.countdown",
                    "text": "04:35 left before deal ends!",
                    "artifact_path": "artifacts/Store/2026-08-29/extracted.json"
                }
            ]
        }

        finding = self.detector.detect(extracted_data, evidence_record)

        self.assertEqual(finding.pattern, "False Urgency")
        self.assertTrue(finding.detected)
        self.assertGreaterEqual(finding.confidence, 85)
        self.assertIn("False Urgency detected", finding.reason)
        self.assertEqual(len(finding.evidence), 1)
        self.assertEqual(finding.evidence[0].evidence_id, "ev_timer_001")
        self.assertEqual(finding.evidence[0].selector, "#banner > span.countdown")

    def test_positive_scarcity_signal(self):
        """Test 2 (Positive Scarcity): Explicit 'Only 2 left at this price' message."""
        extracted_data = {
            "url": "https://store.example/product/shoes",
            "urgency_elements": [
                {
                    "text": "Only 2 left at this price - order soon",
                    "pattern_type": "scarcity",
                    "tag": "p",
                    "classes": "stock-warning",
                    "selector": "div.stock-info > p.stock-warning"
                }
            ]
        }
        evidence_record = {
            "page_url": "https://store.example/product/shoes",
            "evidence_items": [
                {
                    "evidence_id": "ev_scarcity_002",
                    "evidence_type": "extracted_data",
                    "category": "urgency_elements",
                    "selector": "div.stock-info > p.stock-warning",
                    "text": "Only 2 left at this price - order soon",
                    "artifact_path": "artifacts/Store/2026-08-29/extracted.json"
                }
            ]
        }

        finding = self.detector.detect(extracted_data, evidence_record)

        self.assertEqual(finding.pattern, "False Urgency")
        self.assertTrue(finding.detected)
        self.assertGreaterEqual(finding.confidence, 80)
        self.assertEqual(len(finding.evidence), 1)
        self.assertEqual(finding.evidence[0].evidence_id, "ev_scarcity_002")

    def test_negative_weak_generic_text(self):
        """Test 3 (Negative): Generic promotional text without urgency."""
        extracted_data = {
            "url": "https://store.example/home",
            "urgency_elements": [
                {
                    "text": "Special offer available",
                    "pattern_type": None,
                    "tag": "span",
                    "classes": "promo-tag",
                    "selector": "#promo > span"
                }
            ]
        }
        evidence_record = {
            "page_url": "https://store.example/home",
            "evidence_items": []
        }

        finding = self.detector.detect(extracted_data, evidence_record)

        self.assertEqual(finding.pattern, "False Urgency")
        self.assertFalse(finding.detected)
        self.assertEqual(finding.confidence, 0)
        self.assertEqual(len(finding.evidence), 0)

    def test_no_urgency_elements(self):
        """Test 4 (No Urgency): Empty urgency elements list."""
        extracted_data = {
            "url": "https://store.example/contact",
            "urgency_elements": []
        }
        evidence_record = {
            "page_url": "https://store.example/contact",
            "evidence_items": []
        }

        finding = self.detector.detect(extracted_data, evidence_record)

        self.assertEqual(finding.pattern, "False Urgency")
        self.assertFalse(finding.detected)
        self.assertEqual(finding.confidence, 0)
        self.assertEqual(len(finding.evidence), 0)

    def test_evidence_integrity(self):
        """Test 5 (Evidence Integrity): Every DetectionEvidenceRef corresponds to a real EvidenceItem."""
        extracted_data = {
            "url": "https://store.example/flash-deal",
            "urgency_elements": [
                {
                    "text": "Flash sale ends in 10 mins left!",
                    "pattern_type": "timer",
                    "tag": "div",
                    "classes": "timer",
                    "selector": "#flash-banner"
                }
            ]
        }
        evidence_record = {
            "page_url": "https://store.example/flash-deal",
            "evidence_items": [
                {
                    "evidence_id": "ev_urgency_real_777",
                    "evidence_type": "extracted_data",
                    "category": "urgency_elements",
                    "selector": "#flash-banner",
                    "text": "Flash sale ends in 10 mins left!",
                    "artifact_path": "artifacts/Store/2026-08-29/extracted.json"
                }
            ]
        }

        finding = self.detector.detect(extracted_data, evidence_record)

        self.assertTrue(finding.detected)
        self.assertEqual(len(finding.evidence), 1)
        self.assertEqual(finding.evidence[0].evidence_id, "ev_urgency_real_777")
        self.assertEqual(finding.evidence[0].artifact_path, "artifacts/Store/2026-08-29/extracted.json")
        self.assertEqual(finding.evidence[0].selector, "#flash-banner")


if __name__ == "__main__":
    unittest.main()
