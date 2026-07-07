import { afterEach, describe, expect, it, vi } from "vitest";
import { checkApiHealth, fetchJobResult, fetchLiveCzml, getApiConfig, postSimulate } from "./api";

describe("getApiConfig", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("returns null when VITE_API_URL is unset (offline mode)", () => {
    vi.stubEnv("VITE_API_URL", "");
    expect(getApiConfig()).toBeNull();
  });

  it("returns a trimmed config when VITE_API_URL is set", () => {
    vi.stubEnv("VITE_API_URL", "http://localhost:8600/");
    vi.stubEnv("VITE_API_TOKEN", "devtoken");
    expect(getApiConfig()).toEqual({ baseUrl: "http://localhost:8600", token: "devtoken" });
  });

  it("defaults token to empty string when unset", () => {
    vi.stubEnv("VITE_API_URL", "http://localhost:8600");
    vi.stubEnv("VITE_API_TOKEN", "");
    expect(getApiConfig()).toEqual({ baseUrl: "http://localhost:8600", token: "" });
  });
});

describe("checkApiHealth", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns true on 200", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true }));
    const ok = await checkApiHealth({ baseUrl: "http://x", token: "" });
    expect(ok).toBe(true);
  });

  it("returns false on non-ok response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false }));
    const ok = await checkApiHealth({ baseUrl: "http://x", token: "" });
    expect(ok).toBe(false);
  });

  it("returns false (never throws) on network error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));
    const ok = await checkApiHealth({ baseUrl: "http://x", token: "" });
    expect(ok).toBe(false);
  });
});

describe("fetchLiveCzml", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("builds the correct query string and sends the bearer token", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [{ id: "document" }] });
    vi.stubGlobal("fetch", fetchMock);
    const doc = await fetchLiveCzml({ baseUrl: "http://x", token: "tok" }, 100, 42, 240);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://x/api/v1/czml?n_ues=100&seed=42&duration_s=240",
      { headers: { Authorization: "Bearer tok" } },
    );
    expect(doc).toEqual([{ id: "document" }]);
  });

  it("throws on a non-ok response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 422 }));
    await expect(fetchLiveCzml({ baseUrl: "http://x", token: "" }, 100, 42)).rejects.toThrow("422");
  });
});

describe("postSimulate", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts rf_provider and returns the parsed summary", async () => {
    const summary = { job_id: "abc", status: "done", summary: { relations: 5, avg_before: 80, avg_after: 92, banner: "NOT_A_PERFORMANCE_CLAIM" } };
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => summary });
    vi.stubGlobal("fetch", fetchMock);
    const res = await postSimulate({ baseUrl: "http://x", token: "tok" }, "synthetic");
    expect(fetchMock).toHaveBeenCalledWith("http://x/api/v1/simulate", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ rf_provider: "synthetic" }),
    }));
    expect(res).toEqual(summary);
  });

  it("throws on a non-ok response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    await expect(postSimulate({ baseUrl: "http://x", token: "" })).rejects.toThrow("500");
  });
});

describe("fetchJobResult", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches the per-relation result rows", async () => {
    const rows = [{ source_cell: "A", target_cell: "B", current_cio_db: null, before_success_pct: 80, optimal_cio_db: 3, after_success_pct: 92, improvement_pp: 12, source: "counterfactual_sim" }];
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => rows }));
    const result = await fetchJobResult({ baseUrl: "http://x", token: "" }, "job-1");
    expect(result).toEqual(rows);
  });

  it("throws on a non-ok response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 404 }));
    await expect(fetchJobResult({ baseUrl: "http://x", token: "" }, "missing")).rejects.toThrow("404");
  });
});
