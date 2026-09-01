import inspect
import re
import sys
import unittest
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.models.detection_model import DetectionEvidenceRef, DetectionFinding
from app.models.evidence_model import AuditSummary, EvidenceItem, PageSummary
from app.services.automation.crawler_service import run_crawler
from app.services.automation.data_extractor import EXTRACTION_SCRIPT, extract_page_data


class TestSecurityAudit(unittest.TestCase):
    """
    Security review test suite validating that:
    1. Zero secrets/credentials/tokens/cookies are extracted, stored, logged, or persisted.
    2. Interactive browser session transient state is strictly isolated and discarded.
    3. No purchasing, payment, checkout, or order placement actions can ever occur.
    """

    def test_zero_credential_fields_in_pydantic_models(self):
        """Verify that all evidence, detection, and summary models have zero secret fields."""
        models = [DetectionFinding, DetectionEvidenceRef, EvidenceItem, PageSummary, AuditSummary]
        forbidden_keywords = [
            "password", "passwd", "pwd", "secret", "token", "auth_token",
            "access_token", "refresh_token", "jwt", "bearer", "cookie",
            "cookies", "session_id", "otp", "pin", "cvv", "credit_card",
            "card_number", "ssn"
        ]

        for model in models:
            field_names = list(model.model_fields.keys())
            for field in field_names:
                for kw in forbidden_keywords:
                    self.assertNotIn(
                        kw,
                        field.lower(),
                        f"Forbidden secret keyword '{kw}' found in model {model.__name__} field '{field}'"
                    )

    def test_extraction_script_has_no_secret_harvesting(self):
        """Verify that JavaScript extraction script contains no access to storage/cookies/secrets."""
        forbidden_js_patterns = [
            r"localStorage",
            r"sessionStorage",
            r"document\.cookie",
            r"indexedDB",
            r"authorization",
            r"bearer",
            r"apiKey",
            r"api_key"
        ]

        for pat in forbidden_js_patterns:
            matches = re.findall(pat, EXTRACTION_SCRIPT, re.IGNORECASE)
            self.assertEqual(
                len(matches),
                0,
                f"Forbidden JS access pattern '{pat}' found in data extraction script!"
            )

    def test_extraction_script_masks_sensitive_inputs(self):
        """Verify that password, CVV, PIN, and token inputs are strictly masked in extracted forms."""
        self.assertIn("isSensitive", EXTRACTION_SCRIPT)
        self.assertIn("[MASKED]", EXTRACTION_SCRIPT)

    def test_crawler_source_contains_no_purchasing_or_payment_actions(self):
        """Verify that crawler source code does NOT automate checkout, payment, or order placement."""
        crawler_src = inspect.getsource(run_crawler)

        # Ensure browser lifecycle closes context and browser in finally
        self.assertIn("finally:", crawler_src)
        self.assertIn("context.close()", crawler_src)
        self.assertIn("browser.close()", crawler_src)

        # Ensure no checkout or payment completion button is clicked
        forbidden_actions = [
            "place_order",
            "proceed_to_checkout",
            "buy_now",
            "pay_now",
            "submit_payment",
            "complete_purchase"
        ]
        for act in forbidden_actions:
            self.assertNotIn(
                act,
                crawler_src.lower(),
                f"Forbidden purchase action '{act}' found in crawler!"
            )

    def test_crawler_excludes_auth_and_checkout_endpoints(self):
        """Verify that crawler excludes sensitive, login, and payment endpoints from BFS traversal."""
        import app.services.automation.crawler_service as cs
        src = inspect.getsource(cs)

        self.assertIn("EXCLUDED_PATH_PATTERNS", src)
        self.assertIn("/login", src)
        self.assertIn("/checkout", src)
        self.assertIn("/auth", src)


if __name__ == "__main__":
    unittest.main()
