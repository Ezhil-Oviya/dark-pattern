import React, { useState, useEffect } from "react";
import {
  BrainCircuit,
  Trophy,
  Zap,
  ShieldAlert,
  CheckCircle2,
  BarChart3,
  Scale,
  RefreshCw,
  Cpu,
  Layers,
  AlertTriangle,
  Info,
  Download,
  BookOpen,
  Calendar,
  Database,
  Sliders,
  Check,
  ChevronRight,
  ExternalLink,
  Target,
  FileText,
  Activity,
  Percent,
  Hash
} from "lucide-react";
import Layout from "../components/layout/Layout";
import {
  getAlgorithmOverview,
  getAlgorithmDetails,
  getLiteratureBenchmarks,
  getHistoricalEvaluations,
  triggerNewEvaluation,
  downloadReportCsv,
  downloadReportPdf,
} from "../services/algorithmAnalysisService";
import "../styles/algorithm-comparison.css";

const ALL_EIGHT_CATEGORIES = [
  { id: "False Urgency", label: "False Urgency", icon: "⏰" },
  { id: "Drip Pricing", label: "Drip Pricing", icon: "💧" },
  { id: "Bait and Switch", label: "Bait and Switch", icon: "🎣" },
  { id: "Confirmshaming", label: "Confirmshaming", icon: "🥺" },
  { id: "SaaS Billing", label: "SaaS Billing", icon: "💳" },
  { id: "Interface Interference", label: "Interface Interference", icon: "👁️" },
  { id: "Forced Action", label: "Forced Action (CCPA)", icon: "🚪" },
  { id: "Basket Sneaking", label: "Basket Sneaking", icon: "🛒" },
];

export default function AlgorithmComparisonPage() {
  const [overview, setOverview] = useState(null);
  const [literature, setLiterature] = useState([]);
  const [algorithms, setAlgorithms] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [downloadingFormat, setDownloadingFormat] = useState(null);

  // User Interactive Filters & Tabs
  const [activeCategory, setActiveCategory] = useState("Basket Sneaking");
  const [metricFilter, setMetricFilter] = useState("ALL"); // ALL, ACCURACY, PRECISION, RECALL, F1
  const [cmDisplayMode, setCmDisplayMode] = useState("COUNTS"); // COUNTS or PERCENTAGES
  const [cmCategoryScope, setCmCategoryScope] = useState("OVERALL"); // OVERALL or specific category
  const [litComparabilityFilter, setLitComparabilityFilter] = useState("ALL");
  const [showEvalModal, setShowEvalModal] = useState(false);
  const [evalConfig, setEvalConfig] = useState({ random_seed: 42, test_size: 0.30 });

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    try {
      const [overviewData, litData, algoData, histData] = await Promise.all([
        getAlgorithmOverview(),
        getLiteratureBenchmarks(),
        getAlgorithmDetails(),
        getHistoricalEvaluations(),
      ]);
      setOverview(overviewData);
      setLiterature(litData?.literature_benchmarks || []);
      setAlgorithms(algoData?.algorithms || []);
      setHistory(histData?.evaluations || []);
    } catch (err) {
      console.error("Failed to load algorithm analysis data:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleRunEvaluation = async () => {
    setEvaluating(true);
    setShowEvalModal(false);
    try {
      await triggerNewEvaluation(evalConfig);
      await loadAllData();
    } catch (err) {
      console.error("Failed to run evaluation:", err);
      alert("Evaluation failed to complete: " + (err.response?.data?.detail || err.message));
    } finally {
      setEvaluating(false);
    }
  };

  const handleExport = async (format) => {
    if (!overview?.evaluation_id) return;
    setDownloadingFormat(format);
    try {
      if (format === "csv") {
        await downloadReportCsv(overview.evaluation_id);
      } else {
        await downloadReportPdf(overview.evaluation_id);
      }
    } catch (err) {
      console.error("Failed to download report:", err);
      alert("Export failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setDownloadingFormat(null);
    }
  };

  if (loading && !overview) {
    return (
      <Layout>
        <div className="comparison-page" style={{ alignItems: "center", justifyContent: "center", minHeight: "60vh" }}>
          <RefreshCw size={36} className="animate-spin text-primary" color="#4f46e5" />
          <p style={{ marginTop: "16px", color: "var(--text-secondary)", fontWeight: 600 }}>
            Loading empirical evaluation benchmark and training baselines...
          </p>
        </div>
      </Layout>
    );
  }

  const pMetrics = overview?.metric_cards || {};
  const baselines = overview?.baseline_algorithms || [];
  const catBreakdown = overview?.category_breakdown || {};
  const currentCatData = catBreakdown[activeCategory] || {};
  const stability = overview?.stability_analysis || {};
  const coverage = overview?.coverage_policy || {};

  // Active confusion matrix scope
  const activeCmData = cmCategoryScope === "OVERALL"
    ? pMetrics?.confusion_matrix || {}
    : catBreakdown[cmCategoryScope]?.confusion_matrix || {};

  const activeCmPercentages = cmCategoryScope === "OVERALL"
    ? overview?.proposed_algorithm?.metrics?.confusion_matrix_percentages || {}
    : catBreakdown[cmCategoryScope]?.confusion_matrix_percentages || {};

  // Filtered literature
  const filteredLiterature = literature.filter((item) => {
    if (litComparabilityFilter === "ALL") return true;
    if (litComparabilityFilter === "DIRECT") return item.comparability?.toLowerCase().includes("directly");
    if (litComparabilityFilter === "PARTIAL") return item.comparability?.toLowerCase().includes("partially");
    if (litComparabilityFilter === "CONTEXT") return item.comparability?.toLowerCase().includes("context only");
    return true;
  });

  return (
    <Layout>
      <div className="comparison-page">
        {/* TOP HEADER */}
        <div className="comparison-header">
          <div className="comparison-header-left">
            <h1>
              <BrainCircuit size={32} color="#4f46e5" />
              Algorithm Analysis & Comparative Evaluation
            </h1>
            <p className="comparison-subtitle">
              Rigorous, scientifically defensible evaluation of our proposed multi-modal compliance auditing pipeline
              against reproduced machine learning baselines and verified academic literature across 8 dark-pattern categories.
            </p>
          </div>

          <div className="header-action-buttons">
            <button
              className="action-btn secondary"
              onClick={() => handleExport("csv")}
              disabled={downloadingFormat !== null}
              title="Download structured CSV report"
            >
              <Download size={16} />
              {downloadingFormat === "csv" ? "Exporting CSV..." : "Export CSV"}
            </button>

            <button
              className="action-btn secondary"
              onClick={() => handleExport("pdf")}
              disabled={downloadingFormat !== null}
              title="Download academic PDF report"
            >
              <FileText size={16} />
              {downloadingFormat === "pdf" ? "Exporting PDF..." : "Export PDF Report"}
            </button>

            <button
              className="action-btn primary"
              onClick={() => setShowEvalModal(true)}
              disabled={evaluating}
            >
              <RefreshCw size={16} className={evaluating ? "animate-spin" : ""} />
              {evaluating ? "Evaluating Models..." : "Run New Evaluation"}
            </button>
          </div>
        </div>

        {/* PROVENANCE BAR */}
        <div className="provenance-bar">
          <div className="provenance-left">
            <span className="provenance-badge online">
              <CheckCircle2 size={13} />
              Status: Evaluated
            </span>
            <span className="provenance-item">
              Dataset: <strong>{overview?.dataset_name || "DPCA-ECom-8Cat-Benchmark"}</strong> (v{overview?.dataset_version || "3.0.0"})
            </span>
            <span className="provenance-item" title={overview?.dataset_hash}>
              SHA-256: <code>{overview?.dataset_hash ? `${overview.dataset_hash.slice(0, 12)}...` : "N/A"}</code>
            </span>
            <span className="provenance-item">
              Protocol: <strong>{overview?.split_policy || "Stratified 70/30 (Seed 42)"}</strong>
            </span>
          </div>

          <div className="provenance-right">
            <span className="provenance-item">
              Run ID: <strong>{overview?.evaluation_id || "eval_latest"}</strong>
            </span>
          </div>
        </div>

        {/* SECTION A: MAIN METRIC CARDS (PROPOSED ALGORITHM) */}
        <div>
          <div className="section-title-row">
            <div className="section-title">
              <Target size={22} color="#4f46e5" />
              Our Experimental Results — Proposed Architecture Performance
            </div>
            <span className="section-tag">Tested on Held-Out Split</span>
          </div>

          <div className="metric-cards-grid">
            <div className="hero-metric-card accuracy">
              <div className="metric-card-top">
                <span className="metric-card-label">Overall Accuracy</span>
                <Trophy size={18} color="#4f46e5" />
              </div>
              <div className="metric-card-value">
                {pMetrics.accuracy != null ? `${pMetrics.accuracy}%` : "Not evaluated"}
              </div>
              <div className="metric-card-desc">
                Correct classifications divided by all {pMetrics.support || 0} evaluated test examples.
              </div>
            </div>

            <div className="hero-metric-card precision">
              <div className="metric-card-top">
                <span className="metric-card-label">Precision</span>
                <CheckCircle2 size={18} color="#0ea5e9" />
              </div>
              <div className="metric-card-value">
                {pMetrics.precision != null ? `${pMetrics.precision}%` : "Not evaluated"}
              </div>
              <div className="metric-card-desc">
                True positives divided by all items flagged as dark patterns (minimizes false alarms).
              </div>
            </div>

            <div className="hero-metric-card recall">
              <div className="metric-card-top">
                <span className="metric-card-label">Recall (Detection Rate)</span>
                <Activity size={18} color="#10b981" />
              </div>
              <div className="metric-card-value">
                {pMetrics.recall != null ? `${pMetrics.recall}%` : "Not evaluated"}
              </div>
              <div className="metric-card-desc">
                Positive-Class Recall: Percentage of actual deceptive dark-pattern violations detected.
              </div>
            </div>

            <div className="hero-metric-card f1">
              <div className="metric-card-top">
                <span className="metric-card-label">F1-Score (Harmonic Mean)</span>
                <Scale size={18} color="#8b5cf6" />
              </div>
              <div className="metric-card-value">
                {pMetrics.f1_score != null ? `${pMetrics.f1_score}%` : "Not evaluated"}
              </div>
              <div className="metric-card-desc">
                Balanced harmonic mean of precision and recall; primary metric for imbalanced classes.
              </div>
            </div>
          </div>

          {/* Supporting sample statistics */}
          <div className="supporting-stats-row">
            <div className="supporting-stat-pill">
              <span className="supporting-stat-label">Total Test Samples</span>
              <span className="supporting-stat-val">{pMetrics.support || 0}</span>
              <span className="supporting-stat-note">Held-out test partition</span>
            </div>

            <div className="supporting-stat-pill">
              <span className="supporting-stat-label">Actual Dark Patterns</span>
              <span className="supporting-stat-val" style={{ color: "#e11d48" }}>
                {overview?.positive_test_count ?? "N/A"}
              </span>
              <span className="supporting-stat-note">Positive ground-truth cases</span>
            </div>

            <div className="supporting-stat-pill">
              <span className="supporting-stat-label">Actual Benign UI Cases</span>
              <span className="supporting-stat-val" style={{ color: "#059669" }}>
                {overview?.negative_test_count ?? "N/A"}
              </span>
              <span className="supporting-stat-note">Negative ground-truth cases</span>
            </div>

            <div className="supporting-stat-pill">
              <span className="supporting-stat-label">Predicted Detection Rate</span>
              <span className="supporting-stat-val">
                {pMetrics.predicted_detection_rate != null ? `${pMetrics.predicted_detection_rate}%` : "N/A"}
              </span>
              <span className="supporting-stat-note">Distinct from model accuracy</span>
            </div>

            <div className="supporting-stat-pill">
              <span className="supporting-stat-label">Cross-Validation Stability</span>
              <span className="supporting-stat-val">
                {stability.mean_f1 != null ? `${stability.mean_f1}%` : "N/A"}
              </span>
              <span className="supporting-stat-note">
                {stability.std_f1 != null ? `Std Dev: ±${stability.std_f1}% (5 folds)` : "5-Fold CV"}
              </span>
            </div>

            <div className="supporting-stat-pill">
              <span className="supporting-stat-label">Dataset Coverage Rate</span>
              <span className="supporting-stat-val" style={{ color: "#4f46e5" }}>
                {coverage.coverage_rate_pct != null ? `${coverage.coverage_rate_pct}%` : "100%"}
              </span>
              <span className="supporting-stat-note">
                {coverage.insufficient_evidence_count != null ? `${coverage.insufficient_evidence_count} abstentions tracked` : "Decisive cases"}
              </span>
            </div>
          </div>
        </div>

        {/* SECTION B: ALGORITHM COMPARISON (PROPOSED VS REPRODUCED BASELINES) */}
        <div className="comparison-card">
          <div className="section-title-row">
            <div>
              <div className="section-title">
                <BarChart3 size={22} color="#0ea5e9" />
                Algorithm Comparative Benchmark: Proposed Architecture vs Reproduced Baselines
              </div>
              <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: "4px" }}>
                Fair empirical comparison: All candidate algorithms trained and evaluated on the <strong>identical held-out test split</strong> using scikit-learn.
              </p>
            </div>
            <span className="section-tag baseline">Reproduced Baselines</span>
          </div>

          <div className="benchmark-controls-bar">
            <div className="metric-filter-buttons">
              <span style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--text-muted)", alignSelf: "center", marginRight: "6px" }}>
                Filter Metric:
              </span>
              {["ALL", "ACCURACY", "PRECISION", "RECALL", "F1"].map((m) => (
                <button
                  key={m}
                  className={`filter-btn ${metricFilter === m ? "active" : ""}`}
                  onClick={() => setMetricFilter(m)}
                >
                  {m === "ALL" ? "All Metrics" : m}
                </button>
              ))}
            </div>
          </div>

          <div className="models-comparison-table-wrapper">
            <table className="models-comparison-table">
              <thead>
                <tr>
                  <th>Algorithm Architecture</th>
                  <th>Evaluation Paradigm</th>
                  {(metricFilter === "ALL" || metricFilter === "ACCURACY") && <th>Accuracy</th>}
                  {(metricFilter === "ALL" || metricFilter === "PRECISION") && <th>Precision</th>}
                  {(metricFilter === "ALL" || metricFilter === "RECALL") && <th>Recall (Detection %)</th>}
                  {(metricFilter === "ALL" || metricFilter === "F1") && <th>F1-Score</th>}
                  <th>FP Rate</th>
                  <th>Evaluation Status</th>
                </tr>
              </thead>
              <tbody>
                {/* Proposed model row */}
                <tr className="highlight-proposed">
                  <td>
                    <div className="model-name-cell">
                      <span className="model-main-name" style={{ color: "#4f46e5" }}>
                        ⭐ {overview?.proposed_algorithm_name || "Proposed Multi-Modal Architecture (Ours)"}
                      </span>
                      <span className="model-paradigm-sub">Multi-Modal Cross-Attention + DOM State Gating</span>
                    </div>
                  </td>
                  <td>
                    <span style={{ fontSize: "0.78rem", fontWeight: 600, color: "var(--text-secondary)" }}>
                      Cross-Modal Deep Learning
                    </span>
                  </td>
                  {(metricFilter === "ALL" || metricFilter === "ACCURACY") && (
                    <td className="metric-bar-cell">
                      <div className="metric-score-label">
                        <span>{pMetrics.accuracy != null ? `${pMetrics.accuracy}%` : "N/A"}</span>
                      </div>
                      <div className="mini-bar-track">
                        <div className="mini-bar-fill proposed" style={{ width: `${pMetrics.accuracy || 0}%` }} />
                      </div>
                    </td>
                  )}
                  {(metricFilter === "ALL" || metricFilter === "PRECISION") && (
                    <td className="metric-bar-cell">
                      <div className="metric-score-label">
                        <span>{pMetrics.precision != null ? `${pMetrics.precision}%` : "N/A"}</span>
                      </div>
                      <div className="mini-bar-track">
                        <div className="mini-bar-fill proposed" style={{ width: `${pMetrics.precision || 0}%` }} />
                      </div>
                    </td>
                  )}
                  {(metricFilter === "ALL" || metricFilter === "RECALL") && (
                    <td className="metric-bar-cell">
                      <div className="metric-score-label">
                        <span>{pMetrics.recall != null ? `${pMetrics.recall}%` : "N/A"}</span>
                      </div>
                      <div className="mini-bar-track">
                        <div className="mini-bar-fill proposed" style={{ width: `${pMetrics.recall || 0}%` }} />
                      </div>
                    </td>
                  )}
                  {(metricFilter === "ALL" || metricFilter === "F1") && (
                    <td className="metric-bar-cell">
                      <div className="metric-score-label">
                        <span style={{ color: "#4f46e5", fontWeight: 800 }}>{pMetrics.f1_score != null ? `${pMetrics.f1_score}%` : "N/A"}</span>
                      </div>
                      <div className="mini-bar-track">
                        <div className="mini-bar-fill proposed" style={{ width: `${pMetrics.f1_score || 0}%` }} />
                      </div>
                    </td>
                  )}
                  <td>
                    <span style={{ color: "#059669", fontWeight: 700 }}>
                      {pMetrics.false_positive_rate != null ? `${pMetrics.false_positive_rate}%` : "N/A"}
                    </span>
                  </td>
                  <td>
                    <span className="provenance-badge online">PROPOSED (OURS)</span>
                  </td>
                </tr>

                {/* Baseline rows */}
                {baselines.map((b, idx) => {
                  const bm = b.metrics || {};
                  return (
                    <tr key={idx}>
                      <td>
                        <div className="model-name-cell">
                          <span className="model-main-name">{b.name}</span>
                          <span className="model-paradigm-sub">{b.paradigm}</span>
                        </div>
                      </td>
                      <td>
                        <span style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>
                          {b.paradigm}
                        </span>
                      </td>
                      {(metricFilter === "ALL" || metricFilter === "ACCURACY") && (
                        <td className="metric-bar-cell">
                          <div className="metric-score-label">
                            <span>{bm.accuracy != null ? `${bm.accuracy}%` : "N/A"}</span>
                          </div>
                          <div className="mini-bar-track">
                            <div className="mini-bar-fill baseline" style={{ width: `${bm.accuracy || 0}%` }} />
                          </div>
                        </td>
                      )}
                      {(metricFilter === "ALL" || metricFilter === "PRECISION") && (
                        <td className="metric-bar-cell">
                          <div className="metric-score-label">
                            <span>{bm.precision != null ? `${bm.precision}%` : "N/A"}</span>
                          </div>
                          <div className="mini-bar-track">
                            <div className="mini-bar-fill baseline" style={{ width: `${bm.precision || 0}%` }} />
                          </div>
                        </td>
                      )}
                      {(metricFilter === "ALL" || metricFilter === "RECALL") && (
                        <td className="metric-bar-cell">
                          <div className="metric-score-label">
                            <span>{bm.recall != null ? `${bm.recall}%` : "N/A"}</span>
                          </div>
                          <div className="mini-bar-track">
                            <div className="mini-bar-fill baseline" style={{ width: `${bm.recall || 0}%` }} />
                          </div>
                        </td>
                      )}
                      {(metricFilter === "ALL" || metricFilter === "F1") && (
                        <td className="metric-bar-cell">
                          <div className="metric-score-label">
                            <span style={{ fontWeight: 700 }}>{bm.f1_score != null ? `${bm.f1_score}%` : "N/A"}</span>
                          </div>
                          <div className="mini-bar-track">
                            <div className="mini-bar-fill baseline" style={{ width: `${bm.f1_score || 0}%` }} />
                          </div>
                        </td>
                      )}
                      <td>
                        <span style={{ color: bm.false_positive_rate > 20 ? "#e11d48" : "inherit" }}>
                          {bm.false_positive_rate != null ? `${bm.false_positive_rate}%` : "N/A"}
                        </span>
                      </td>
                      <td>
                        <span className="provenance-badge" style={{ background: "#f1f5f9", color: "#475569" }}>
                          REPRODUCED
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* SECTION C: EIGHT-CATEGORY DETECTION ANALYSIS */}
        <div className="comparison-card">
          <div className="section-title-row">
            <div>
              <div className="section-title">
                <Layers size={22} color="#8b5cf6" />
                Category-Wise Detection Analysis (All 8 Dark-Pattern Categories)
              </div>
              <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: "4px" }}>
                Inspect precision, recall, sample distribution, and ground-truth counts across each individual dark pattern.
              </p>
            </div>
            <span className="section-tag">8-Pattern Taxonomy</span>
          </div>

          {/* 8 Category Tabs */}
          <div className="category-tabs-row">
            {ALL_EIGHT_CATEGORIES.map((cat) => (
              <button
                key={cat.id}
                className={`category-tab-btn ${activeCategory === cat.id ? "active" : ""}`}
                onClick={() => {
                  setActiveCategory(cat.id);
                  setCmCategoryScope(cat.id);
                }}
              >
                <span>{cat.icon}</span>
                <span>{cat.label}</span>
              </button>
            ))}
          </div>

          {/* Selected Category Details Inspector */}
          <div className="category-inspector-card">
            <div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "14px" }}>
                <h3 style={{ fontSize: "1.2rem", fontWeight: 700 }}>{activeCategory}</h3>
                <span className={`provenance-badge ${currentCatData.status === "Evaluated" ? "online" : ""}`}>
                  {currentCatData.status || "Evaluated"}
                </span>
              </div>

              <div className="category-stats-list">
                <div className="category-stat-box">
                  <div className="title">Category Accuracy</div>
                  <div className="val" style={{ color: "#4f46e5" }}>
                    {currentCatData.accuracy != null ? `${currentCatData.accuracy}%` : "N/A"}
                  </div>
                </div>

                <div className="category-stat-box">
                  <div className="title">Precision</div>
                  <div className="val" style={{ color: "#0ea5e9" }}>
                    {currentCatData.precision != null ? `${currentCatData.precision}%` : "N/A"}
                  </div>
                </div>

                <div className="category-stat-box">
                  <div className="title">Recall (Detection Rate)</div>
                  <div className="val" style={{ color: "#10b981" }}>
                    {currentCatData.recall != null ? `${currentCatData.recall}%` : "N/A"}
                  </div>
                </div>

                <div className="category-stat-box">
                  <div className="title">F1-Score</div>
                  <div className="val" style={{ color: "#8b5cf6" }}>
                    {currentCatData.f1_score != null ? `${currentCatData.f1_score}%` : "N/A"}
                  </div>
                </div>

                <div className="category-stat-box">
                  <div className="title">Positive Test Cases</div>
                  <div className="val" style={{ color: "#e11d48" }}>
                    {currentCatData.positive_ground_truth ?? 0}
                  </div>
                </div>

                <div className="category-stat-box">
                  <div className="title">Benign / Clean Cases</div>
                  <div className="val" style={{ color: "#059669" }}>
                    {currentCatData.negative_ground_truth ?? 0}
                  </div>
                </div>
              </div>
            </div>

            {/* Category Confusion Matrix */}
            <div className="confusion-matrix-wrapper">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontWeight: 700, fontSize: "0.9rem" }}>
                  Confusion Matrix ({activeCategory})
                </span>
                <button
                  className="filter-btn"
                  onClick={() => setCmDisplayMode(cmDisplayMode === "COUNTS" ? "PERCENTAGES" : "COUNTS")}
                >
                  Mode: {cmDisplayMode === "COUNTS" ? "Sample Counts" : "Percentages"}
                </button>
              </div>

              <div className="cm-grid-2x2">
                <div className="cm-corner-label">Pred \ Actual</div>
                <div className="cm-col-header">Actual Positive</div>
                <div className="cm-col-header">Actual Negative</div>

                <div className="cm-row-header">Pred Positive</div>
                <div className="cm-cell tp">
                  <span className="cm-cell-count">
                    {cmDisplayMode === "COUNTS"
                      ? (currentCatData.confusion_matrix?.true_positive ?? 0)
                      : `${currentCatData.confusion_matrix_percentages?.true_positive_rate ?? 0}%`}
                  </span>
                  <span className="cm-cell-tag" style={{ color: "#047857" }}>True Positive (TP)</span>
                </div>
                <div className="cm-cell fp">
                  <span className="cm-cell-count">
                    {cmDisplayMode === "COUNTS"
                      ? (currentCatData.confusion_matrix?.false_positive ?? 0)
                      : `${currentCatData.confusion_matrix_percentages?.false_positive_rate ?? 0}%`}
                  </span>
                  <span className="cm-cell-tag" style={{ color: "#b45309" }}>False Positive (FP)</span>
                </div>

                <div className="cm-row-header">Pred Negative</div>
                <div className="cm-cell fn">
                  <span className="cm-cell-count">
                    {cmDisplayMode === "COUNTS"
                      ? (currentCatData.confusion_matrix?.false_negative ?? 0)
                      : `${currentCatData.confusion_matrix_percentages?.false_negative_rate ?? 0}%`}
                  </span>
                  <span className="cm-cell-tag" style={{ color: "#be123c" }}>False Negative (FN)</span>
                </div>
                <div className="cm-cell tn">
                  <span className="cm-cell-count">
                    {cmDisplayMode === "COUNTS"
                      ? (currentCatData.confusion_matrix?.true_negative ?? 0)
                      : `${currentCatData.confusion_matrix_percentages?.true_negative_rate ?? 0}%`}
                  </span>
                  <span className="cm-cell-tag" style={{ color: "#4338ca" }}>True Negative (TN)</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* SECTION D: PUBLISHED LITERATURE COMPARISON (TYPE C) */}
        <div className="comparison-card">
          <div className="section-title-row">
            <div>
              <div className="section-title">
                <BookOpen size={22} color="#b45309" />
                Published Research Benchmarks — Literature Comparison
              </div>
              <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: "4px" }}>
                Literature metrics reported by verified peer-reviewed publications. 
                <strong style={{ color: "#b45309" }}> Academic Note:</strong> Published metrics were measured on disparate corpora and tasks; they provide academic context rather than direct experimental equivalence.
              </p>
            </div>
            <span className="section-tag literature">Literature Context</span>
          </div>

          <div className="benchmark-controls-bar">
            <div className="metric-filter-buttons">
              <span style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--text-muted)", alignSelf: "center", marginRight: "6px" }}>
                Filter Comparability:
              </span>
              {[
                { id: "ALL", label: "All Papers" },
                { id: "DIRECT", label: "Directly Comparable" },
                { id: "PARTIAL", label: "Partially Comparable" },
                { id: "CONTEXT", label: "Literature Context Only" },
              ].map((f) => (
                <button
                  key={f.id}
                  className={`filter-btn ${litComparabilityFilter === f.id ? "active" : ""}`}
                  onClick={() => setLitComparabilityFilter(f.id)}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          <div className="literature-table-wrapper">
            <table className="literature-table">
              <thead>
                <tr>
                  <th>Paper & Publication Citation</th>
                  <th>Algorithm / Model</th>
                  <th>Dataset Evaluated</th>
                  <th>Reported F1</th>
                  <th>Reported Acc</th>
                  <th>Reported Prec / Rec</th>
                  <th>Comparability & Rationale</th>
                </tr>
              </thead>
              <tbody>
                {filteredLiterature.map((lit, idx) => (
                  <tr key={idx}>
                    <td>
                      <div className="lit-title-cell">
                        <span className="lit-paper-title">{lit.title}</span>
                        <span className="lit-authors">{lit.authors} ({lit.year})</span>
                        <span style={{ fontSize: "0.74rem", color: "var(--text-muted)" }}>{lit.venue}</span>
                        {lit.doi && (
                          <a
                            href={lit.url || `https://doi.org/${lit.doi}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="lit-doi-link"
                          >
                            DOI: {lit.doi} <ExternalLink size={11} />
                          </a>
                        )}
                      </div>
                    </td>
                    <td>
                      <span style={{ fontWeight: 600 }}>{lit.algorithm_or_model}</span>
                    </td>
                    <td>
                      <div style={{ fontSize: "0.8rem" }}>
                        <div><strong>{lit.dataset_name}</strong></div>
                        <div style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>{lit.dataset_size}</div>
                      </div>
                    </td>
                    <td>
                      <strong style={{ color: lit.reported_f1 !== "Not reported" ? "#4f46e5" : "inherit" }}>
                        {lit.reported_f1}
                      </strong>
                    </td>
                    <td>{lit.reported_accuracy}</td>
                    <td>
                      <span style={{ fontSize: "0.78rem" }}>
                        P: {lit.reported_precision} / R: {lit.reported_recall}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                        <span className={`comparability-pill ${
                          lit.comparability?.toLowerCase().includes("directly") ? "directly" :
                          lit.comparability?.toLowerCase().includes("partially") ? "partially" : "context"
                        }`}>
                          {lit.comparability}
                        </span>
                        <span style={{ fontSize: "0.72rem", color: "var(--text-secondary)", lineHeight: 1.35 }}>
                          {lit.comparability_reason}
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* SECTION E: ALGORITHM ARCHITECTURAL DETAILS PANEL */}
        <div className="comparison-card">
          <div className="section-title-row">
            <div>
              <div className="section-title">
                <Cpu size={22} color="#10b981" />
                Algorithm Architectures & Implementation Configurations
              </div>
              <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: "4px" }}>
                Verifiable pipeline specifications, input representations, neural modules, and documented limitations.
              </p>
            </div>
            <span className="section-tag">Model Registry</span>
          </div>

          <div className="algorithm-details-grid">
            {algorithms.map((algo) => (
              <div key={algo.id} className="algorithm-detail-card">
                <div className="algorithm-detail-header">
                  <div>
                    <span className="algorithm-detail-name">{algo.name}</span>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "2px" }}>
                      {algo.family}
                    </div>
                  </div>
                  <span className={`provenance-badge ${algo.id.includes("proposed") ? "online" : ""}`}>
                    {algo.status}
                  </span>
                </div>

                <div className="algorithm-field">
                  <strong>Architecture:</strong> {algo.architecture}
                </div>
                <div className="algorithm-field">
                  <strong>Input Features:</strong> {algo.input_features}
                </div>
                <div className="algorithm-field">
                  <strong>Hyperparameters:</strong> {algo.hyperparameters}
                </div>
                <div className="algorithm-field">
                  <strong>Key Strengths:</strong> {algo.key_strengths}
                </div>
                <div className="algorithm-field" style={{ color: "#b45309" }}>
                  <strong>Documented Limitations:</strong> {algo.known_limitations}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* SECTION F: EVALUATION EXPERIMENT HISTORY */}
        {history.length > 0 && (
          <div className="comparison-card">
            <div className="section-title-row">
              <div className="section-title">
                <Calendar size={20} color="#475569" />
                Evaluation Experiment History
              </div>
              <span className="section-tag">Historical Runs</span>
            </div>

            <div className="models-comparison-table-wrapper">
              <table className="models-comparison-table">
                <thead>
                  <tr>
                    <th>Evaluation ID</th>
                    <th>Timestamp</th>
                    <th>Dataset</th>
                    <th>Test Samples</th>
                    <th>F1-Score</th>
                    <th>Accuracy</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((h) => (
                    <tr key={h.evaluation_id}>
                      <td><strong>{h.evaluation_id}</strong></td>
                      <td>{new Date(h.created_at).toLocaleString()}</td>
                      <td>{h.dataset_name} (v{h.dataset_version})</td>
                      <td>{h.test_sample_count}</td>
                      <td><strong style={{ color: "#4f46e5" }}>{h.f1_score}%</strong></td>
                      <td>{h.accuracy}%</td>
                      <td>
                        <div style={{ display: "flex", gap: "6px" }}>
                          <button
                            className="action-btn secondary"
                            style={{ padding: "4px 8px", fontSize: "0.75rem" }}
                            onClick={() => downloadReportCsv(h.evaluation_id)}
                          >
                            CSV
                          </button>
                          <button
                            className="action-btn secondary"
                            style={{ padding: "4px 8px", fontSize: "0.75rem" }}
                            onClick={() => downloadReportPdf(h.evaluation_id)}
                          >
                            PDF
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* EVALUATION CONFIGURATION MODAL */}
        {showEvalModal && (
          <div className="modal-overlay-custom" onClick={() => setShowEvalModal(false)}>
            <div className="modal-content-custom" onClick={(e) => e.stopPropagation()}>
              <h2 style={{ fontSize: "1.3rem", fontWeight: 700, marginBottom: "8px" }}>
                Execute Scientific Evaluation Run
              </h2>
              <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: "20px" }}>
                Re-evaluates the proposed multi-modal model alongside all reproduced baselines on a fresh stratified split of the benchmark dataset.
              </p>

              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div>
                  <label style={{ fontSize: "0.82rem", fontWeight: 600, display: "block", marginBottom: "6px" }}>
                    Random Seed (Leakage Prevention & Reproducibility):
                  </label>
                  <input
                    type="number"
                    value={evalConfig.random_seed}
                    onChange={(e) => setEvalConfig({ ...evalConfig, random_seed: parseInt(e.target.value) || 42 })}
                    style={{ width: "100%", padding: "8px 12px", borderRadius: "8px", border: "1px solid var(--border-color)" }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: "0.82rem", fontWeight: 600, display: "block", marginBottom: "6px" }}>
                    Held-Out Test Split Ratio: {(evalConfig.test_size * 100).toFixed(0)}% (Train: {((1 - evalConfig.test_size) * 100).toFixed(0)}%)
                  </label>
                  <input
                    type="range"
                    min="0.15"
                    max="0.45"
                    step="0.05"
                    value={evalConfig.test_size}
                    onChange={(e) => setEvalConfig({ ...evalConfig, test_size: parseFloat(e.target.value) })}
                    style={{ width: "100%" }}
                  />
                </div>

                <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "12px" }}>
                  <button className="action-btn secondary" onClick={() => setShowEvalModal(false)}>
                    Cancel
                  </button>
                  <button className="action-btn primary" onClick={handleRunEvaluation}>
                    Start Evaluation
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
