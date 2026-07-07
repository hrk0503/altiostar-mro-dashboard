// Live API client for the AltioStar MRO backend (P4).
//
// Offline-first: if VITE_API_URL is unset, getApiConfig() returns null and the
// app MUST fall back to the pre-generated scenes in public/data/ — see
// lib/loadData.ts. This module never throws on "not configured"; it only
// throws on actual network/HTTP failures once a config exists.

export interface ApiConfig {
  baseUrl: string;
  token: string;
}

export interface SimulateSummary {
  relations: number;
  avg_before: number | null;
  avg_after: number | null;
  banner: string;
}

export interface SimulateResponse {
  job_id: string;
  status: string;
  summary: SimulateSummary;
}

export interface JobRelationResult {
  source_cell: string;
  target_cell: string;
  current_cio_db: number | null;
  before_success_pct: number;
  optimal_cio_db: number;
  after_success_pct: number;
  improvement_pp: number;
  source: string;
}

/** Reads VITE_API_URL / VITE_API_TOKEN. Returns null when the API is not configured (offline mode). */
export function getApiConfig(): ApiConfig | null {
  const baseUrl = import.meta.env.VITE_API_URL as string | undefined;
  if (!baseUrl || !baseUrl.trim()) return null;
  const token = (import.meta.env.VITE_API_TOKEN as string | undefined) ?? "";
  return { baseUrl: baseUrl.replace(/\/+$/, ""), token };
}

/** Cheap reachability check against the root health route. Never throws. */
export async function checkApiHealth(config: ApiConfig): Promise<boolean> {
  try {
    const res = await fetch(`${config.baseUrl}/`, { method: "GET" });
    return res.ok;
  } catch (err) {
    console.debug("[api] health check failed", err);
    return false;
  }
}

function authHeaders(config: ApiConfig): HeadersInit {
  return config.token ? { Authorization: `Bearer ${config.token}` } : {};
}

export async function fetchLiveCzml(
  config: ApiConfig,
  nUes: number,
  seed: number,
  durationS = 240,
): Promise<unknown[]> {
  const url = `${config.baseUrl}/api/v1/czml?n_ues=${nUes}&seed=${seed}&duration_s=${durationS}`;
  const res = await fetch(url, { headers: authHeaders(config) });
  if (!res.ok) throw new Error(`czml request failed: ${res.status}`);
  return (await res.json()) as unknown[];
}

export async function postSimulate(
  config: ApiConfig,
  rfProvider = "synthetic",
): Promise<SimulateResponse> {
  const res = await fetch(`${config.baseUrl}/api/v1/simulate`, {
    method: "POST",
    headers: { ...authHeaders(config), "Content-Type": "application/json" },
    body: JSON.stringify({ rf_provider: rfProvider }),
  });
  if (!res.ok) throw new Error(`simulate request failed: ${res.status}`);
  return (await res.json()) as SimulateResponse;
}

export async function fetchJobResult(
  config: ApiConfig,
  jobId: string,
): Promise<JobRelationResult[]> {
  const res = await fetch(`${config.baseUrl}/api/v1/jobs/${jobId}/result`, {
    headers: authHeaders(config),
  });
  if (!res.ok) throw new Error(`job result request failed: ${res.status}`);
  return (await res.json()) as JobRelationResult[];
}
