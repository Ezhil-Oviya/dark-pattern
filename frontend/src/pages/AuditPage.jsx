import { useState, useRef, useEffect } from "react";

import Layout from "../components/layout/Layout";
import AuditForm from "../components/audit/AuditForm";
import AuditProgress from "../components/audit/AuditProgress";
import AuditResult from "../components/audit/AuditResult";

import {
  startAudit,
  getActiveSession,
  getAuditStatus,
  resumeAudit
} from "../services/automationService";

import "../styles/audit.css";

export default function AuditPage() {
  const [loading, setLoading] = useState(false);
  const [auditSession, setAuditSession] = useState(null);
  const [resuming, setResuming] = useState(false);
  const [result, setResult] = useState(null);
  const pollingTimerRef = useRef(null);

  const startPolling = (websiteId) => {
    if (pollingTimerRef.current) {
      clearInterval(pollingTimerRef.current);
    }

    pollingTimerRef.current = setInterval(async () => {
      try {
        const sessionData = await getActiveSession(websiteId);
        if (sessionData && sessionData.active) {
          setAuditSession(sessionData);
          if (sessionData.status === "RESUMING") {
            setResuming(true);
          } else if (sessionData.status !== "AUTHENTICATION_REQUIRED") {
            setResuming(false);
          }
        }
      } catch (err) {
        // Quiet poll error
      }
    }, 1500);
  };

  const stopPolling = () => {
    if (pollingTimerRef.current) {
      clearInterval(pollingTimerRef.current);
      pollingTimerRef.current = null;
    }
  };

  useEffect(() => {
    return () => stopPolling();
  }, []);

  async function handleAudit(id) {
    try {
      setLoading(true);
      setResult(null);
      setAuditSession(null);
      setResuming(false);

      startPolling(id);

      const data = await startAudit(id);

      setResult(data);
      setAuditSession(null);
    } catch (e) {
      console.error("Audit error:", e);
      const detail = e.response?.data?.detail || e.message || "Audit Failed";
      alert(`Audit Failed: ${detail}`);
    } finally {
      stopPolling();
      setLoading(false);
      setResuming(false);
    }
  }

  async function handleResume() {
    if (!auditSession?.audit_id) return;
    try {
      setResuming(true);
      await resumeAudit(auditSession.audit_id);
    } catch (e) {
      console.error("Resume error:", e);
      const detail = e.response?.data?.detail || e.message || "Resume failed";
      alert(`Resume failed: ${detail}`);
      setResuming(false);
    }
  }

  return (
    <Layout>
      <AuditForm onStart={handleAudit} loading={loading} />

      <AuditProgress
        loading={loading}
        auditSession={auditSession}
        onResume={handleResume}
        resuming={resuming}
      />

      <AuditResult result={result} />
    </Layout>
  );
}