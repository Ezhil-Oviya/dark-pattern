import { axiosClient } from "../api/axiosClient";

export const startAudit = async (websiteId) => {
  const response = await axiosClient.post(
    `/automation/start/${websiteId}`
  );

  return response.data;
};