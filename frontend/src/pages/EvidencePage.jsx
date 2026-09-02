import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import Layout from "../components/layout/Layout";
import { getAudits, getAuditDetails } from "../services/automationService";
import { env } from "../config/env";
import "../styles/audit.css";

const API_BASE = env.apiBaseUrl.replace(/\/api\/v1\/?$/, "") + "/";

export default function EvidencePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [audits, setAudits] = useState([]);
  const [selectedAuditId, setSelectedAuditId] = useState(searchParams.get("audit_id") || "");
  const [auditDetails, setAuditDetails] = useState(null);
  const [selectedPageIndex, setSelectedPageIndex] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadAudits();
  }, []);

  useEffect(() => {
    const paramId = searchParams.get("audit_id");
    if (paramId && paramId !== selectedAuditId) {
      setSelectedAuditId(paramId);
    }
  }, [searchParams]);

  useEffect(() => {
    if (selectedAuditId) {
      loadAudit(selectedAuditId);
    }
  }, [selectedAuditId]);

  async function loadAudits() {
    try {
      const list = await getAudits();
      const safeList = Array.isArray(list) ? list : [];
      setAudits(safeList);
      if (safeList.length > 0 && !selectedAuditId) {
        setSelectedAuditId(safeList[0].audit_id);
      }
    } catch (e) {
      console.error("Failed to load audits from MongoDB:", e);
      setAudits([]);
    }
  }


  async function loadAudit(id) {
    try {
      setLoading(true);
      const data = await getAuditDetails(id);
      setAuditDetails(data);
      setSelectedPageIndex(0);
    } catch (e) {
      console.error("Failed to load audit details from MongoDB:", e);
    } finally {
      setLoading(false);
    }
  }

  const handleAuditChange = (e) => {
    const newId = e.target.value;
    setSelectedAuditId(newId);
    setSearchParams({ audit_id: newId });
  };

  const pages = auditDetails?.pages || [];
  const selectedPage = pages[selectedPageIndex] || pages[0] || null;
  const artifacts = selectedPage?.artifacts || {};

  // Resolve MongoDB GridFS artifact streaming link
  const getArtifactUrl = (rawPath) => {
    if (!rawPath) return "";
    if (rawPath.startsWith("http")) return rawPath;
    if (rawPath.startsWith("/")) return `${API_BASE}${rawPath.slice(1)}`;
    return `${API_BASE}${rawPath}`;
  };

  return (
    <Layout>
      <div style={{ padding: "10px 0" }}>
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "15px" }}>
            <div>
              <h2 style={{ margin: 0 }}>Evidence Collection</h2>
              <p style={{ margin: "4px 0 0 0", color: "#6b7280", fontSize: "14px" }}>
                Inspect physical artifacts, rendered DOMs, screenshots, and granular evidence stored in MongoDB.
              </p>
            </div>

            <div style={{ minWidth: "320px" }}>
              <label style={{ fontSize: "13px", color: "#374151", marginBottom: "4px" }}>Select Audit Session (MongoDB)</label>
              <select
                value={selectedAuditId}
                onChange={handleAuditChange}
                style={{ marginBottom: 0, padding: "8px 12px", fontSize: "14px" }}
              >
                {audits.length === 0 && <option value="">No completed audits found in MongoDB</option>}
                {audits.map((a) => (
                  <option key={a.audit_id} value={a.audit_id}>
                    {a.platform} - {a.start_time} ({a.pages_crawled} pages)
                  </option>
                ))}
              </select>
            </div>
          </div>

          {auditDetails && (
            <>
              <hr style={{ margin: "20px 0", borderColor: "#e5e7eb" }} />
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "12px" }}>
                <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                  <div style={{ fontSize: "12px", color: "#64748b", fontWeight: 600 }}>PAGES CRAWLED</div>
                  <div style={{ fontSize: "20px", fontWeight: "bold", color: "#0f172a", marginTop: "4px" }}>
                    {auditDetails.pages_crawled || pages.length}
                  </div>
                </div>

                <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                  <div style={{ fontSize: "12px", color: "#64748b", fontWeight: 600 }}>EVIDENCE ITEMS</div>
                  <div style={{ fontSize: "20px", fontWeight: "bold", color: "#2563eb", marginTop: "4px" }}>
                    {auditDetails.total_evidence_items ?? 0}
                  </div>
                </div>

                <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                  <div style={{ fontSize: "12px", color: "#64748b", fontWeight: 600 }}>SCREENSHOTS (GRIDFS)</div>
                  <div style={{ fontSize: "20px", fontWeight: "bold", color: "#0891b2", marginTop: "4px" }}>
                    {pages.filter(p => p.artifacts?.screenshot).length}
                  </div>
                </div>

                <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                  <div style={{ fontSize: "12px", color: "#64748b", fontWeight: 600 }}>DOM RECORDS (GRIDFS)</div>
                  <div style={{ fontSize: "20px", fontWeight: "bold", color: "#059669", marginTop: "4px" }}>
                    {pages.filter(p => p.artifacts?.dom).length}
                  </div>
                </div>

                <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                  <div style={{ fontSize: "12px", color: "#64748b", fontWeight: 600 }}>DETECTED FINDINGS</div>
                  <div style={{ fontSize: "20px", fontWeight: "bold", color: "#d97706", marginTop: "4px" }}>
                    {auditDetails.total_dark_pattern_findings ?? 0}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

        {loading ? (
          <div className="card" style={{ textAlign: "center", padding: "40px" }}>
            <h3>Loading Audit Evidence from MongoDB...</h3>
          </div>
        ) : !auditDetails ? (
          <div className="card" style={{ textAlign: "center", padding: "40px" }}>
            <h3>No Audit Selected</h3>
            <p>Please select an audit from the dropdown above to view collected evidence.</p>
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: "20px", alignItems: "start" }}>
            {/* Left Column: Pages List */}
            <div className="card" style={{ padding: "16px", maxHeight: "800px", overflowY: "auto" }}>
              <h3 style={{ margin: "0 0 12px 0", fontSize: "16px" }}>
                Crawled Pages ({pages.length})
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {pages.map((p, idx) => {
                  const isSelected = idx === selectedPageIndex;
                  return (
                    <div
                      key={idx}
                      onClick={() => setSelectedPageIndex(idx)}
                      style={{
                        padding: "12px",
                        borderRadius: "8px",
                        border: `1px solid ${isSelected ? "#2563eb" : "#e5e7eb"}`,
                        background: isSelected ? "#eff6ff" : "#ffffff",
                        cursor: "pointer",
                        transition: "0.2s"
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                        <span
                          style={{
                            fontSize: "11px",
                            fontWeight: 700,
                            padding: "2px 6px",
                            borderRadius: "4px",
                            background: isSelected ? "#2563eb" : "#e2e8f0",
                            color: isSelected ? "#ffffff" : "#475569"
                          }}
                        >
                          Depth {p.depth}
                        </span>
                        <span style={{ fontSize: "11px", color: p.status === "success" ? "#16a34a" : "#dc2626", fontWeight: 600 }}>
                          ● {p.status === "success" ? "Success" : "Failed"}
                        </span>
                      </div>

                      <div style={{ fontSize: "13px", fontWeight: 600, color: "#1e293b", wordBreak: "break-all" }}>
                        {p.title || p.url}
                      </div>

                      <div style={{ fontSize: "12px", color: "#64748b", marginTop: "4px", wordBreak: "break-all" }}>
                        {p.url}
                      </div>

                      <div style={{ display: "flex", gap: "10px", marginTop: "8px", fontSize: "11px", color: "#475569" }}>
                        <span>📁 {p.evidence_count || 0} Evidence</span>
                        <span style={{ color: p.findings_count > 0 ? "#b45309" : "#64748b", fontWeight: p.findings_count > 0 ? "bold" : "normal" }}>
                          ⚠️ {p.findings_count || 0} Findings
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Right Column: Selected Page Detail */}
            {selectedPage && (
              <div className="card">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "10px" }}>
                  <div>
                    <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                      <span
                        style={{
                          background: "#2563eb",
                          color: "#fff",
                          padding: "2px 8px",
                          borderRadius: "4px",
                          fontSize: "12px",
                          fontWeight: "bold"
                        }}
                      >
                        Page #{selectedPageIndex + 1}
                      </span>
                      <span
                        style={{
                          background: "#f1f5f9",
                          color: "#334155",
                          padding: "2px 8px",
                          borderRadius: "4px",
                          fontSize: "12px",
                          fontWeight: "bold"
                        }}
                      >
                        Depth {selectedPage.depth}
                      </span>
                    </div>
                    <h3 style={{ margin: "8px 0 4px 0", fontSize: "18px" }}>
                      {selectedPage.title || "Page Evidence"}
                    </h3>
                    <a
                      href={selectedPage.url}
                      target="_blank"
                      rel="noreferrer"
                      style={{ fontSize: "13px", color: "#2563eb", wordBreak: "break-all" }}
                    >
                      {selectedPage.url} ↗
                    </a>
                  </div>
                </div>

                <hr style={{ margin: "16px 0", borderColor: "#e5e7eb" }} />

                <h4 style={{ margin: "0 0 10px 0" }}>Page Artifacts (GridFS Stream)</h4>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "10px", marginBottom: "20px" }}>
                  {artifacts.screenshot && (
                    <a
                      href={getArtifactUrl(artifacts.screenshot)}
                      target="_blank"
                      rel="noreferrer"
                      style={{
                        padding: "8px 14px",
                        background: "#2563eb",
                        color: "#fff",
                        borderRadius: "6px",
                        textDecoration: "none",
                        fontSize: "13px",
                        fontWeight: 500
                      }}
                    >
                      📸 Screenshot (PNG)
                    </a>
                  )}

                  {artifacts.dom && (
                    <a
                      href={getArtifactUrl(artifacts.dom)}
                      target="_blank"
                      rel="noreferrer"
                      style={{
                        padding: "8px 14px",
                        background: "#0891b2",
                        color: "#fff",
                        borderRadius: "6px",
                        textDecoration: "none",
                        fontSize: "13px",
                        fontWeight: 500
                      }}
                    >
                      🌐 Raw DOM (HTML)
                    </a>
                  )}

                  {artifacts.extracted_json && (
                    <a
                      href={getArtifactUrl(artifacts.extracted_json)}
                      target="_blank"
                      rel="noreferrer"
                      style={{
                        padding: "8px 14px",
                        background: "#059669",
                        color: "#fff",
                        borderRadius: "6px",
                        textDecoration: "none",
                        fontSize: "13px",
                        fontWeight: 500
                      }}
                    >
                      📊 Extracted Data (JSON)
                    </a>
                  )}

                  {artifacts.evidence_json && (
                    <a
                      href={getArtifactUrl(artifacts.evidence_json)}
                      target="_blank"
                      rel="noreferrer"
                      style={{
                        padding: "8px 14px",
                        background: "#7c3aed",
                        color: "#fff",
                        borderRadius: "6px",
                        textDecoration: "none",
                        fontSize: "13px",
                        fontWeight: 500
                      }}
                    >
                      🔍 Evidence Record (JSON)
                    </a>
                  )}
                </div>

                {/* Page Findings (Final Four Dark Patterns) */}
                {selectedPage.detections && selectedPage.detections.length > 0 && (
                  <>
                    <hr style={{ margin: "16px 0", borderColor: "#e5e7eb" }} />
                    <h4 style={{ margin: "0 0 10px 0" }}>Page Dark Pattern Analysis</h4>
                    <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginBottom: "20px" }}>
                      {selectedPage.detections.map((det, dIdx) => {
                        const isDetected = det.status === "DETECTED" || (det.detected && det.status !== "INSUFFICIENT_EVIDENCE" && det.status !== "NOT_EVALUATED");
                        const isInsufficient = det.status === "INSUFFICIENT_EVIDENCE" || det.status === "NOT_EVALUATED";
                        let statusText = "Not Detected";
                        let statusBg = "#dcfce7";
                        let statusColor = "#166534";
                        let borderC = "#bbf7d0";
                        let bgC = "#f0fdf4";

                        if (isDetected) {
                          statusText = "Potential Dark Pattern Detected";
                          statusBg = "#fef3c7";
                          statusColor = "#92400e";
                          borderC = "#fde68a";
                          bgC = "#fffbeb";
                        } else if (isInsufficient) {
                          statusText = "Insufficient Evidence";
                          statusBg = "#f1f5f9";
                          statusColor = "#475569";
                          borderC = "#cbd5e1";
                          bgC = "#f8fafc";
                        }

                        return (
                          <div
                            key={dIdx}
                            style={{
                              padding: "12px 16px",
                              borderRadius: "8px",
                              background: bgC,
                              border: `1px solid ${borderC}`
                            }}
                          >
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                              <strong style={{ color: isDetected ? "#92400e" : isInsufficient ? "#334155" : "#166534" }}>
                                {det.pattern}: {statusText}
                              </strong>
                              <span
                                style={{
                                  fontSize: "11px",
                                  fontWeight: "bold",
                                  padding: "2px 8px",
                                  borderRadius: "10px",
                                  background: statusBg,
                                  color: statusColor
                                }}
                              >
                                {isDetected ? `Confidence: ${det.confidence}%` : isInsufficient ? "Status: Insufficient Evidence" : "Confidence: 0%"}
                              </span>
                            </div>
                            <p style={{ margin: "6px 0 0 0", fontSize: "13px", color: "#374151" }}>
                              {det.reason}
                            </p>
                            {det.evidence && det.evidence.length > 0 && (
                              <div style={{ marginTop: "8px", fontSize: "12px" }}>
                                <strong>Evidence Elements:</strong>
                                <ul style={{ margin: "4px 0 0 16px", padding: 0 }}>
                                  {det.evidence.map((ev, eIdx) => (
                                    <li key={eIdx}>
                                      <code>{ev.category}</code>: {ev.text || ev.selector || ev.evidence_id}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </>
                )}

                {/* Screenshot Viewer via GridFS URL */}
                {artifacts.screenshot && (
                  <>
                    <hr style={{ margin: "16px 0", borderColor: "#e5e7eb" }} />
                    <h4 style={{ margin: "0 0 10px 0" }}>Rendered Page Screenshot (MongoDB GridFS)</h4>
                    <div style={{ maxHeight: "500px", overflowY: "auto", border: "1px solid #e5e7eb", borderRadius: "8px" }}>
                      <img
                        src={getArtifactUrl(artifacts.screenshot)}
                        alt={`Screenshot for ${selectedPage.url}`}
                        style={{ width: "100%", display: "block" }}
                      />
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </Layout>
  );
}
