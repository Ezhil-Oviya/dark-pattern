import { axiosClient } from "../api/axiosClient";

/**
 * Retrieves latest empirical evaluation overview, dataset metadata,
 * 4 metric cards, proposed vs reproduced baselines, and category breakdown.
 */
export const getAlgorithmOverview = async () => {
  const response = await axiosClient.get("/algorithm-analysis/overview");
  return response.data;
};

/**
 * Retrieves deep technical architectures, input features, and hyperparameters.
 */
export const getAlgorithmDetails = async () => {
  const response = await axiosClient.get("/algorithm-analysis/algorithms");
  return response.data;
};

/**
 * Retrieves detailed per-category metrics across all 8 dark patterns.
 */
export const getCategoryMetrics = async (evaluationId = null) => {
  const url = evaluationId
    ? `/algorithm-analysis/categories?evaluation_id=${evaluationId}`
    : "/algorithm-analysis/categories";
  const response = await axiosClient.get(url);
  return response.data;
};

/**
 * Retrieves interactive confusion matrix data for overall or specific category.
 */
export const getConfusionMatrixData = async (category = null, evaluationId = null) => {
  const params = new URLSearchParams();
  if (category) params.append("category", category);
  if (evaluationId) params.append("evaluation_id", evaluationId);

  const query = params.toString() ? `?${params.toString()}` : "";
  const response = await axiosClient.get(`/algorithm-analysis/confusion-matrix${query}`);
  return response.data;
};

/**
 * Retrieves verified published academic research benchmarks and citations.
 */
export const getLiteratureBenchmarks = async () => {
  const response = await axiosClient.get("/algorithm-analysis/literature");
  return response.data;
};

/**
 * Lists previous evaluation experiment runs.
 */
export const getHistoricalEvaluations = async () => {
  const response = await axiosClient.get("/algorithm-analysis/evaluations");
  return response.data;
};

/**
 * Triggers a fresh, reproducible scientific evaluation run.
 */
export const triggerNewEvaluation = async (payload = { random_seed: 42, test_size: 0.30 }) => {
  const response = await axiosClient.post("/algorithm-analysis/evaluate", payload);
  return response.data;
};

/**
 * Downloads evaluation report in CSV format.
 */
export const downloadReportCsv = async (evaluationId) => {
  const response = await axiosClient.get(`/algorithm-analysis/evaluations/${evaluationId}/export/csv`, {
    responseType: "blob",
  });
  const blob = new Blob([response.data], { type: "text/csv;charset=utf-8;" });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", `${evaluationId}_report.csv`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

/**
 * Downloads evaluation report in PDF format.
 */
export const downloadReportPdf = async (evaluationId) => {
  const response = await axiosClient.get(`/algorithm-analysis/evaluations/${evaluationId}/export/pdf`, {
    responseType: "blob",
  });
  const blob = new Blob([response.data], { type: "application/pdf" });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", `${evaluationId}_report.pdf`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};
