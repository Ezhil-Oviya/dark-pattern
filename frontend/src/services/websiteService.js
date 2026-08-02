import { axiosClient } from "../api/axiosClient";

const BASE_URL = "/websites";

export const getWebsites = async () => {
  const response = await axiosClient.get(BASE_URL);
  return response.data;
};

export const createWebsite = async (website) => {
  const response = await axiosClient.post(BASE_URL, website);
  return response.data;
};

export const updateWebsite = async (id, website) => {
  const response = await axiosClient.put(`${BASE_URL}/${id}`, website);
  return response.data;
};

export const deleteWebsite = async (id) => {
  const response = await axiosClient.delete(`${BASE_URL}/${id}`);
  return response.data;
};