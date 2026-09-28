import logging
import threading
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AuditSession:
    """
    Manages in-memory state and synchronization for an active audit run,
    enabling non-invasive pause/resume for interactive authentication checkpoints.
    """

    def __init__(self, audit_id: str, website: Dict[str, Any]):
        self.audit_id = audit_id
        self.website_id = str(website.get("id") or website.get("_id") or "")
        self.platform = website.get("platform", "Platform")
        self.start_url = website.get("url", "")
        self.status = "RUNNING"  # "RUNNING", "AUTHENTICATION_REQUIRED", "RESUMING", "COMPLETED", "FAILED"
        self.authentication_required = False
        self.authentication_status = "not_required"  # "not_required", "required", "completed", "failed"
        self.current_stage = "Initializing Browser Session"
        self.current_url = self.start_url
        self.page_index = 0
        self.paused_at: Optional[str] = None
        self.resumed_at: Optional[str] = None
        self.resume_event = threading.Event()
        self.message = "Audit is running normally."
        self.error: Optional[str] = None
        self.result: Optional[Dict[str, Any]] = None
        self.created_at = datetime.now().isoformat()

    def request_authentication(self, url: str, reason: str):
        """Pauses the crawl and marks the session as requiring manual user authentication."""
        self.status = "AUTHENTICATION_REQUIRED"
        self.authentication_required = True
        self.authentication_status = "required"
        self.current_url = url
        self.paused_at = datetime.now().isoformat()
        self.current_stage = f"Authentication Required: {reason}"
        self.message = "Please complete login in the visible browser session, then click Resume Audit or wait for automatic detection."
        self.resume_event.clear()
        logger.info(f"[AuditSession {self.audit_id}] Status -> AUTHENTICATION_REQUIRED: {reason}")

    def signal_resume(self, source: str = "manual"):
        """Signals the waiting crawler thread to resume after authentication."""
        self.status = "RESUMING"
        self.authentication_status = "completed"
        self.resumed_at = datetime.now().isoformat()
        self.current_stage = f"Resuming audit ({source})..."
        self.message = "Authentication confirmed. Continuing crawl and cart workflow..."
        self.resume_event.set()
        logger.info(f"[AuditSession {self.audit_id}] Status -> RESUMING (source: {source})")

    def to_dict(self) -> Dict[str, Any]:
        """Returns non-sensitive session metadata for the API/frontend."""
        return {
            "audit_id": self.audit_id,
            "website_id": self.website_id,
            "platform": self.platform,
            "status": self.status,
            "authentication_required": self.authentication_required,
            "authentication_status": self.authentication_status,
            "current_stage": self.current_stage,
            "current_url": self.current_url,
            "page_index": self.page_index,
            "paused_at": self.paused_at,
            "resumed_at": self.resumed_at,
            "message": self.message,
            "error": self.error,
        }


class AuditSessionManager:
    """Thread-safe registry of active audit sessions."""

    def __init__(self):
        self._sessions: Dict[str, AuditSession] = {}
        self._website_active_audit: Dict[str, str] = {}
        self._lock = threading.Lock()

    def create_session(self, audit_id: str, website: Dict[str, Any]) -> AuditSession:
        with self._lock:
            session = AuditSession(audit_id, website)
            self._sessions[audit_id] = session
            w_id = session.website_id
            if w_id:
                self._website_active_audit[w_id] = audit_id
            return session

    def get_session(self, audit_id: str) -> Optional[AuditSession]:
        with self._lock:
            return self._sessions.get(audit_id)

    def get_active_session_for_website(self, website_id: str) -> Optional[AuditSession]:
        with self._lock:
            audit_id = self._website_active_audit.get(website_id)
            if audit_id:
                session = self._sessions.get(audit_id)
                if session and session.status in ("RUNNING", "AUTHENTICATION_REQUIRED", "RESUMING"):
                    return session
            return None

    def resume_session(self, audit_id: str) -> bool:
        with self._lock:
            session = self._sessions.get(audit_id)
            if not session:
                return False
            session.signal_resume(source="manual_api")
            return True

    def complete_session(self, audit_id: str, result: Dict[str, Any]):
        with self._lock:
            session = self._sessions.get(audit_id)
            if session:
                session.status = "COMPLETED"
                session.result = result
                session.current_stage = "Audit completed successfully"

    def fail_session(self, audit_id: str, error: str):
        with self._lock:
            session = self._sessions.get(audit_id)
            if session:
                session.status = "FAILED"
                session.error = error
                session.current_stage = f"Audit failed: {error}"

    def remove_session(self, audit_id: str):
        with self._lock:
            if audit_id in self._sessions:
                s = self._sessions.pop(audit_id)
                if s.website_id in self._website_active_audit and self._website_active_audit[s.website_id] == audit_id:
                    del self._website_active_audit[s.website_id]


session_manager = AuditSessionManager()
