import json
import sys
import unittest
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.config.database import check_mongo_connection
from app.services.evidence.mongodb_evidence_service import (
    get_all_audits_from_mongodb,
    get_audit_details_from_mongodb,
    get_evidence_items_from_mongodb,
    get_gridfs_artifact,
    save_audit_to_mongodb,
    store_artifact_in_gridfs,
)

is_mongo_online, _ = check_mongo_connection()


class TestMongoDBEvidencePersistence(unittest.TestCase):
    @unittest.skipUnless(is_mongo_online, "MongoDB connection is offline or inaccessible")
    def test_gridfs_artifact_storage_and_retrieval(self):
        """Tests uploading binary artifacts to GridFS and retrieving them with metadata."""
        sample_screenshot = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRmock_png_bytes"
        file_id = store_artifact_in_gridfs(
            content=sample_screenshot,
            filename="test_screenshot.png",
            content_type="image/png",
            metadata={"test_tag": "unit_test"}
        )
        self.assertIsNotNone(file_id)

        # Retrieve and verify
        content, filename, content_type = get_gridfs_artifact(file_id)
        self.assertEqual(content, sample_screenshot)
        self.assertEqual(filename, "test_screenshot.png")
        self.assertEqual(content_type, "image/png")

    @unittest.skipUnless(is_mongo_online, "MongoDB connection is offline or inaccessible")
    def test_audit_pages_and_evidence_persistence_and_query(self):
        """Tests saving and retrieving a complete audit with pages and evidence items in MongoDB."""
        test_audit_id = f"test_audit_mongo_{Path(__file__).stat().st_mtime_ns}"

        audit_summary = {
            "audit_id": test_audit_id,
            "website_id": "mock_web_123",
            "platform": "TestStore",
            "start_url": "https://teststore.example/",
            "configured_crawl_depth": 1,
            "actual_max_depth_reached": 1,
            "max_pages_limit": 10,
            "pages_crawled": 2,
            "pages_successful": 2,
            "pages_failed": 0,
            "total_evidence_items": 5,
            "total_dark_pattern_findings": 1,
            "start_time": "2026-08-30_12-00-00",
            "end_time": "2026-08-30_12-00-15",
            "status": "completed",
            "dark_pattern_summary": [
                {
                    "pattern": "Basket Sneaking",
                    "status": "NOT_EVALUATED",
                    "detected": False,
                    "confidence": 0,
                    "pages_affected_count": 0,
                    "affected_pages": [],
                    "total_instances": 0,
                    "reason": "Not evaluated",
                    "evidence": []
                },
                {
                    "pattern": "False Urgency",
                    "status": "DETECTED",
                    "detected": True,
                    "confidence": 90,
                    "pages_affected_count": 1,
                    "affected_pages": [{"page_index": 0, "url": "https://teststore.example/", "depth": 0}],
                    "total_instances": 1,
                    "reason": "Countdown timer detected",
                    "evidence": [{"evidence_id": "ev_test_1", "text": "05:00 left"}]
                }
            ]
        }

        pages_data = [
            {
                "audit_id": test_audit_id,
                "page_index": 0,
                "folder": "page_000",
                "url": "https://teststore.example/",
                "title": "Homepage",
                "depth": 0,
                "status": "success",
                "evidence_count": 3,
                "findings_count": 1,
                "artifacts": {
                    "screenshot": "api/v1/automation/artifact/mock_scr_0",
                    "dom": "api/v1/automation/artifact/mock_dom_0"
                },
                "detections": []
            },
            {
                "audit_id": test_audit_id,
                "page_index": 1,
                "folder": "page_001",
                "url": "https://teststore.example/products",
                "title": "Products",
                "depth": 1,
                "status": "success",
                "evidence_count": 2,
                "findings_count": 0,
                "artifacts": {
                    "screenshot": "api/v1/automation/artifact/mock_scr_1",
                    "dom": "api/v1/automation/artifact/mock_dom_1"
                },
                "detections": []
            }
        ]

        evidence_items = [
            {
                "evidence_id": "ev_test_1",
                "audit_id": test_audit_id,
                "page_index": 0,
                "page_url": "https://teststore.example/",
                "page_title": "Homepage",
                "crawl_depth": 0,
                "evidence_type": "extracted_data",
                "category": "urgency_elements",
                "selector": "span.timer",
                "text": "05:00 left",
                "artifact_path": "api/v1/automation/artifact/mock_extracted_0"
            }
        ]

        # Save to MongoDB
        saved_id = save_audit_to_mongodb(audit_summary, pages_data, evidence_items)
        self.assertEqual(saved_id, test_audit_id)

        # Retrieve and verify audit details
        retrieved_audit = get_audit_details_from_mongodb(test_audit_id)
        self.assertIsNotNone(retrieved_audit)
        self.assertEqual(retrieved_audit["platform"], "TestStore")
        self.assertEqual(retrieved_audit["pages_crawled"], 2)
        self.assertEqual(len(retrieved_audit["pages"]), 2)
        self.assertEqual(retrieved_audit["pages"][0]["title"], "Homepage")

        # Retrieve evidence items
        items = get_evidence_items_from_mongodb(test_audit_id, page_index=0)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["text"], "05:00 left")

        # Verify audit listed in all audits query
        all_audits = get_all_audits_from_mongodb()
        self.assertTrue(any(a.get("audit_id") == test_audit_id for a in all_audits))


if __name__ == "__main__":
    unittest.main()
