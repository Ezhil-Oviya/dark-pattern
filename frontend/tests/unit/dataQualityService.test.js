import { describe, it, expect, vi } from "vitest";
import { getAuditDataQuality, getAuditsDataQuality, evaluateRawAuditDataQuality } from "../../src/services/dataQualityService";
import { axiosClient } from "../../src/api/axiosClient";

vi.mock("../../src/api/axiosClient", () => ({
  axiosClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("dataQualityService", () => {
  it("fetches audit data quality by id", async () => {
    const mockData = {
      audit_id: "test_audit_1",
      overall_score: 92.5,
      overall_status: "EXCELLENT",
      dimensions: {},
    };
    axiosClient.get.mockResolvedValueOnce({ data: mockData });

    const result = await getAuditDataQuality("test_audit_1");
    expect(axiosClient.get).toHaveBeenCalledWith("/data-quality/audit/test_audit_1");
    expect(result).toEqual(mockData);
  });

  it("fetches list of audit quality summaries", async () => {
    const mockList = [
      { audit_id: "audit_1", overall_score: 88.0 },
      { audit_id: "audit_2", overall_score: 94.0 },
    ];
    axiosClient.get.mockResolvedValueOnce({ data: mockList });

    const result = await getAuditsDataQuality();
    expect(axiosClient.get).toHaveBeenCalledWith("/data-quality/audits");
    expect(result).toEqual(mockList);
  });

  it("evaluates raw audit payload", async () => {
    const rawAudit = { audit_id: "raw_1", pages: [] };
    const mockResponse = { overall_score: null, overall_status: "INSUFFICIENT_DATA" };
    axiosClient.post.mockResolvedValueOnce({ data: mockResponse });

    const result = await evaluateRawAuditDataQuality(rawAudit);
    expect(axiosClient.post).toHaveBeenCalledWith("/data-quality/evaluate-raw", {
      audit: rawAudit,
      evidence_items: [],
    });
    expect(result).toEqual(mockResponse);
  });
});
