import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fastapi.testclient import TestClient
from app.main import app
from app.services.automation.audit_session_manager import AuditSession, session_manager
from app.services.automation.crawler_service import (
    detect_authentication_required,
    detect_authentication_success,
)
from app.services.dark_patterns.basket_sneaking_detector import BasketSneakingDetector


class TestAuthenticationCheckpointAndCartWorkflow(unittest.TestCase):
    """
    Unit and integration tests for Authentication Checkpoint, Audit Session Manager,
    Controlled Cart Workflow, and Basket Sneaking Preselection Detection.
    """

    def setUp(self):
        self.detector = BasketSneakingDetector()
        self.client = TestClient(app)

    # --- 1. AUTHENTICATION DETECTION TESTS ---

    def test_authentication_detected_from_url_patterns(self):
        """Verifies URL signals (/login, /signin, /account/login, query redirects)."""
        mock_page = MagicMock()
        mock_page.evaluate.return_value = {
            "hasVisiblePassword": False,
            "hasLoginForm": False,
            "authTextMatch": False,
        }

        # Login URL path
        is_req, reason = detect_authentication_required(mock_page, "https://store.example.com/account/login")
        self.assertTrue(is_req)
        self.assertIn("Authentication URL pattern detected", reason)

        # Sign-in URL path
        is_req2, reason2 = detect_authentication_required(mock_page, "https://store.example.com/users/sign_in")
        self.assertTrue(is_req2)

        # Redirect query parameter
        is_req3, reason3 = detect_authentication_required(mock_page, "https://store.example.com/cart?redirect_to=login")
        self.assertTrue(is_req3)

        # Normal product page (not login)
        is_req4, reason4 = detect_authentication_required(mock_page, "https://store.example.com/products/headphones-123")
        self.assertFalse(is_req4)

    def test_authentication_detected_from_dom_signals(self):
        """Verifies DOM signals (visible password input, login forms with gating text)."""
        mock_page = MagicMock()
        mock_page.evaluate.return_value = {
            "hasVisiblePassword": True,
            "hasLoginForm": True,
            "authTextMatch": True,
        }

        # Even with a generic URL, DOM password input triggers authentication checkpoint
        is_req, reason = detect_authentication_required(mock_page, "https://store.example.com/gated-checkout")
        self.assertTrue(is_req)
        self.assertIn("Visible password input", reason)

    def test_authentication_success_detection(self):
        """Verifies DOM and navigation signals indicating user authentication completion."""
        mock_page = MagicMock()
        mock_page.url = "https://store.example.com/account/dashboard"
        mock_page.evaluate.return_value = {
            "visiblePasswordCount": 0,
            "logoutPresent": True,
            "accountMenuPresent": True,
        }

        auth_ok, msg = detect_authentication_success(mock_page, start_login_url="https://store.example.com/login")
        self.assertTrue(auth_ok)
        self.assertIn("logout navigation element detected", msg)

    # --- 2. AUDIT SESSION MANAGER PAUSE & RESUME ---

    def test_audit_session_lifecycle_and_pause_resume(self):
        """Verifies in-memory session creation, authentication checkpoint request, and resume signaling."""
        website = {
            "id": "site_test_123",
            "platform": "TestStore",
            "url": "https://store.example.com",
            "login_required": True,
        }
        audit_id = "audit_teststore_2026_09_27"

        session = session_manager.create_session(audit_id, website)
        self.assertEqual(session.status, "RUNNING")
        self.assertFalse(session.authentication_required)

        # Request Authentication Checkpoint
        session.request_authentication(
            url="https://store.example.com/login",
            reason="Login page encountered"
        )
        self.assertEqual(session.status, "AUTHENTICATION_REQUIRED")
        self.assertTrue(session.authentication_required)
        self.assertEqual(session.authentication_status, "required")
        self.assertFalse(session.resume_event.is_set())

        # Check API status endpoint
        response = self.client.get(f"/api/v1/automation/audit/{audit_id}/status")
        self.assertEqual(response.status_code, 200)
        status_data = response.json()
        self.assertEqual(status_data["status"], "AUTHENTICATION_REQUIRED")
        self.assertTrue(status_data["authentication_required"])

        # Check active session endpoint
        active_resp = self.client.get("/api/v1/automation/active-session/site_test_123")
        self.assertEqual(active_resp.status_code, 200)
        self.assertTrue(active_resp.json().get("active"))

        # Trigger Resume via API
        resume_resp = self.client.post(f"/api/v1/automation/audit/{audit_id}/resume")
        self.assertEqual(resume_resp.status_code, 200)
        self.assertEqual(resume_resp.json()["status"], "RESUMING")
        self.assertTrue(session.resume_event.is_set())
        self.assertEqual(session.status, "RESUMING")
        self.assertEqual(session.authentication_status, "completed")

        # Cleanup
        session_manager.remove_session(audit_id)
        self.assertIsNone(session_manager.get_session(audit_id))

    # --- 3. BASKET SNEAKING DETECTION SCENARIOS ---

    def test_preselected_paid_addon_detected(self):
        """Preselected paid add-on before user interaction -> DETECTED."""
        extracted_data = {
            "url": "https://store.example.com/cart",
            "checkboxes": [
                {
                    "name": "protection_plan",
                    "checked": True,
                    "default_checked": True,
                    "label": "Add 2-Year Extended Device Protection Plan (₹499)",
                    "surrounding_text": "2-Year Extended Device Protection Plan for ₹499",
                    "selector": "#chk_protection",
                    "preselected_before_interaction": True,
                }
            ],
            "cart_items": [
                {"name": "Laptop", "price": "₹65,000"}
            ],
        }
        evidence_record = {"page_url": "https://store.example.com/cart", "evidence_items": []}

        finding = self.detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "DETECTED")
        self.assertTrue(finding.detected)
        self.assertEqual(finding.validation_status, "PASSED")
        self.assertGreaterEqual(finding.model_score, 0.70)
        self.assertTrue(finding.metadata.get("preselected_before_interaction"))

    def test_unchecked_optional_addon_not_detected(self):
        """Optional paid add-on cleanly offered in an unchecked state -> NOT_DETECTED."""
        extracted_data = {
            "url": "https://store.example.com/cart",
            "checkboxes": [
                {
                    "name": "protection_plan",
                    "checked": False,
                    "default_checked": False,
                    "label": "Add 2-Year Extended Device Protection Plan (₹499)",
                    "surrounding_text": "2-Year Extended Device Protection Plan for ₹499",
                    "selector": "#chk_protection",
                }
            ],
            "cart_items": [
                {"name": "Laptop", "price": "₹65,000"}
            ],
        }
        evidence_record = {"page_url": "https://store.example.com/cart", "evidence_items": []}

        finding = self.detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "NOT_DETECTED")
        self.assertFalse(finding.detected)
        self.assertEqual(finding.validation_status, "PASSED")

    def test_user_selected_addon_not_detected(self):
        """Add-on explicitly selected by user interaction -> NOT_DETECTED / USER_SELECTED."""
        extracted_data = {
            "url": "https://store.example.com/cart",
            "checkboxes": [
                {
                    "name": "protection_plan",
                    "checked": True,
                    "selection_origin": "user_selected",
                    "user_selected": True,
                    "label": "Add 2-Year Extended Device Protection Plan (₹499)",
                    "surrounding_text": "2-Year Extended Device Protection Plan for ₹499",
                    "selector": "#chk_protection",
                }
            ],
            "cart_items": [
                {"name": "Laptop", "price": "₹65,000"}
            ],
        }
        evidence_record = {"page_url": "https://store.example.com/cart", "evidence_items": []}

        finding = self.detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "NOT_DETECTED")
        self.assertFalse(finding.detected)

    def test_mandatory_terms_checkbox_not_detected(self):
        """Mandatory terms and conditions checkbox -> NOT_DETECTED (not Basket Sneaking)."""
        extracted_data = {
            "url": "https://store.example.com/checkout",
            "checkboxes": [
                {
                    "name": "terms_agree",
                    "checked": True,
                    "required": True,
                    "label": "I agree to the Terms and Conditions and Privacy Policy",
                    "surrounding_text": "I agree to the Terms of Service and Privacy Policy",
                    "selector": "#chk_terms",
                }
            ],
            "cart_items": [{"name": "Book", "price": "₹299"}],
        }
        evidence_record = {"page_url": "https://store.example.com/checkout", "evidence_items": []}

        finding = self.detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "NOT_DETECTED")
        self.assertFalse(finding.detected)

    def test_clean_cart_not_detected(self):
        """Cart with only clean products and no sneaky add-ons -> NOT_DETECTED."""
        extracted_data = {
            "url": "https://store.example.com/cart",
            "checkboxes": [],
            "cart_items": [
                {"name": "Running Shoes", "price": "₹2,499", "quantity": 1}
            ],
        }
        evidence_record = {"page_url": "https://store.example.com/cart", "evidence_items": []}

        finding = self.detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "NOT_DETECTED")
        self.assertFalse(finding.detected)

    def test_unknown_selection_state_insufficient_evidence(self):
        """Add-on mentioned without determinable DOM checked status -> INSUFFICIENT_EVIDENCE."""
        extracted_data = {
            "url": "https://store.example.com/cart",
            "checkboxes": [
                {
                    "name": "warranty_banner",
                    "checked": None,
                    "default_checked": None,
                    "label": "Optional Extended Warranty ₹399",
                    "surrounding_text": "Optional Extended Warranty ₹399 available",
                    "selector": "#warranty_container",
                }
            ],
        }
        evidence_record = {"page_url": "https://store.example.com/cart", "evidence_items": []}

        finding = self.detector.detect(extracted_data, evidence_record)
        self.assertEqual(finding.status, "INSUFFICIENT_EVIDENCE")
        self.assertFalse(finding.detected)


if __name__ == "__main__":
    unittest.main()
