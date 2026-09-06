import { useNavigate } from "react-router-dom";
import { ALL_PATTERNS, PATTERN_ICONS } from "../../config/patterns";

export default function AuditResult({ result }) {
  const navigate = useNavigate();

  if (!result) return null;

  const pages = result.pages || [];
  const rawDarkPatterns = result.dark_pattern_summary || result.detection_results || [];

  // Normalize and map findings to the complete 8 dark patterns
  const darkPatterns = ALL_PATTERNS.map((patternName) => {
    const existing = rawDarkPatterns.find((d) => d.pattern === patternName);
    if (existing) return existing;
    return {
      pattern: patternName,
      status: "INSUFFICIENT_EVIDENCE",
      detected: false,
      confidence: 0,
      reason: `Insufficient page data available to evaluate ${patternName}.`,
      pages_affected_count: 0,
      total_instances: 0,
      evidence: [],
    };
  });

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
        <div>
          <h2 style={{ margin: 0 }}>Audit Summary</h2>
          <p style={{ margin: "4px 0 0 0", color: "#6b7280", fontSize: "14px" }}>
            Multi-page compliance and dark-pattern audit overview stored in MongoDB.
          </p>
        </div>

        <button
          className="primary-btn"
          style={{ width: "auto", padding: "10px 20px", fontSize: "14px", fontWeight: "bold" }}
          onClick={() => navigate(`/evidence?audit_id=${result.audit_id}`)}
        >
          View Evidence Collection →
        </button>
      </div>

      <hr style={{ margin: "20px 0", borderColor: "#e5e7eb" }} />

      {/* Audit Meta Grid */}
      <table className="audit-table">
        <tbody>
          <tr>
            <td><strong>Website Platform</strong></td>
            <td>{result.platform}</td>
            <td><strong>Audit ID</strong></td>
            <td><code>{result.audit_id}</code></td>
          </tr>
          <tr>
            <td><strong>Start URL</strong></td>
            <td colSpan={3}>
              <a href={result.start_url || result.final_url} target="_blank" rel="noreferrer" style={{ color: "#2563eb" }}>
                {result.start_url || result.final_url}
              </a>
            </td>
          </tr>
          <tr>
            <td><strong>Audit Times</strong></td>
            <td>{result.start_time || result.audit_time} &nbsp;→&nbsp; {result.end_time || result.audit_time}</td>
            <td><strong>Audit Status</strong></td>
            <td>
              <span style={{ color: result.status === "completed" ? "#16a34a" : "#ca8a04", fontWeight: "bold" }}>
                ● {result.status ? result.status.toUpperCase() : "COMPLETED"}
              </span>
            </td>
          </tr>
          <tr>
            <td><strong>Configured Crawl Depth</strong></td>
            <td>
              <span style={{ fontWeight: 600 }}>{result.configured_crawl_depth ?? 0}</span>
              {result.actual_max_depth_reached !== undefined && (
                <span style={{ color: "#6b7280", fontSize: "12px", marginLeft: "8px" }}>
                  (Max reached: {result.actual_max_depth_reached})
                </span>
              )}
            </td>
            <td><strong>Pages Crawled</strong></td>
            <td>
              <strong>{result.pages_crawled || pages.length || 1}</strong>
              <span style={{ color: "#16a34a", fontSize: "12px", marginLeft: "8px" }}>
                ({result.pages_successful ?? (result.pages_crawled || 1)} success, {result.pages_failed ?? 0} failed)
              </span>
            </td>
          </tr>
          <tr>
            <td><strong>Total Evidence Items</strong></td>
            <td>
              <span style={{ color: "#2563eb", fontWeight: "bold" }}>
                📁 {result.total_evidence_items ?? result.evidence?.summary?.total_evidence_items ?? 0} Items
              </span>
            </td>
            <td><strong>Total Dark Pattern Findings</strong></td>
            <td>
              <span style={{ color: (result.total_dark_pattern_findings || 0) > 0 ? "#b45309" : "#16a34a", fontWeight: "bold" }}>
                ⚠️ {result.total_dark_pattern_findings ?? 0} Detected Instance(s)
              </span>
            </td>
          </tr>
        </tbody>
      </table>

      <hr style={{ margin: "24px 0", borderColor: "#e5e7eb" }} />

      {/* 8 Dark Pattern Categories Findings */}
      <h3 style={{ marginBottom: "12px" }}>Dark Pattern Detection Engine (8 Categories)</h3>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "14px", marginBottom: "24px" }}>
        {darkPatterns.map((det, idx) => {
          const isDetected = det.status === "DETECTED" || (det.detected && det.status !== "INSUFFICIENT_EVIDENCE" && det.status !== "NOT_EVALUATED");
          const isInsufficient = det.status === "INSUFFICIENT_EVIDENCE" || det.status === "NOT_EVALUATED";
          const isNotDetected = det.status === "NOT_DETECTED" || (!det.detected && !isInsufficient);
          const icon = PATTERN_ICONS[det.pattern] || "⚠️";

          let badgeBg = "#dcfce7";
          let badgeColor = "#166534";
          let badgeText = "Not Detected";
          let cardBg = "#f0fdf4";
          let cardBorder = "#bbf7d0";

          if (isDetected) {
            badgeBg = "#fef3c7";
            badgeColor = "#92400e";
            badgeText = `Detected (${det.confidence}%)`;
            cardBg = "#fffbeb";
            cardBorder = "#fde68a";
          } else if (isInsufficient) {
            badgeBg = "#f1f5f9";
            badgeColor = "#475569";
            badgeText = "Insufficient Evidence";
            cardBg = "#f8fafc";
            cardBorder = "#cbd5e1";
          }

          return (
            <div
              key={idx}
              style={{
                padding: "16px",
                borderRadius: "8px",
                backgroundColor: cardBg,
                border: `1px solid ${cardBorder}`
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <span style={{ fontSize: "15px", fontWeight: "bold", color: isDetected ? "#b45309" : isInsufficient ? "#334155" : "#15803d" }}>
                  {icon} {det.pattern}
                </span>
                <span
                  style={{
                    padding: "3px 10px",
                    borderRadius: "10px",
                    fontSize: "11px",
                    fontWeight: "bold",
                    backgroundColor: badgeBg,
                    color: badgeColor
                  }}
                >
                  {badgeText}
                </span>
              </div>

              <p style={{ margin: "6px 0", fontSize: "13px", color: "#374151", lineHeight: "1.4" }}>
                {det.reason}
              </p>

              {det.metadata?.signals && det.metadata.signals.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", margin: "6px 0" }}>
                  {det.metadata.signals.map((sig, sIdx) => (
                    <span
                      key={sIdx}
                      style={{
                        fontSize: "10px",
                        fontWeight: 700,
                        padding: "2px 6px",
                        borderRadius: "4px",
                        background: "rgba(217, 119, 6, 0.15)",
                        color: "#b45309",
                        textTransform: "uppercase"
                      }}
                    >
                      🏷️ {sig.replace(/_/g, " ")}
                    </span>
                  ))}
                </div>
              )}

              {det.evidence && det.evidence.length > 0 && (
                <div style={{ marginTop: "6px", fontSize: "11px", background: "rgba(255, 255, 255, 0.6)", padding: "6px 10px", borderRadius: "6px", border: "1px solid rgba(0,0,0,0.05)" }}>
                  <strong>Evidence Snippets:</strong>
                  <ul style={{ margin: "2px 0 0 14px", padding: 0 }}>
                    {det.evidence.slice(0, 3).map((ev, eIdx) => (
                      <li key={eIdx} style={{ wordBreak: "break-all" }}>
                        <code>{ev.category}</code>: {ev.text || ev.selector || ev.evidence_id}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {isDetected && det.pages_affected_count !== undefined && (
                <div style={{ marginTop: "8px", fontSize: "12px", color: "#b45309", fontWeight: 600 }}>
                  📍 Affected Pages: {det.pages_affected_count} page(s) ({det.total_instances} instance(s))
                </div>
              )}
            </div>
          );
        })}
      </div>

      <hr style={{ margin: "24px 0", borderColor: "#e5e7eb" }} />

      {/* Page Coverage Breakdown */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
        <h3 style={{ margin: 0 }}>Crawl Coverage Breakdown ({pages.length} Pages)</h3>
        <span style={{ fontSize: "13px", color: "#64748b" }}>
          Maximum Depth Configured: {result.configured_crawl_depth ?? 0}
        </span>
      </div>

      {pages.length === 0 ? (
        <p style={{ color: "#6b7280", fontStyle: "italic" }}>Single page audit completed.</p>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table className="audit-table" style={{ border: "1px solid #e5e7eb", borderRadius: "8px" }}>
            <thead>
              <tr style={{ background: "#f8fafc", textAlign: "left" }}>
                <th style={{ padding: "10px" }}>Page</th>
                <th style={{ padding: "10px" }}>Depth</th>
                <th style={{ padding: "10px" }}>URL</th>
                <th style={{ padding: "10px" }}>Status</th>
                <th style={{ padding: "10px" }}>Evidence</th>
                <th style={{ padding: "10px" }}>Findings</th>
              </tr>
            </thead>
            <tbody>
              {pages.map((p, pIdx) => (
                <tr key={pIdx}>
                  <td style={{ fontWeight: 600 }}>#{p.page_index + 1}</td>
                  <td>
                    <span
                      style={{
                        fontSize: "11px",
                        fontWeight: 700,
                        padding: "2px 6px",
                        borderRadius: "4px",
                        background: "#e2e8f0",
                        color: "#334155"
                      }}
                    >
                      Depth {p.depth}
                    </span>
                  </td>
                  <td style={{ fontSize: "13px", maxWidth: "350px", wordBreak: "break-all" }}>
                    <a href={p.url} target="_blank" rel="noreferrer" style={{ color: "#2563eb" }}>
                      {p.title ? `${p.title} (${p.url})` : p.url}
                    </a>
                  </td>
                  <td>
                    <span style={{ color: p.status === "success" ? "#16a34a" : "#dc2626", fontWeight: 600, fontSize: "12px" }}>
                      ● {p.status === "success" ? "Success" : "Failed"}
                    </span>
                  </td>
                  <td style={{ fontSize: "13px" }}>{p.evidence_count || 0} items</td>
                  <td style={{ fontSize: "13px", fontWeight: p.findings_count > 0 ? "bold" : "normal", color: p.findings_count > 0 ? "#b45309" : "#64748b" }}>
                    {p.findings_count || 0} finding(s)
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Navigation Footer */}
      <div style={{ marginTop: "25px", textAlign: "right" }}>
        <button
          className="primary-btn"
          style={{ width: "auto", padding: "12px 24px", fontSize: "15px", fontWeight: "bold" }}
          onClick={() => navigate(`/evidence?audit_id=${result.audit_id}`)}
        >
          View Full Evidence & Artifacts →
        </button>
      </div>
    </div>
  );
}