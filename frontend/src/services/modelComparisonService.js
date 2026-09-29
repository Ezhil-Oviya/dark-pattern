import { axiosClient } from "../api/axiosClient";

/**
 * Retrieves full empirical benchmark comparison across all model paradigms for non-rule-based patterns.
 * @returns {Promise<Object>}
 */
export const getAlgorithmBenchmarks = async () => {
  const response = await axiosClient.get("/model-comparison/benchmarks");
  return response.data;
};

/**
 * Simulates a live multi-model prediction battle on an input sample.
 * @param {Object} battlePayload
 * @returns {Promise<Object>}
 */
export const simulateAlgorithmBattle = async (battlePayload) => {
  const response = await axiosClient.post("/model-comparison/simulate-battle", battlePayload);
  return response.data;
};
