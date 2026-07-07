import { useEffect, useState } from "react";
import { CesiumCanvas, type LayerVisibility } from "./components/CesiumCanvas";
import { ControlPanel } from "./components/ControlPanel";
import { LoginGate } from "./components/LoginGate";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { isAuthenticated } from "./lib/auth";
import { loadCzml, loadRelations, loadSceneManifest, loadSites } from "./lib/loadData";
import { computeStats } from "./lib/stats";
import { findScene } from "./lib/geo";
import type { RelationRecord, SceneManifestEntry, SiteRecord } from "./types";
import { ERROR_DATA_LOAD } from "./constants";

const DEFAULT_LAYERS: LayerVisibility = {
  sites: true,
  beams: true,
  relations: true,
  ues: true,
  handovers: true,
};

export default function App() {
  const [authed, setAuthed] = useState(isAuthenticated());

  if (!authed) {
    return <LoginGate onSuccess={() => setAuthed(true)} />;
  }

  return (
    <ErrorBoundary>
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <Canvas />
    </ErrorBoundary>
  );
}

function Canvas() {
  const [sites, setSites] = useState<SiteRecord[] | null>(null);
  const [relations, setRelations] = useState<RelationRecord[] | null>(null);
  const [scenes, setScenes] = useState<SceneManifestEntry[]>([]);
  const [activeScene, setActiveScene] = useState<SceneManifestEntry>();
  const [czml, setCzml] = useState<unknown[] | null>(null);
  const [layers, setLayers] = useState<LayerVisibility>(DEFAULT_LAYERS);
  const [relationsThreshold, setRelationsThreshold] = useState(1);
  const [dimBasemap, setDimBasemap] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    Promise.all([loadSites(), loadRelations(), loadSceneManifest()])
      .then(([s, r, manifest]) => {
        setSites(s);
        setRelations(r);
        setScenes(manifest);
        const first = findScene(manifest, 21, 42) ?? manifest[0];
        setActiveScene(first);
      })
      .catch((err) => {
        console.debug("[Canvas] data load failed", err);
        setError(true);
      });
  }, []);

  useEffect(() => {
    if (!activeScene) return;
    loadCzml(activeScene.file)
      .then(setCzml)
      .catch((err) => {
        console.debug("[Canvas] czml load failed", err);
        setError(true);
      });
  }, [activeScene]);

  if (error) {
    return (
      <div role="alert" style={{ padding: 24 }}>
        {ERROR_DATA_LOAD}
      </div>
    );
  }

  if (!sites || !relations) {
    return <div style={{ padding: 24 }}>Loading…</div>;
  }

  const stats = computeStats(sites, relations, (czml as { id: string }[] | null) ?? []);

  return (
    <main id="main" style={{ position: "relative", width: "100vw", height: "100vh" }}>
      <ControlPanel
        stats={stats}
        layers={layers}
        onLayersChange={setLayers}
        scenes={scenes}
        activeScene={activeScene}
        onSceneChange={(nUes, seed) => {
          const scene = findScene(scenes, nUes, seed);
          if (scene) setActiveScene(scene);
        }}
        relationsThreshold={relationsThreshold}
        onRelationsThresholdChange={setRelationsThreshold}
        dimBasemap={dimBasemap}
        onDimBasemapChange={setDimBasemap}
      />
      <CesiumCanvas
        sites={sites}
        relations={relations}
        czml={czml}
        layers={layers}
        relationsThreshold={relationsThreshold}
        dimBasemap={dimBasemap}
      />
    </main>
  );
}
