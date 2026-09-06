import { axiosClient } from "../api/axiosClient";

/**
 * Retrieves the comprehensive Data Quality Assessment for a specific audit session.
 * @param {string} auditId - The unique audit session identifier
 * @returns {Promise<Object>} The DataQualityAssessmentResponse object
 */
export const getAuditDataQuality = async (auditId) => {
  const response = await axiosClient.get(`/data-quality/audit/${auditId}`);
  return response.data;
};

/**
 * Retrieves high-level data quality summary scores for all available audits in MongoDB.
 * @returns {Promise<Array>} Array of audit quality summaries
 */
export const getAuditsDataQuality = async () => {
  const response = await axiosClient.get("/data-quality/audits");
  return response.data;
};

/**
 * Evaluates raw audit data payload on-demand without prior database persistence.
 * @param {Object} audit - Raw audit dictionary
 * @param {Array} evidenceItems - Optional array of granular evidence items
 * @returns {Promise<Object>}
 */
export const evaluateRawAuditDataQuality = async (audit, evidenceItems = []) => {
  const response = await axiosClient.post("/data-quality/evaluate-raw", {
    audit,
    evidence_items: evidenceItems,
  });
  return response.data;
};
