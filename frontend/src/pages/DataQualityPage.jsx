import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  Database,
  Layers,
  FileCheck2,
  ShieldCheck,
  Search,
  CopyCheck,
  FileText,
  Camera,
  Globe,
  Activity,
  ArrowUpRight,
  Sparkles,
  Info,
  Check,
  AlertCircle,
  SlidersHorizontal,
} from "lucide-react";
import Layout from "../components/layout/Layout";
import { getAudits } from "../services/automationService";
import { getAuditDataQuality } from "../services/dataQualityService";
import { env } from "../config/env";
import "../styles/data-quality.css";

const API_BASE = env.apiBaseUrl.replace(/\/api\/v1\/?$/, "") + "/";

export default function DataQualityPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [audits, setAudits] = useState([]);
  const [selectedAuditId, setSelectedAuditId] = useState(searchParams.get("audit_id") || "");
  const [qualityData, setQualityData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [activeTab, setActiveTab] = useState("missing_data");

  useEffect(() => {
    loadAuditsList();
  }, []);

  useEffect(() => {
    const paramId = searchParams.get("audit_id");
    if (paramId && paramId !== selectedAuditId) {
      setSelectedAuditId(paramId);
    }
  }, [searchParams]);

  useEffect(() => {
    if (selectedAuditId) {
      loadQualityAssessment(selectedAuditId);
    }
  }, [selectedAuditId]);

  async function loadAuditsList() {
    try {
      const list = await getAudits();
      const safeList = Array.isArray(list) ? list : [];
      setAudits(safeList);
      if (safeList.length > 0 && !selectedAuditId) {
        const firstId = safeList[0].audit_id;
        setSelectedAuditId(firstId);
        setSearchParams({ audit_id: firstId });
      }
    } catch (e) {
      console.error("Failed to load audits from MongoDB:", e);
      setAudits([]);
    }
  }

  async function loadQualityAssessment(id) {
    try {
      setLoading(true);
      setErrorMsg("");
      const data = await getAuditDataQuality(id);
      setQualityData(data);
    } catch (e) {
      console.error("Failed to load data quality assessment:", e);
      setErrorMsg(e.response?.data?.detail || "Failed to load Data Quality Assessment from server.");
      setQualityData(null);
    } finally {
      setLoading(false);
    }
  }

  const handleAuditChange = (e) => {
    const newId = e.target.value;
    setSelectedAuditId(newId);
    setSearchParams({ audit_id: newId });
  };

  // Helper for status colors
  const getStatusColor = (status, score) => {
    if (status === "PASSED" || (score !== null && score >= 85)) return "#10b981";
    if (status === "WARNING" || (score !== null && score >= 60)) return "#f59e0b";
    if (status === "CRITICAL" || (score !== null && score < 60)) return "#f43f5e";
    return "#64748b";
  };

  const getStatusBg = (status, score) => {
    if (status === "PASSED" || (score !== null && score >= 85)) return "rgba(16, 185, 129, 0.12)";
    if (status === "WARNING" || (score !== null && score >= 60)) return "rgba(245, 158, 11, 0.12)";
    if (status === "CRITICAL" || (score !== null && score < 60)) return "rgba(244, 63, 94, 0.12)";
    return "rgba(100, 116, 139, 0.1)";
  };

  // Resolve GridFS stream URL
  const getArtifactUrl = (rawPath) => {
    if (!rawPath) return "";
    if (rawPath.startsWith("http")) return rawPath;
    if (rawPath.startsWith("/")) return `${API_BASE}${rawPath.slice(1)}`;
    return `${API_BASE}${rawPath}`;
  };

  // SVG Gauge calculations
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const overallScoreVal = qualityData?.overall_score ?? 0;
  const strokeDashoffset = circumference - (overallScoreVal / 100) * circumference;

  // Radar Chart helper (6-axis polygon)
  const renderRadarChart = () => {
    if (!qualityData?.dimensions) return null;
    const dims = [
      { key: "completeness", label: "Completeness", val: qualityData.dimensions.completeness?.score || 0 },
      { key: "validity", label: "Validity", val: qualityData.dimensions.validity?.score || 0 },
      { key: "consistency", label: "Consistency", val: qualityData.dimensions.consistency?.score || 0 },
      { key: "relevance", label: "Relevance", val: qualityData.dimensions.relevance?.score || 0 },
      { key: "uniqueness", label: "Uniqueness", val: qualityData.dimensions.uniqueness?.score || 0 },
      { key: "evidence_availability", label: "Evidence", val: qualityData.dimensions.evidence_availability?.score || 0 },
    ];

    const cx = 130;
    const cy = 130;
    const r = 90;
    const numAxes = dims.length;

    // Calculate radar points
    const points = dims.map((d, i) => {
      const angle = (Math.PI * 2 / numAxes) * i - Math.PI / 2;
      const normalizedVal = (d.val / 100) * r;
      const x = cx + normalizedVal * Math.cos(angle);
      const y = cy + normalizedVal * Math.sin(angle);
      return `${x},${y}`;
    }).join(" ");

    // Grid rings
    const rings = [0.25, 0.5, 0.75, 1.0];

    return (
      <svg width="260" height="260" viewBox="0 0 260 260" style={{ overflow: "visible" }}>
        {/* Background Grid Rings */}
        {rings.map((factor, idx) => {
          const ringPoints = dims.map((_, i) => {
            const angle = (Math.PI * 2 / numAxes) * i - Math.PI / 2;
            const x = cx + (r * factor) * Math.cos(angle);
            const y = cy + (r * factor) * Math.sin(angle);
            return `${x},${y}`;
          }).join(" ");
          return (
            <polygon
              key={idx}
              points={ringPoints}
              fill={idx === rings.length - 1 ? "rgba(241, 245, 249, 0.4)" : "none"}
              stroke="#e2e8f0"
              strokeWidth="1"
            />
          );
        })}

        {/* Axis Lines */}
        {dims.map((_, i) => {
          const angle = (Math.PI * 2 / numAxes) * i - Math.PI / 2;
          const x = cx + r * Math.cos(angle);
          const y = cy + r * Math.sin(angle);
          return (
            <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="#cbd5e1" strokeWidth="1" strokeDasharray="2,2" />
          );
        })}

        {/* Data Polygon */}
        <polygon
          points={points}
          fill="rgba(79, 70, 229, 0.25)"
          stroke="#4f46e5"
          strokeWidth="2.5"
          strokeLinejoin="round"
        />

        {/* Data Vertices */}
        {dims.map((d, i) => {
          const angle = (Math.PI * 2 / numAxes) * i - Math.PI / 2;
          const normalizedVal = (d.val / 100) * r;
          const x = cx + normalizedVal * Math.cos(angle);
          const y = cy + normalizedVal * Math.sin(angle);
          const labelX = cx + (r + 18) * Math.cos(angle);
          const labelY = cy + (r + 18) * Math.sin(angle);

          return (
            <g key={i}>
              <circle cx={x} cy={y} r="4" fill="#4f46e5" stroke="#ffffff" strokeWidth="1.5" />
              <text
                x={labelX}
                y={labelY}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize="10"
                fontWeight="700"
                fill="#475569"
              >
                {d.label}
              </text>
            </g>
          );
        })}
      </svg>
    );
  };

  const dimensionsList = qualityData ? [
    {
      key: "completeness",
      title: "Completeness",
      icon: <Layers size={20} color="#4f46e5" />,
      bg: "rgba(79, 70, 229, 0.1)",
      data: qualityData.dimensions.completeness,
    },
    {
      key: "validity",
      title: "Validity",
      icon: <FileCheck2 size={20} color="#0ea5e9" />,
      bg: "rgba(14, 165, 233, 0.1)",
      data: qualityData.dimensions.validity,
    },
    {
      key: "consistency",
      title: "Consistency",
      icon: <ShieldCheck size={20} color="#10b981" />,
      bg: "rgba(16, 185, 129, 0.1)",
      data: qualityData.dimensions.consistency,
    },
    {
      key: "relevance",
      title: "Relevance (Detector Input Readiness)",
      icon: <Search size={20} color="#f59e0b" />,
      bg: "rgba(245, 158, 11, 0.1)",
      data: qualityData.dimensions.relevance,
    },
    {
      key: "uniqueness",
      title: "Uniqueness",
      icon: <CopyCheck size={20} color="#8b5cf6" />,
      bg: "rgba(139, 92, 246, 0.1)",
      data: qualityData.dimensions.uniqueness,
    },
    {
      key: "evidence_availability",
      title: "Evidence Availability",
      icon: <Camera size={20} color="#ec4899" />,
      bg: "rgba(236, 72, 153, 0.1)",
      data: qualityData.dimensions.evidence_availability,
    },
  ] : [];

  return (
    <Layout>
      <div className="dq-container">
        {/* Header and Audit Selector */}
        <div className="dq-header-card">
          <div className="dq-header-top">
            <div className="dq-title-group">
              <h1>
                <ShieldCheck size={28} color="var(--primary)" />
                Data Quality Assessment
              </h1>
              <p>
                Evaluate dataset completeness, validity, consistency, and evidence traceability before interpreting dark-pattern findings.
              </p>
            </div>

            <div className="dq-selector-wrapper">
              <label>Select Audit Session (MongoDB)</label>
              <select
                value={selectedAuditId}
                onChange={handleAuditChange}
                className="dq-select-input"
              >
                {audits.length === 0 && <option value="">No completed audits found</option>}
                {audits.map((a) => (
                  <option key={a.audit_id} value={a.audit_id}>
                    {a.platform} - {a.start_time} ({a.pages_crawled} pages)
                  </option>
                ))}
              </select>
            </div>
          </div>

          {qualityData && (
            <div className="dq-meta-strip">
              <span className="dq-meta-chip primary">
                <Globe size={14} /> Platform: <strong>{qualityData.platform}</strong>
              </span>
              <span className="dq-meta-chip">
                ID: <code>{qualityData.audit_id}</code>
              </span>
              <span className="dq-meta-chip">
                Target URL: <strong>{qualityData.start_url || "N/A"}</strong>
              </span>
              <span className="dq-meta-chip">
                Timestamp: <strong>{qualityData.start_time}</strong>
              </span>
              <span className="dq-meta-chip">
                Crawl Depth: <strong>{qualityData.configured_crawl_depth} (Reached {qualityData.actual_max_depth_reached})</strong>
              </span>
            </div>
          )}
        </div>

        {loading ? (
          <div className="dq-state-card">
            <div className="dq-spinner" />
            <h3>Analyzing Audit Data Quality from MongoDB...</h3>
            <p style={{ color: "#64748b", fontSize: "14px" }}>
              Evaluating structural completeness, validating data formats, checking relational consistency, and measuring evidence traceability.
            </p>
          </div>
        ) : errorMsg ? (
          <div className="dq-state-card">
            <XCircle size={48} color="#f43f5e" />
            <h3>Unable to Load Assessment</h3>
            <p style={{ color: "#64748b", maxWidth: "500px" }}>{errorMsg}</p>
          </div>
        ) : !qualityData ? (
          <div className="dq-state-card">
            <HelpCircle size={48} color="#94a3b8" />
            <h3>No Audit Selected</h3>
            <p style={{ color: "#64748b" }}>Please select a completed audit session to view its Data Quality Assessment.</p>
          </div>
        ) : (
          <>
            {/* Overall Quality Summary Banner */}
            <div className="dq-summary-banner">
              {/* Radial Gauge */}
              <div className="dq-score-gauge-card">
                <div style={{ position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <svg className="dq-score-circle-svg">
                    <circle
                      className="dq-score-circle-bg"
                      cx="70"
                      cy="70"
                      r={radius}
                    />
                    <circle
                      className="dq-score-circle-val"
                      cx="70"
                      cy="70"
                      r={radius}
                      stroke={getStatusColor(qualityData.overall_status, qualityData.overall_score)}
                      strokeDasharray={circumference}
                      strokeDashoffset={qualityData.overall_score !== null ? strokeDashoffset : circumference}
                    />
                  </svg>
                  <div className="dq-score-center-text">
                    <div
                      className="dq-score-number"
                      style={{ color: getStatusColor(qualityData.overall_status, qualityData.overall_score) }}
                    >
                      {qualityData.overall_score !== null ? `${qualityData.overall_score}%` : "N/A"}
                    </div>
                    <div className="dq-score-label">Data Quality</div>
                  </div>
                </div>

                <div
                  className={`dq-grade-badge ${qualityData.overall_status.toLowerCase()}`}
                  style={{ marginTop: "14px" }}
                >
                  <Sparkles size={14} />
                  Grade: {qualityData.quality_grade}
                </div>
              </div>

              {/* Summary Info */}
              <div className="dq-summary-info">
                <div>
                  <h2 style={{ margin: "0 0 6px 0", fontSize: "20px" }}>
                    Overall Audit Usability Assessment
                  </h2>
                  <p className="dq-summary-text">{qualityData.summary_text}</p>
                </div>

                <div className="dq-summary-metrics-grid">
                  <div className="dq-summary-metric-box">
                    <div className="label">Total Pages</div>
                    <div className="val">{qualityData.details.completeness.total_pages}</div>
                  </div>
                  <div className="dq-summary-metric-box">
                    <div className="label">Successful Pages</div>
                    <div className="val" style={{ color: "#16a34a" }}>
                      {qualityData.details.completeness.successful_pages}
                    </div>
                  </div>
                  <div className="dq-summary-metric-box">
                    <div className="label">Failed Pages</div>
                    <div className="val" style={{ color: qualityData.details.completeness.failed_pages > 0 ? "#dc2626" : "#64748b" }}>
                      {qualityData.details.completeness.failed_pages}
                    </div>
                  </div>
                  <div className="dq-summary-metric-box">
                    <div className="label">Evidence Items</div>
                    <div className="val" style={{ color: "#2563eb" }}>
                      {qualityData.details.evidence_availability.total_evidence_items}
                    </div>
                  </div>
                  <div className="dq-summary-metric-box">
                    <div className="label">Validation Issues</div>
                    <div className="val" style={{ color: qualityData.details.validity.invalid_records > 0 ? "#d97706" : "#16a34a" }}>
                      {qualityData.details.validity.invalid_records}
                    </div>
                  </div>
                </div>

                <div className="dq-methodology-note">
                  <strong>Transparent Methodology: </strong>
                  {qualityData.methodology}
                </div>
              </div>
            </div>

            {/* 6 Dimensions Quality Cards */}
            <div className="dq-dimensions-section">
              <div className="dq-section-heading">
                <span>Core Quality Dimensions</span>
                <span style={{ fontSize: "13px", fontWeight: 500, color: "#64748b" }}>
                  6 Independent Dimensions Evaluated
                </span>
              </div>

              <div className="dq-cards-grid">
                {dimensionsList.map((dim) => {
                  const score = dim.data?.score;
                  const status = dim.data?.status || "INSUFFICIENT_DATA";
                  const pass = dim.data?.passed_checks ?? 0;
                  const fail = dim.data?.failed_checks ?? 0;
                  const color = getStatusColor(status, score);

                  return (
                    <div key={dim.key} className="dq-dimension-card">
                      <div className="dq-card-header">
                        <div className="dq-card-title-group">
                          <div className="dq-card-icon" style={{ background: dim.bg }}>
                            {dim.icon}
                          </div>
                          <div>
                            <h3>{dim.title}</h3>
                            <span
                              style={{
                                fontSize: "11px",
                                fontWeight: 700,
                                padding: "2px 8px",
                                borderRadius: "10px",
                                background: getStatusBg(status, score),
                                color: color,
                                display: "inline-block",
                                marginTop: "2px",
                              }}
                            >
                              {status}
                            </span>
                          </div>
                        </div>

                        <div className="dq-card-score-badge" style={{ color }}>
                          {score !== null ? `${score}%` : "N/A"}
                        </div>
                      </div>

                      <div className="dq-card-progress-bar">
                        <div
                          className="dq-card-progress-fill"
                          style={{
                            width: `${score !== null ? score : 0}%`,
                            background: color,
                          }}
                        />
                      </div>

                      <div className="dq-card-body">
                        {dim.data?.summary || "No dimension summary available."}
                      </div>

                      <div className="dq-card-stats">
                        <span className="dq-stat-pass">
                          <CheckCircle2 size={14} /> {pass} Passed
                        </span>
                        <span className="dq-stat-fail">
                          <AlertTriangle size={14} /> {fail} Flagged
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Visualization & Dimension Comparison */}
            <div className="dq-visualizer-card">
              <div className="dq-section-heading">
                <span>Dimensional Quality Profile & Comparison</span>
                <span style={{ fontSize: "13px", fontWeight: 500, color: "#64748b" }}>
                  Multivariate Quality Balance
                </span>
              </div>

              <div className="dq-vis-grid">
                {/* 6-Axis Radar Chart */}
                <div className="dq-radar-container">
                  {renderRadarChart()}
                </div>

                {/* Horizontal Dimension Comparison Bars */}
                <div className="dq-bar-comparison-list">
                  {dimensionsList.map((dim) => {
                    const score = dim.data?.score;
                    const color = getStatusColor(dim.data?.status, score);
                    return (
                      <div key={dim.key} className="dq-bar-item">
                        <div className="dq-bar-label-row">
                          <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                            {dim.title}
                          </span>
                          <span style={{ color, fontWeight: 700 }}>
                            {score !== null ? `${score}%` : "Insufficient Data"}
                          </span>
                        </div>
                        <div className="dq-card-progress-bar" style={{ height: "10px" }}>
                          <div
                            className="dq-card-progress-fill"
                            style={{
                              width: `${score !== null ? score : 0}%`,
                              background: color,
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Detection Readiness & Evidence Sufficiency Section */}
            <div className="dq-prs-section">
              <div className="dq-section-heading">
                <span>Detection Readiness & Evidence Sufficiency</span>
                <span style={{ fontSize: "13px", fontWeight: 500, color: "#64748b" }}>
                  8 Dark Patterns Evaluated
                </span>
              </div>

              {/* Conceptual Distinction Framework Banner */}
              <div className="dq-framework-banner">
                <div className="dq-framework-title">
                  <Info size={16} />
                  <span>Auditing Methodology & Conceptual Framework</span>
                </div>
                <div className="dq-framework-pillars">
                  <div className="dq-framework-pillar">
                    <span className="pillar-tag dq">1. Data Quality</span>
                    <p>Measures the integrity, completeness, validity, and artifact storage health of crawled data.</p>
                  </div>
                  <div className="dq-framework-pillar">
                    <span className="pillar-tag dir">2. Detector Input Readiness</span>
                    <p>Measures whether required DOM structures, pricing, or forms were captured for the detector to execute.</p>
                  </div>
                  <div className="dq-framework-pillar">
                    <span className="pillar-tag res">3. Detection Outcome & Evidence</span>
                    <p>Compliance determination (DETECTED, NOT DETECTED, INSUFFICIENT EVIDENCE) backed by traceable proof.</p>
                  </div>
                </div>
                <div style={{ fontSize: "12px", color: "#475569", lineHeight: "1.45", borderTop: "1px solid rgba(99, 102, 241, 0.15)", paddingTop: "8px" }}>
                  <strong>Important Distinction: </strong>
                  Data Quality measures the integrity and usability of collected audit data. Detector Input Readiness measures whether each detector received sufficient structured input. Detection Result and Evidence Sufficiency are determined independently from the detector outputs and traceable evidence.
                </div>
              </div>

              {/* 7 Pattern Cards Grid */}
              <div className="dq-prs-grid">
                {(qualityData.details.pattern_readiness_and_sufficiency || []).map((item) => {
                  const detReadiness = qualityData.details.relevance?.detectors_readiness?.find(
                    (d) => d.detector_name.toLowerCase() === item.pattern.toLowerCase()
                  );

                  const isDetected = item.detection_status === "DETECTED" || item.detected;
                  const isNotDetected = item.detection_status === "NOT_DETECTED";
                  const isInsufficient = item.detection_status === "INSUFFICIENT_EVIDENCE";

                  return (
                    <div key={item.pattern} className="dq-prs-card">
                      <div className="dq-prs-card-header">
                        <div className="dq-prs-pattern-title">
                          <Activity size={18} color="var(--primary)" />
                          <span>{item.pattern}</span>
                        </div>
                      </div>

                      {/* Status Badges Row */}
                      <div className="dq-prs-pills-row">
                        {/* Input Readiness */}
                        <span className={`dq-status-chip ${item.input_ready ? "input-ready" : "input-incomplete"}`}>
                          {item.input_ready ? <CheckCircle2 size={12} /> : <AlertTriangle size={12} />}
                          Input: {item.input_ready ? "Ready" : "Incomplete"}
                        </span>

                        {/* Detection Status */}
                        <span
                          className={`dq-status-chip ${
                            isDetected
                              ? "detected"
                              : isNotDetected
                              ? "not-detected"
                              : isInsufficient
                              ? "insufficient"
                              : "not-evaluated"
                          }`}
                        >
                          {isDetected ? (
                            <AlertTriangle size={12} />
                          ) : isNotDetected ? (
                            <CheckCircle2 size={12} />
                          ) : isInsufficient ? (
                            <HelpCircle size={12} />
                          ) : (
                            <HelpCircle size={12} />
                          )}
                          Result: {item.detection_status.replace(/_/g, " ")}
                        </span>

                        {/* Evidence Sufficiency */}
                        <span
                          className={`dq-status-chip ${
                            item.evidence_sufficient ? "evidence-sufficient" : "evidence-insufficient"
                          }`}
                        >
                          {item.evidence_sufficient ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
                          Evidence: {item.evidence_sufficient ? "Sufficient" : "Insufficient"}
                        </span>
                      </div>

                      {/* Metrics Summary Strip */}
                      <div className="dq-prs-meta-grid">
                        <div className="dq-prs-meta-item">
                          <span className="meta-label">Affected Pages</span>
                          <span className="meta-val" style={{ color: item.affected_pages_count > 0 ? "#d97706" : "#64748b" }}>
                            {item.affected_pages_count} page{item.affected_pages_count === 1 ? "" : "s"}
                          </span>
                        </div>
                        <div className="dq-prs-meta-item">
                          <span className="meta-label">Evidence Instances</span>
                          <span className="meta-val" style={{ color: item.evidence_instances_count > 0 ? "#2563eb" : "#64748b" }}>
                            {item.evidence_instances_count} instance{item.evidence_instances_count === 1 ? "" : "s"}
                          </span>
                        </div>
                      </div>

                      {/* Actual Persisted Explanation */}
                      <div className="dq-prs-explanation-box">
                        <strong>Evaluation Rationale: </strong>
                        {item.explanation || "No explanation provided for this pattern."}
                      </div>

                      {/* Input Feature Signals */}
                      {detReadiness && (
                        <div className="dq-feature-tags-list">
                          {detReadiness.available_features.map((feat) => (
                            <span key={feat} className="dq-feature-tag available">
                              ✓ {feat.replace(/_/g, " ")}
                            </span>
                          ))}
                          {detReadiness.missing_features.map((feat) => (
                            <span key={feat} className="dq-feature-tag missing">
                              ✗ {feat.replace(/_/g, " ")}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Detailed Drilldown Tabs & Tables */}
            <div className="dq-visualizer-card">
              <div className="dq-tabs-nav">
                <button
                  className={`dq-tab-button ${activeTab === "missing_data" ? "active" : ""}`}
                  onClick={() => setActiveTab("missing_data")}
                >
                  <Layers size={16} />
                  Missing & Failed Data
                  <span className="dq-tab-badge">
                    {qualityData.details.completeness.missing_fields.length}
                  </span>
                </button>

                <button
                  className={`dq-tab-button ${activeTab === "validation_issues" ? "active" : ""}`}
                  onClick={() => setActiveTab("validation_issues")}
                >
                  <FileCheck2 size={16} />
                  Validation Issues
                  <span className="dq-tab-badge">
                    {qualityData.details.validity.validation_issues.length}
                  </span>
                </button>

                <button
                  className={`dq-tab-button ${activeTab === "consistency_checks" ? "active" : ""}`}
                  onClick={() => setActiveTab("consistency_checks")}
                >
                  <ShieldCheck size={16} />
                  Consistency Checks
                  <span className="dq-tab-badge">
                    {qualityData.details.consistency.consistency_issues.length}
                  </span>
                </button>

                <button
                  className={`dq-tab-button ${activeTab === "duplicates" ? "active" : ""}`}
                  onClick={() => setActiveTab("duplicates")}
                >
                  <CopyCheck size={16} />
                  Duplicates & Redundancy
                  <span className="dq-tab-badge">
                    {qualityData.details.uniqueness.duplicates.length}
                  </span>
                </button>

                <button
                  className={`dq-tab-button ${activeTab === "evidence_traceability" ? "active" : ""}`}
                  onClick={() => setActiveTab("evidence_traceability")}
                >
                  <Camera size={16} />
                  Evidence Coverage & Traceability
                </button>
              </div>

              <div className="dq-tab-content-panel">
                {/* TAB 1: Missing Data */}
                {activeTab === "missing_data" && (
                  <div>
                    {qualityData.details.completeness.missing_fields.length === 0 ? (
                      <div style={{ textAlign: "center", padding: "30px", color: "#16a34a" }}>
                        <CheckCircle2 size={36} style={{ marginBottom: "8px" }} />
                        <p><strong>No Missing Fields Detected.</strong> All crawled pages contain complete structural artifacts and metadata.</p>
                      </div>
                    ) : (
                      <div className="dq-table-container">
                        <table className="dq-table">
                          <thead>
                            <tr>
                              <th>Scope / Page</th>
                              <th>Page URL</th>
                              <th>Status</th>
                              <th>Missing Artifacts / Elements</th>
                            </tr>
                          </thead>
                          <tbody>
                            {qualityData.details.completeness.missing_fields.map((item, idx) => (
                              <tr key={idx}>
                                <td>
                                  {item.page_index !== undefined ? (
                                    <span style={{ fontWeight: 700 }}>Page #{item.page_index + 1}</span>
                                  ) : (
                                    <span style={{ fontWeight: 700 }}>Audit Level</span>
                                  )}
                                </td>
                                <td style={{ maxWidth: "300px", wordBreak: "break-all" }}>
                                  {item.url || "N/A"}
                                </td>
                                <td>
                                  <span className={`dq-pill ${item.status === "success" ? "pass" : "fail"}`}>
                                    {item.status || "N/A"}
                                  </span>
                                </td>
                                <td>
                                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                                    {(item.missing || [item.field]).map((m, mIdx) => (
                                      <span
                                        key={mIdx}
                                        style={{
                                          background: "#fee2e2",
                                          color: "#991b1b",
                                          padding: "2px 6px",
                                          borderRadius: "4px",
                                          fontSize: "11px",
                                          fontWeight: 600,
                                        }}
                                      >
                                        {m}
                                      </span>
                                    ))}
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}

                {/* TAB 2: Validation Issues */}
                {activeTab === "validation_issues" && (
                  <div>
                    {qualityData.details.validity.validation_issues.length === 0 ? (
                      <div style={{ textAlign: "center", padding: "30px", color: "#16a34a" }}>
                        <CheckCircle2 size={36} style={{ marginBottom: "8px" }} />
                        <p><strong>100% Value Validity.</strong> All URLs, timestamps, selectors, and price strings conform to expected formats.</p>
                      </div>
                    ) : (
                      <div className="dq-table-container">
                        <table className="dq-table">
                          <thead>
                            <tr>
                              <th>Category</th>
                              <th>Target Field</th>
                              <th>Issue Description</th>
                              <th>Offending Value</th>
                              <th>Severity</th>
                            </tr>
                          </thead>
                          <tbody>
                            {qualityData.details.validity.validation_issues.map((issue, idx) => (
                              <tr key={idx}>
                                <td>
                                  <span style={{ textTransform: "capitalize", fontWeight: 600 }}>
                                    {issue.category}
                                  </span>
                                </td>
                                <td><code>{issue.target}</code></td>
                                <td>{issue.issue}</td>
                                <td style={{ maxWidth: "240px", wordBreak: "break-all", color: "#64748b" }}>
                                  {issue.value || "None"}
                                </td>
                                <td>
                                  <span className={`dq-pill ${issue.severity === "error" ? "fail" : "warn"}`}>
                                    {issue.severity}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}

                {/* TAB 3: Consistency Checks */}
                {activeTab === "consistency_checks" && (
                  <div className="dq-table-container">
                    <table className="dq-table">
                      <thead>
                        <tr>
                          <th>Integrity Check</th>
                          <th>Status</th>
                          <th>Expected Value</th>
                          <th>Actual Value</th>
                          <th>Verification Description</th>
                        </tr>
                      </thead>
                      <tbody>
                        {qualityData.details.consistency.consistency_issues.map((chk, idx) => (
                          <tr key={idx}>
                            <td style={{ fontWeight: 700 }}>{chk.check_name}</td>
                            <td>
                              <span className={`dq-pill ${chk.status === "PASSED" ? "pass" : "fail"}`}>
                                {chk.status}
                              </span>
                            </td>
                            <td><code>{String(chk.expected)}</code></td>
                            <td><code>{String(chk.actual)}</code></td>
                            <td style={{ color: "#475569" }}>{chk.description}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* TAB 4: Duplicates & Redundancy */}
                {activeTab === "duplicates" && (
                  <div>
                    {qualityData.details.uniqueness.duplicates.length === 0 ? (
                      <div style={{ textAlign: "center", padding: "30px", color: "#16a34a" }}>
                        <CheckCircle2 size={36} style={{ marginBottom: "8px" }} />
                        <p><strong>Zero Duplicate Items.</strong> All crawled URLs, page titles, and evidence elements are unique.</p>
                      </div>
                    ) : (
                      <div className="dq-table-container">
                        <table className="dq-table">
                          <thead>
                            <tr>
                              <th>Duplicate Type</th>
                              <th>Identifier / Subject</th>
                              <th>Occurrences</th>
                              <th>Context & Impact</th>
                            </tr>
                          </thead>
                          <tbody>
                            {qualityData.details.uniqueness.duplicates.map((dup, idx) => (
                              <tr key={idx}>
                                <td>
                                  <span className="dq-pill warn">
                                    {dup.duplicate_type.replace(/_/g, " ")}
                                  </span>
                                </td>
                                <td style={{ maxWidth: "280px", wordBreak: "break-all", fontWeight: 600 }}>
                                  {dup.identifier}
                                </td>
                                <td>
                                  <strong style={{ color: "#d97706" }}>{dup.count}x</strong>
                                </td>
                                <td style={{ color: "#475569" }}>{dup.context}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}

                {/* TAB 5: Evidence Coverage & Traceability */}
                {activeTab === "evidence_traceability" && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px" }}>
                      <div className="dq-summary-metric-box">
                        <div className="label">Pages Crawled</div>
                        <div className="val">{qualityData.details.evidence_availability.pages_crawled}</div>
                      </div>
                      <div className="dq-summary-metric-box">
                        <div className="label">Screenshots in GridFS</div>
                        <div className="val" style={{ color: "#0891b2" }}>
                          {qualityData.details.evidence_availability.pages_with_screenshots}
                        </div>
                      </div>
                      <div className="dq-summary-metric-box">
                        <div className="label">DOM Records in GridFS</div>
                        <div className="val" style={{ color: "#059669" }}>
                          {qualityData.details.evidence_availability.pages_with_dom}
                        </div>
                      </div>
                      <div className="dq-summary-metric-box">
                        <div className="label">Extracted JSON Records</div>
                        <div className="val" style={{ color: "#4f46e5" }}>
                          {qualityData.details.evidence_availability.pages_with_extracted_json}
                        </div>
                      </div>
                      <div className="dq-summary-metric-box">
                        <div className="label">Traceable Findings</div>
                        <div className="val" style={{ color: "#16a34a" }}>
                          {qualityData.details.evidence_availability.traceable_detection_findings} / {qualityData.details.evidence_availability.total_detection_findings}
                        </div>
                      </div>
                    </div>

                    <p style={{ fontSize: "13px", color: "#64748b", margin: 0 }}>
                      All evidence artifacts are streamed directly from MongoDB GridFS / storage. Every reported dark pattern instance can be audited and visually verified with surrounding DOM context.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </Layout>
  );
}
