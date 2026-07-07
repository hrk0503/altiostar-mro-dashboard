import { useState } from "react";
import type { ApiConfig, JobRelationResult, SimulateSummary } from "../lib/api";
import { fetchJobResult, postSimulate } from "../lib/api";
import {
  SIMULATE_AVG_LABEL,
  SIMULATE_BUTTON,
  SIMULATE_BUTTON_RUNNING,
  SIMULATE_ERROR,
  SIMULATE_ERROR_OFFLINE,
  SIMULATE_PANEL_TITLE,
  SIMULATE_RELATIONS_LABEL,
  SIMULATE_TOGGLE_AFTER,
  SIMULATE_TOGGLE_BEFORE,
} from "../constants";

interface Props {
  apiConfig: ApiConfig | null;
  showAfter: boolean;
  onShowAfterChange: (v: boolean) => void;
  onResults: (results: JobRelationResult[] | null) => void;
}

type RunState = "idle" | "running" | "error" | "done";

export function SimulatePanel({ apiConfig, showAfter, onShowAfterChange, onResults }: Props) {
  const [state, setState] = useState<RunState>("idle");
  const [summary, setSummary] = useState<SimulateSummary | null>(null);

  async function runSimulation() {
    if (!apiConfig) return;
    setState("running");
    setSummary(null);
    onResults(null);
    try {
      const res = await postSimulate(apiConfig, "synthetic");
      setSummary(res.summary);
      try {
        const results = await fetchJobResult(apiConfig, res.job_id);
        onResults(results);
      } catch (err) {
        console.debug("[SimulatePanel] per-relation result fetch failed", err);
      }
      setState("done");
    } catch (err) {
      console.debug("[SimulatePanel] simulate failed", err);
      setState("error");
    }
  }

  return (
    <section style={{ marginBottom: 16 }} aria-label={SIMULATE_PANEL_TITLE}>
      <h2 style={{ fontSize: 13, margin: "0 0 8px", color: "var(--canvas-cyan)" }}>
        {SIMULATE_PANEL_TITLE}
      </h2>

      {!apiConfig && (
        <p style={{ fontSize: 11, opacity: 0.7 }}>{SIMULATE_ERROR_OFFLINE}</p>
      )}

      {apiConfig && (
        <button
          type="button"
          onClick={runSimulation}
          disabled={state === "running"}
          style={{ width: "100%", padding: "6px 8px" }}
        >
          {state === "running" ? SIMULATE_BUTTON_RUNNING : SIMULATE_BUTTON}
        </button>
      )}

      {state === "running" && (
        <p role="status" style={{ fontSize: 11, opacity: 0.7, marginTop: 8 }}>
          …
        </p>
      )}

      {state === "error" && (
        <p role="alert" style={{ fontSize: 11, color: "#dc3545", marginTop: 8 }}>
          {SIMULATE_ERROR}
        </p>
      )}

      {state === "done" && summary && (
        <div data-testid="simulate-summary" style={{ marginTop: 8, fontSize: 11 }}>
          <div>
            {SIMULATE_RELATIONS_LABEL}: <strong>{summary.relations}</strong>
          </div>
          <div>
            {SIMULATE_AVG_LABEL}: <strong>{summary.avg_before ?? "—"}%</strong> {"->"}{" "}
            <strong>{summary.avg_after ?? "—"}%</strong>
          </div>
          <div
            style={{
              marginTop: 6,
              padding: "4px 6px",
              background: "rgba(255, 176, 32, 0.15)",
              border: "1px solid #ffb020",
              color: "#ffb020",
              fontSize: 10,
            }}
          >
            {summary.banner}
          </div>
          <button
            type="button"
            onClick={() => onShowAfterChange(!showAfter)}
            style={{ width: "100%", marginTop: 8, padding: "4px 8px" }}
          >
            {/* Label = the state a click will switch TO (destination, not current). */}
            {showAfter ? SIMULATE_TOGGLE_BEFORE : SIMULATE_TOGGLE_AFTER}
          </button>
        </div>
      )}
    </section>
  );
}
