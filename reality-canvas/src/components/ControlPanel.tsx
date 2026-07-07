import type { LayerVisibility } from "./CesiumCanvas";
import type { SceneManifestEntry, Stats } from "../types";
import {
  APP_SUBTITLE,
  APP_TITLE,
  BASEMAP_DIM_LABEL,
  LAYER_BEAMS,
  LAYER_HANDOVERS,
  LAYER_PANEL_TITLE,
  LAYER_RELATIONS,
  LAYER_SITES,
  LAYER_UES,
  RELATIONS_THRESHOLD_LABEL,
  SCENE_PANEL_TITLE,
  SCENE_REGENERATE_NOTE,
  SCENE_SEED_LABEL,
  SCENE_UE_COUNT_LABEL,
  STATS_CELLS,
  STATS_HANDOVERS,
  STATS_RELATIONS,
  STATS_SITES,
  STATS_UES,
} from "../constants";

interface Props {
  stats: Stats;
  layers: LayerVisibility;
  onLayersChange: (layers: LayerVisibility) => void;
  scenes: SceneManifestEntry[];
  activeScene: SceneManifestEntry | undefined;
  onSceneChange: (nUes: number, seed: number) => void;
  relationsThreshold: number;
  onRelationsThresholdChange: (value: number) => void;
  dimBasemap: boolean;
  onDimBasemapChange: (value: boolean) => void;
}

export function ControlPanel({
  stats,
  layers,
  onLayersChange,
  scenes,
  activeScene,
  onSceneChange,
  relationsThreshold,
  onRelationsThresholdChange,
  dimBasemap,
  onDimBasemapChange,
}: Props) {
  const ueCounts = Array.from(new Set(scenes.map((s) => s.nUes))).sort((a, b) => a - b);
  const seeds = scenes.filter((s) => s.nUes === activeScene?.nUes).map((s) => s.seed);

  return (
    <aside
      aria-label={APP_TITLE}
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: 300,
        maxHeight: "100%",
        overflowY: "auto",
        background: "rgba(16, 24, 44, 0.92)",
        borderRight: "1px solid var(--canvas-cyan)",
        padding: 16,
        fontSize: 13,
        zIndex: 10,
      }}
    >
      <h1 style={{ fontSize: 16, margin: "0 0 4px" }}>{APP_TITLE}</h1>
      <p style={{ fontSize: 11, opacity: 0.65, margin: "0 0 16px" }}>{APP_SUBTITLE}</p>

      <section style={{ marginBottom: 16 }} aria-label="stats">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
          <Stat label={STATS_SITES} value={stats.sites} />
          <Stat label={STATS_CELLS} value={stats.cells} />
          <Stat label={STATS_RELATIONS} value={stats.relations} />
          <Stat label={STATS_UES} value={stats.ues} />
          <Stat label={STATS_HANDOVERS} value={stats.handovers} />
        </div>
      </section>

      <section style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 13, margin: "0 0 8px", color: "var(--canvas-cyan)" }}>
          {LAYER_PANEL_TITLE}
        </h2>
        <LayerCheckbox label={LAYER_SITES} checked={layers.sites} onChange={(v) => onLayersChange({ ...layers, sites: v })} />
        <LayerCheckbox label={LAYER_BEAMS} checked={layers.beams} onChange={(v) => onLayersChange({ ...layers, beams: v })} />
        <LayerCheckbox label={LAYER_RELATIONS} checked={layers.relations} onChange={(v) => onLayersChange({ ...layers, relations: v })} />
        <LayerCheckbox label={LAYER_UES} checked={layers.ues} onChange={(v) => onLayersChange({ ...layers, ues: v })} />
        <LayerCheckbox label={LAYER_HANDOVERS} checked={layers.handovers} onChange={(v) => onLayersChange({ ...layers, handovers: v })} />
      </section>

      <section style={{ marginBottom: 16 }}>
        <label htmlFor="relations-threshold">
          {RELATIONS_THRESHOLD_LABEL} {Math.round(relationsThreshold * 100)}%
        </label>
        <input
          id="relations-threshold"
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={relationsThreshold}
          onChange={(e) => onRelationsThresholdChange(Number(e.target.value))}
          style={{ width: "100%" }}
        />
      </section>

      <section style={{ marginBottom: 16 }}>
        <label>
          <input type="checkbox" checked={dimBasemap} onChange={(e) => onDimBasemapChange(e.target.checked)} />{" "}
          {BASEMAP_DIM_LABEL}
        </label>
      </section>

      <section>
        <h2 style={{ fontSize: 13, margin: "0 0 8px", color: "var(--canvas-cyan)" }}>{SCENE_PANEL_TITLE}</h2>
        <label htmlFor="ue-count">{SCENE_UE_COUNT_LABEL}</label>
        <select
          id="ue-count"
          value={activeScene?.nUes ?? ueCounts[0]}
          onChange={(e) => onSceneChange(Number(e.target.value), seeds[0] ?? 42)}
          style={{ width: "100%", marginBottom: 8 }}
        >
          {ueCounts.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>

        <label htmlFor="seed">{SCENE_SEED_LABEL}</label>
        <select
          id="seed"
          value={activeScene?.seed ?? 42}
          onChange={(e) => onSceneChange(activeScene?.nUes ?? ueCounts[0], Number(e.target.value))}
          style={{ width: "100%" }}
        >
          {seeds.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <p style={{ fontSize: 10, opacity: 0.6, marginTop: 8 }}>{SCENE_REGENERATE_NOTE}</p>
      </section>
    </aside>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div style={{ fontSize: 18, fontWeight: 700, color: "var(--canvas-cyan)" }}>{value}</div>
      <div style={{ fontSize: 10, opacity: 0.7 }}>{label}</div>
    </div>
  );
}

function LayerCheckbox({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label style={{ display: "block", marginBottom: 4 }}>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} /> {label}
    </label>
  );
}
