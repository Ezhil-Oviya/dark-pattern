import json
import sys
import unittest
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fastapi.testclient import TestClient
from app.main import app
from app.services.data_quality.data_quality_service import (
    assess_audit_data_quality,
    evaluate_completeness,
    evaluate_validity,
    evaluate_consistency,
    evaluate_relevance,
    evaluate_uniqueness,
    evaluate_evidence_availability,
)


class TestDataQualityAssessment(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def get_sample_complete_audit(self):
        """Builds a high-integrity, complete audit dataset."""
        return {
            "audit_id": "audit_test_quality_complete_2026",
            "platform": "TestStore",
            "start_url": "https://teststore.example.com",
            "configured_crawl_depth": 1,
            "actual_max_depth_reached": 1,
            "max_pages_limit": 10,
            "pages_crawled": 2,
            "pages_successful": 2,
            "pages_failed": 0,
            "total_evidence_items": 4,
            "total_dark_pattern_findings": 1,
            "start_time": "2026-09-01_10-00-00",
            "end_time": "2026-09-01_10-00-20",
            "status": "completed",
            "dark_pattern_summary": [
                {
                    "pattern": "False Urgency",
                    "status": "DETECTED",
                    "detected": True,
                    "confidence": 90,
                    "pages_affected_count": 1,
                    "affected_pages": [{"page_index": 0, "url": "https://teststore.example.com", "depth": 0}],
                    "total_instances": 1,
                    "reason": "Countdown timer detected",
                    "evidence": [
                        {
                            "evidence_id": "ev_p0_urg_1",
                            "evidence_type": "extracted_data",
                            "category": "urgency_elements",
                            "selector": "div.timer",
                            "text": "Deal ends in 05:00",
                            "artifact_path": "api/v1/automation/artifact/test_ext_0",
                        }
                    ],
                }
            ],
            "pages": [
                {
                    "audit_id": "audit_test_quality_complete_2026",
                    "page_index": 0,
                    "folder": "page_000",
                    "url": "https://teststore.example.com",
                    "title": "Home - TestStore Online",
                    "depth": 0,
                    "status": "success",
                    "evidence_count": 2,
                    "findings_count": 1,
                    "artifacts": {
                        "screenshot": "api/v1/automation/artifact/test_scr_0",
                        "dom": "api/v1/automation/artifact/test_dom_0",
                        "extracted_json": "api/v1/automation/artifact/test_ext_0",
                        "evidence_json": "api/v1/automation/artifact/test_ev_0",
                    },
                    "detections": [],
                },
                {
                    "audit_id": "audit_test_quality_complete_2026",
                    "page_index": 1,
                    "folder": "page_001",
                    "url": "https://teststore.example.com/products",
                    "title": "Products Catalog - TestStore",
                    "depth": 1,
                    "status": "success",
                    "evidence_count": 2,
                    "findings_count": 0,
                    "artifacts": {
                        "screenshot": "api/v1/automation/artifact/test_scr_1",
                        "dom": "api/v1/automation/artifact/test_dom_1",
                        "extracted_json": "api/v1/automation/artifact/test_ext_1",
                        "evidence_json": "api/v1/automation/artifact/test_ev_1",
                    },
                    "detections": [],
                },
            ],
        }

    def get_sample_evidence_items(self):
        return [
            {
                "evidence_id": "ev_p0_urg_1",
                "audit_id": "audit_test_quality_complete_2026",
                "page_index": 0,
                "page_url": "https://teststore.example.com",
                "category": "urgency_elements",
                "selector": "div.timer",
                "text": "Deal ends in 05:00",
                "artifact_path": "api/v1/automation/artifact/test_ext_0",
            },
            {
                "evidence_id": "ev_p0_pr_1",
                "audit_id": "audit_test_quality_complete_2026",
                "page_index": 0,
                "page_url": "https://teststore.example.com",
                "category": "prices",
                "selector": "span.price",
                "text": "₹499.00",
                "attributes": {"detected_price": "₹499.00", "currency": "INR"},
                "artifact_path": "api/v1/automation/artifact/test_ext_0",
            },
            {
                "evidence_id": "ev_p1_btn_1",
                "audit_id": "audit_test_quality_complete_2026",
                "page_index": 1,
                "page_url": "https://teststore.example.com/products",
                "category": "buttons",
                "selector": "button.buy-now",
                "text": "Buy Now",
                "artifact_path": "api/v1/automation/artifact/test_ext_1",
            },
            {
                "evidence_id": "ev_p1_lnk_1",
                "audit_id": "audit_test_quality_complete_2026",
                "page_index": 1,
                "page_url": "https://teststore.example.com/products",
                "category": "links",
                "selector": "a.deal-link",
                "text": "Special Deal",
                "artifact_path": "api/v1/automation/artifact/test_ext_1",
            },
        ]

    # Test 1: Complete and high-integrity audit
    def test_complete_audit_quality(self):
        audit = self.get_sample_complete_audit()
        evidence = self.get_sample_evidence_items()

        result = assess_audit_data_quality(audit, evidence)

        self.assertIsNotNone(result.overall_score)
        self.assertGreaterEqual(result.overall_score, 85.0)
        self.assertEqual(result.overall_status, "EXCELLENT")
        self.assertEqual(result.dimensions["completeness"].status, "PASSED")
        self.assertEqual(result.dimensions["validity"].status, "PASSED")
        self.assertEqual(result.dimensions["consistency"].status, "PASSED")
        self.assertEqual(result.dimensions["evidence_availability"].status, "PASSED")
        self.assertEqual(result.details.completeness.total_pages, 2)
        self.assertEqual(result.details.completeness.successful_pages, 2)
        self.assertEqual(result.details.completeness.failed_pages, 0)

    # Test 2: Partially missing audit data
    def test_partially_missing_audit_data(self):
        audit = self.get_sample_complete_audit()
        # Add a failed page missing title, screenshots, DOM, and evidence
        audit["pages"].append({
            "audit_id": audit["audit_id"],
            "page_index": 2,
            "folder": "page_002",
            "url": "https://teststore.example.com/broken",
            "title": "Failed Page",
            "depth": 1,
            "status": "failed",
            "evidence_count": 0,
            "findings_count": 0,
            "artifacts": {},
            "detections": [],
        })
        audit["pages_crawled"] = 3
        audit["pages_failed"] = 1

        result = assess_audit_data_quality(audit, self.get_sample_evidence_items())

        self.assertEqual(result.details.completeness.total_pages, 3)
        self.assertEqual(result.details.completeness.failed_pages, 1)
        self.assertLess(result.dimensions["completeness"].score, 100.0)
        self.assertTrue(any(m.get("page_index") == 2 for m in result.details.completeness.missing_fields))

    # Test 3: Invalid URL, timestamp, and selector formats
    def test_invalid_data_formats(self):
        audit = self.get_sample_complete_audit()
        # Inject bad URL and bad timestamp
        audit["pages"][0]["url"] = "not_a_valid_url"
        audit["start_time"] = "invalid_date_string"

        evidence = [
            {
                "evidence_id": "ev_bad_1",
                "audit_id": audit["audit_id"],
                "page_index": 0,
                "category": "prices",
                "selector": "",  # Empty selector
                "text": "   ",  # Blank text
                "attributes": {"detected_price": "no_numeric_amount"},
                "artifact_path": "invalid_scheme://test",
            }
        ]

        result = assess_audit_data_quality(audit, evidence)

        self.assertLess(result.dimensions["validity"].score, 90.0)
        self.assertGreater(len(result.details.validity.validation_issues), 0)
        issues_categories = [i.category for i in result.details.validity.validation_issues]
        self.assertIn("url", issues_categories)
        self.assertIn("selector", issues_categories)

    # Test 4: Duplicate records detection
    def test_duplicate_records_detection(self):
        audit = self.get_sample_complete_audit()
        # Duplicate page URL
        audit["pages"].append({
            "audit_id": audit["audit_id"],
            "page_index": 2,
            "folder": "page_002",
            "url": "https://teststore.example.com",  # Duplicate of page 0
            "title": "Home - TestStore Online",
            "depth": 1,
            "status": "success",
            "evidence_count": 0,
            "findings_count": 0,
            "artifacts": {},
        })
        # Duplicate evidence items
        evidence = self.get_sample_evidence_items()
        evidence.append(evidence[0].copy())  # Duplicate ev_p0_urg_1

        result = assess_audit_data_quality(audit, evidence)

        self.assertLess(result.dimensions["uniqueness"].score, 100.0)
        self.assertGreater(result.details.uniqueness.duplicate_count, 0)
        dup_types = [d.duplicate_type for d in result.details.uniqueness.duplicates]
        self.assertTrue("duplicate_crawled_url" in dup_types or "duplicate_evidence_id" in dup_types)

    # Test 5: Missing evidence and untraceable detections
    def test_untraceable_detection_findings(self):
        audit = self.get_sample_complete_audit()
        # Add finding with empty evidence array
        audit["dark_pattern_summary"].append({
            "pattern": "Confirmshaming",
            "status": "DETECTED",
            "detected": True,
            "confidence": 80,
            "evidence": [],  # Untraceable
            "affected_pages": [{"page_index": 1, "url": "https://teststore.example.com/products"}],
        })

        result = assess_audit_data_quality(audit, self.get_sample_evidence_items())

        self.assertGreater(result.details.evidence_availability.untraceable_detection_findings, 0)

    # Test 6: Empty audit session handling
    def test_empty_audit_session(self):
        empty_audit = {
            "audit_id": "audit_empty_test",
            "platform": "EmptyStore",
            "start_url": "https://emptystore.example.com",
            "pages_crawled": 0,
            "pages": [],
        }

        result = assess_audit_data_quality(empty_audit, [])

        self.assertIsNone(result.overall_score)
        self.assertEqual(result.overall_status, "INSUFFICIENT_DATA")
        self.assertEqual(result.quality_grade, "N/A")
        self.assertEqual(result.dimensions["completeness"].status, "INSUFFICIENT_DATA")

    # Test 7: Detector readiness evaluation
    def test_detection_readiness_dimensions(self):
        audit = self.get_sample_complete_audit()
        evidence = self.get_sample_evidence_items()

        score_model, relevance_detail = evaluate_relevance(audit, audit["pages"], evidence)

        self.assertEqual(len(relevance_detail.detectors_readiness), 8)
        detector_names = [d.detector_name for d in relevance_detail.detectors_readiness]
        self.assertIn("False Urgency", detector_names)
        self.assertIn("Confirmshaming", detector_names)
        self.assertIn("Drip Pricing", detector_names)
        self.assertIn("Bait and Switch", detector_names)
        self.assertIn("SaaS Billing", detector_names)
        self.assertIn("Interface Interference", detector_names)
        self.assertIn("Forced Action", detector_names)
        self.assertIn("Basket Sneaking", detector_names)
        self.assertGreater(score_model.score, 0.0)


    # Test 8: FastAPI raw evaluation endpoint
    def test_api_raw_evaluation_endpoint(self):
        audit = self.get_sample_complete_audit()
        evidence = self.get_sample_evidence_items()

        response = self.client.post(
            "/api/v1/data-quality/evaluate-raw",
            json={"audit": audit, "evidence_items": evidence},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("overall_score", data)
        self.assertEqual(data["audit_id"], audit["audit_id"])
        self.assertIn("completeness", data["dimensions"])
        self.assertIn("validity", data["dimensions"])
        self.assertIn("consistency", data["dimensions"])
        self.assertIn("relevance", data["dimensions"])
        self.assertIn("uniqueness", data["dimensions"])
        self.assertIn("evidence_availability", data["dimensions"])

    # Test 9: Nonexistent audit ID 404
    def test_api_nonexistent_audit_returns_404(self):
        response = self.client.get("/api/v1/data-quality/audit/nonexistent_audit_id_999999")
        self.assertEqual(response.status_code, 404)

    # Test 11: Detector can be input-ready while returning NOT_DETECTED
    def test_detector_input_ready_while_not_detected(self):
        audit = self.get_sample_complete_audit()
        audit["dark_pattern_summary"].append({
            "pattern": "Drip Pricing",
            "status": "NOT_DETECTED",
            "detected": False,
            "confidence": 0,
            "pages_affected_count": 0,
            "affected_pages": [],
            "total_instances": 0,
            "reason": "Price disclosures appear upfront; no undisclosed fees.",
            "evidence": [],
        })
        evidence = self.get_sample_evidence_items()

        result = assess_audit_data_quality(audit, evidence)
        dp_item = next((p for p in result.details.pattern_readiness_and_sufficiency if p.pattern == "Drip Pricing"), None)
        
        self.assertIsNotNone(dp_item)
        self.assertTrue(dp_item.input_ready)
        self.assertEqual(dp_item.detection_status, "NOT_DETECTED")
        self.assertFalse(dp_item.detected)
        self.assertTrue(dp_item.evidence_sufficient)
        self.assertIn("Price disclosures appear upfront", dp_item.explanation)

    # Test 12: Detector can be input-ready while returning INSUFFICIENT_EVIDENCE
    def test_detector_input_ready_while_insufficient_evidence(self):
        audit = self.get_sample_complete_audit()
        audit["dark_pattern_summary"].append({
            "pattern": "Confirmshaming",
            "status": "INSUFFICIENT_EVIDENCE",
            "detected": False,
            "confidence": 0,
            "pages_affected_count": 0,
            "affected_pages": [],
            "total_instances": 0,
            "reason": "No qualifying interactive opt-out or decline modal elements found.",
            "evidence": [],
        })
        evidence = self.get_sample_evidence_items()

        result = assess_audit_data_quality(audit, evidence)
        cs_item = next((p for p in result.details.pattern_readiness_and_sufficiency if p.pattern == "Confirmshaming"), None)
        
        self.assertIsNotNone(cs_item)
        self.assertTrue(cs_item.input_ready)
        self.assertEqual(cs_item.detection_status, "INSUFFICIENT_EVIDENCE")
        self.assertFalse(cs_item.detected)
        self.assertFalse(cs_item.evidence_sufficient)
        self.assertIn("No qualifying interactive opt-out", cs_item.explanation)

    # Test 13: DETECTED findings contain traceable evidence
    def test_detected_findings_traceable_evidence(self):
        audit = self.get_sample_complete_audit()
        evidence = self.get_sample_evidence_items()

        result = assess_audit_data_quality(audit, evidence)
        fu_item = next((p for p in result.details.pattern_readiness_and_sufficiency if p.pattern == "False Urgency"), None)
        
        self.assertIsNotNone(fu_item)
        self.assertTrue(fu_item.input_ready)
        self.assertEqual(fu_item.detection_status, "DETECTED")
        self.assertTrue(fu_item.detected)
        self.assertTrue(fu_item.evidence_sufficient)
        self.assertEqual(fu_item.affected_pages_count, 1)
        self.assertEqual(fu_item.evidence_instances_count, 1)
        self.assertGreater(fu_item.confidence, 0)

    # Test 14: Missing evidence is not automatically classified as NOT_DETECTED
    def test_missing_evidence_not_converted_to_not_detected(self):
        audit = self.get_sample_complete_audit()
        audit["dark_pattern_summary"].append({
            "pattern": "Bait and Switch",
            "status": "INSUFFICIENT_EVIDENCE",
            "detected": False,
            "confidence": 0,
            "pages_affected_count": 0,
            "affected_pages": [],
            "total_instances": 0,
            "reason": "Insufficient cross-page promotional comparison data.",
            "evidence": [],
        })

        result = assess_audit_data_quality(audit, self.get_sample_evidence_items())
        bs_item = next((p for p in result.details.pattern_readiness_and_sufficiency if p.pattern == "Bait and Switch"), None)
        
        self.assertIsNotNone(bs_item)
        self.assertNotEqual(bs_item.detection_status, "NOT_DETECTED")
        self.assertEqual(bs_item.detection_status, "INSUFFICIENT_EVIDENCE")
        self.assertFalse(bs_item.evidence_sufficient)

    # Test 15: Data Quality score is independent of detection result
    def test_data_quality_score_independent_of_detection_result(self):
        audit_no_violations = self.get_sample_complete_audit()
        audit_no_violations["dark_pattern_summary"] = [
            {"pattern": "False Urgency", "status": "NOT_DETECTED", "detected": False, "confidence": 0, "evidence": []},
            {"pattern": "Confirmshaming", "status": "INSUFFICIENT_EVIDENCE", "detected": False, "confidence": 0, "evidence": []},
        ]

        audit_with_violations = self.get_sample_complete_audit()
        # False Urgency DETECTED already in sample

        res_clean = assess_audit_data_quality(audit_no_violations, self.get_sample_evidence_items())
        res_violation = assess_audit_data_quality(audit_with_violations, self.get_sample_evidence_items())

        # Both audits have identical high data quality scores because data quality measures data hygiene, not violations
        self.assertEqual(res_clean.dimensions["completeness"].score, res_violation.dimensions["completeness"].score)
        self.assertEqual(res_clean.dimensions["validity"].score, res_violation.dimensions["validity"].score)
        self.assertEqual(res_clean.dimensions["consistency"].score, res_violation.dimensions["consistency"].score)
        self.assertEqual(res_clean.dimensions["uniqueness"].score, res_violation.dimensions["uniqueness"].score)

    # Test 16: Evidence Availability does not mean every dark pattern has been detected
    def test_evidence_availability_does_not_imply_pattern_detected(self):
        audit = self.get_sample_complete_audit()
        audit["dark_pattern_summary"] = [
            {"pattern": "False Urgency", "status": "NOT_DETECTED", "detected": False, "confidence": 0, "evidence": []},
            {"pattern": "Confirmshaming", "status": "INSUFFICIENT_EVIDENCE", "detected": False, "confidence": 0, "evidence": []},
            {"pattern": "Drip Pricing", "status": "NOT_DETECTED", "detected": False, "confidence": 0, "evidence": []},
        ]
        evidence = self.get_sample_evidence_items()

        result = assess_audit_data_quality(audit, evidence)
        # 100% evidence availability (screenshots, DOM, extracted JSON present)
        self.assertGreaterEqual(result.dimensions["evidence_availability"].score, 85.0)
        self.assertEqual(result.dimensions["evidence_availability"].status, "PASSED")
        # But zero patterns detected
        for item in result.details.pattern_readiness_and_sufficiency:
            self.assertFalse(item.detected)

    # Test 17: All eight dark patterns appear in pattern_readiness_and_sufficiency
    def test_all_eight_patterns_present_in_assessment(self):
        audit = self.get_sample_complete_audit()
        result = assess_audit_data_quality(audit, self.get_sample_evidence_items())
        
        self.assertEqual(len(result.details.pattern_readiness_and_sufficiency), 8)
        present_names = [p.pattern for p in result.details.pattern_readiness_and_sufficiency]
        expected_patterns = [
            "False Urgency",
            "Drip Pricing",
            "Bait and Switch",
            "Confirmshaming",
            "SaaS Billing",
            "Interface Interference",
            "Forced Action",
            "Basket Sneaking",
        ]
        for ep in expected_patterns:
            self.assertIn(ep, present_names)

    # Test 18: Output values match persisted audit results
    def test_values_match_persisted_audit_results(self):
        audit = self.get_sample_complete_audit()
        audit["dark_pattern_summary"] = [
            {
                "pattern": "False Urgency",
                "status": "DETECTED",
                "detected": True,
                "confidence": 92,
                "pages_affected_count": 1,
                "affected_pages": [{"page_index": 0, "url": "https://teststore.example.com", "depth": 0}],
                "total_instances": 3,
                "reason": "Countdown timer and low-stock indicators detected",
                "evidence": [{"evidence_id": "ev_p0_urg_1"}],
            },
            {
                "pattern": "Confirmshaming",
                "status": "INSUFFICIENT_EVIDENCE",
                "detected": False,
                "confidence": 0,
                "pages_affected_count": 0,
                "affected_pages": [],
                "total_instances": 0,
                "reason": "No qualifying decline button found",
                "evidence": [],
            },
        ]
        result = assess_audit_data_quality(audit, self.get_sample_evidence_items())
        
        fu_item = next(p for p in result.details.pattern_readiness_and_sufficiency if p.pattern == "False Urgency")
        self.assertEqual(fu_item.detection_status, "DETECTED")
        self.assertEqual(fu_item.confidence, 92)
        self.assertEqual(fu_item.affected_pages_count, 1)
        self.assertEqual(fu_item.evidence_instances_count, 3)
        self.assertIn("Countdown timer", fu_item.explanation)

        cs_item = next(p for p in result.details.pattern_readiness_and_sufficiency if p.pattern == "Confirmshaming")
        self.assertEqual(cs_item.detection_status, "INSUFFICIENT_EVIDENCE")
        self.assertEqual(cs_item.affected_pages_count, 0)
        self.assertEqual(cs_item.evidence_instances_count, 0)
        self.assertIn("No qualifying decline button found", cs_item.explanation)


if __name__ == "__main__":
    unittest.main()

