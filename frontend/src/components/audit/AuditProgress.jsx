export default function AuditProgress({
  loading,
  auditSession,
  onResume,
  resuming
}) {
  if (!loading) return null;

  const isAuthRequired =
    auditSession?.status === "AUTHENTICATION_REQUIRED" ||
    (auditSession?.authentication_required && auditSession?.authentication_status === "required");

  const isResuming = auditSession?.status === "RESUMING";

  if (isAuthRequired) {
    return (
      <div
        className="card"
        style={{
          borderLeft: "5px solid #f59e0b",
          background: "linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%)",
          boxShadow: "0 10px 25px -5px rgba(245, 158, 11, 0.15)",
          borderRadius: "12px",
          padding: "24px",
          margin: "20px 0"
        }}
      >
        <div style={{ display: "flex", alignItems: "flex-start", gap: "16px" }}>
          <div
            style={{
              fontSize: "32px",
              lineHeight: 1,
              background: "#fef3c7",
              padding: "12px",
              borderRadius: "12px",
              border: "1px solid #fde68a"
            }}
          >
            🔐
          </div>

          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
              <span
                style={{
                  background: "#d97706",
                  color: "#ffffff",
                  fontSize: "11px",
                  fontWeight: "700",
                  padding: "3px 8px",
                  borderRadius: "4px",
                  letterSpacing: "0.05em",
                  textTransform: "uppercase"
                }}
              >
                Authentication Required
              </span>
              <span style={{ fontSize: "13px", color: "#92400e", fontWeight: "500" }}>
                Interactive Checkpoint
              </span>
            </div>

            <h2 style={{ margin: "0 0 8px 0", fontSize: "20px", color: "#78350f", fontWeight: "700" }}>
              Please Complete Login in the Visible Browser
            </h2>

            <p style={{ margin: "0 0 16px 0", fontSize: "14px", color: "#92400e", lineHeight: 1.6 }}>
              The auditor detected that this e-commerce site requires login before accessing products or shopping cart features.
              The Playwright browser session is active and visible. <strong>Please enter your credentials manually in the browser</strong>.
              No credentials are saved or collected by the auditor.
            </p>

            {auditSession?.current_url && (
              <div
                style={{
                  background: "#ffffff",
                  padding: "10px 14px",
                  borderRadius: "8px",
                  border: "1px solid #fde68a",
                  marginBottom: "18px",
                  fontSize: "13px",
                  color: "#475569"
                }}
              >
                <strong>Checkpoint URL:</strong>{" "}
                <code style={{ color: "#b45309", background: "#fef3c7", padding: "2px 6px", borderRadius: "4px" }}>
                  {auditSession.current_url}
                </code>
              </div>
            )}

            <div style={{ display: "flex", alignItems: "center", gap: "14px", flexWrap: "wrap" }}>
              <button
                type="button"
                onClick={onResume}
                disabled={resuming}
                style={{
                  background: resuming ? "#94a3b8" : "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: "8px",
                  padding: "10px 22px",
                  fontSize: "14px",
                  fontWeight: "600",
                  cursor: resuming ? "not-allowed" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  boxShadow: "0 4px 12px rgba(37, 99, 235, 0.25)",
                  transition: "all 0.2s ease"
                }}
              >
                {resuming ? (
                  <>
                    <span
                      style={{
                        width: "14px",
                        height: "14px",
                        border: "2px solid #ffffff",
                        borderTopColor: "transparent",
                        borderRadius: "50%",
                        animation: "spin 1s linear infinite",
                        display: "inline-block"
                      }}
                    />
                    Resuming Audit...
                  </>
                ) : (
                  <>
                    <span>▶</span>
                    Resume Audit
                  </>
                )}
              </button>

              <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "#b45309" }}>
                <span
                  style={{
                    width: "8px",
                    height: "8px",
                    background: "#f59e0b",
                    borderRadius: "50%",
                    display: "inline-block",
                    animation: "pulse 1.5s ease-in-out infinite"
                  }}
                />
                <span>Awaiting user login or auto-detection...</span>
              </div>
            </div>
          </div>
        </div>

        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
          @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(1.3); }
          }
        `}</style>
      </div>
    );
  }

  return (
    <div
      className="card"
      style={{
        borderLeft: isResuming ? "4px solid #10b981" : "4px solid #2563eb",
        background: "#f8fafc",
        borderRadius: "12px",
        padding: "20px",
        margin: "20px 0"
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "16px" }}>
        <div
          style={{
            width: "20px",
            height: "20px",
            border: isResuming ? "3px solid #10b981" : "3px solid #2563eb",
            borderTopColor: "transparent",
            borderRadius: "50%",
            animation: "spin 1s linear infinite"
          }}
        />
        <div>
          <h2 style={{ margin: 0, fontSize: "18px", color: "#1e293b" }}>
            {isResuming
              ? "Authentication Completed — Continuing Audit..."
              : "Automated Crawl & Compliance Audit in Progress..."}
          </h2>
          {auditSession?.current_stage && (
            <p style={{ margin: "4px 0 0 0", fontSize: "13px", color: "#64748b" }}>
              {auditSession.current_stage}
            </p>
          )}
        </div>
      </div>

      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "10px",
          fontSize: "14px",
          color: "#475569"
        }}
      >
        <p style={{ margin: 0 }}>🌐 <strong>Step 1:</strong> Initializing Chromium Session</p>
        <p style={{ margin: 0 }}>🔍 <strong>Step 2:</strong> BFS Queue & Page Exploration</p>
        <p style={{ margin: 0 }}>🛒 <strong>Step 3:</strong> Controlled Product & Cart Workflow</p>
        <p style={{ margin: 0 }}>📸 <strong>Step 4:</strong> Per-Page Screenshot & DOM Capture</p>
        <p style={{ margin: 0 }}>📊 <strong>Step 5:</strong> Structured Data Extraction</p>
        <p style={{ margin: 0 }}>⚠️ <strong>Step 6:</strong> MiniLM AI & Hybrid Pattern Analysis</p>
      </div>

      <p style={{ margin: "14px 0 0 0", fontSize: "12px", color: "#64748b", fontStyle: "italic" }}>
        * Multi-page audits explore links up to the configured crawl depth and inspect e-commerce cart flows for Basket Sneaking.
      </p>
    </div>
  );
}