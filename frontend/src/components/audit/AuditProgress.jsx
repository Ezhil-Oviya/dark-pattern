export default function AuditProgress({ loading }) {
  if (!loading) return null;

  return (
    <div className="card" style={{ borderLeft: "4px solid #2563eb", background: "#f8fafc" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "16px" }}>
        <div
          style={{
            width: "20px",
            height: "20px",
            border: "3px solid #2563eb",
            borderTopColor: "transparent",
            borderRadius: "50%",
            animation: "spin 1s linear infinite"
          }}
        />
        <h2 style={{ margin: 0, fontSize: "18px", color: "#1e293b" }}>
          Automated Crawl & Compliance Audit in Progress...
        </h2>
      </div>

      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "10px", fontSize: "14px", color: "#475569" }}>
        <p style={{ margin: 0 }}>🌐 <strong>Step 1:</strong> Initializing Chromium Browser Context</p>
        <p style={{ margin: 0 }}>🔍 <strong>Step 2:</strong> BFS Multi-Page Queue Navigation</p>
        <p style={{ margin: 0 }}>📸 <strong>Step 3:</strong> Per-Page Screenshot & DOM Capture</p>
        <p style={{ margin: 0 }}>📊 <strong>Step 4:</strong> Structured Page Data Extraction</p>
        <p style={{ margin: 0 }}>📁 <strong>Step 5:</strong> Evidence Record Generation</p>
        <p style={{ margin: 0 }}>⚠️ <strong>Step 6:</strong> Final Four Dark Pattern Analysis</p>
      </div>

      <p style={{ margin: "14px 0 0 0", fontSize: "12px", color: "#64748b", fontStyle: "italic" }}>
        * Multi-page audits explore links up to the configured crawl depth. Please remain on this page while Playwright completes the crawl.
      </p>
    </div>
  );
}