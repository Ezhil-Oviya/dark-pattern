import { axiosClient } from "../api/axiosClient";

export const startAudit = async (websiteId) => {
  const response = await axiosClient.post(
    `/automation/start/${websiteId}`
  );
  return response.data;
};

export const getAudits = async () => {
  const response = await axiosClient.get("/automation/audits");
  return response.data;
};

export const getAuditDetails = async (auditId) => {
  const response = await axiosClient.get(`/automation/audit/${auditId}`);
  return response.data;
};

export const getAuditStatus = async (auditId) => {
  const response = await axiosClient.get(`/automation/audit/${auditId}/status`);
  return response.data;
};

export const getActiveSession = async (websiteId) => {
  const response = await axiosClient.get(`/automation/active-session/${websiteId}`);
  return response.data;
};

export const resumeAudit = async (auditId) => {
  const response = await axiosClient.post(`/automation/audit/${auditId}/resume`);
  return response.data;
};