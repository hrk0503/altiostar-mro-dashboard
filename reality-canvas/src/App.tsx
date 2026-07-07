import { useEffect, useState } from "react";
import { CesiumCanvas, type LayerVisibility } from "./components/CesiumCanvas";
import { ControlPanel } from "./components/ControlPanel";
import { LoginGate } from "./components/LoginGate";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { isAuthenticated } from "./lib/auth";
import { loadCzml, loadRelations, loadSceneManifest, loadSites } from "./lib/loadData";
import { computeStats } from "./lib/stats";
import { findScene } from "./lib/geo";
import { checkApiHealth, fetchLiveCzml, getApiConfig, type ApiConfig, type JobRelationResult } from "./lib/api";
import { indexResultsByRelation, type RelationResultMap } from "./lib/results";
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

  const [apiConfig] = useState<ApiConfig | null>(() => getApiConfig());
  const [isLive, setIsLive] = useState(false);
  const [resultsByRelation, setResultsByRelation] = useState<RelationResultMap | null>(null);
  const [showAfter, setShowAfter] = useState(false);

  // ── P4: detect a reachable live API; offline fallback if unset/unreachable ──
  useEffect(() => {
    if (!apiConfig) {
      setIsLive(false);
      return;
    }
    let cancelled = false;
    checkApiHealth(apiConfig).then((ok) => {
      if (!cancelled) setIsLive(ok);
    });
    return () => {
      cancelled = true;
    };
  }, [apiConfig]);

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

    if (isLive && apiConfig) {
      fetchLiveCzml(apiConfig, activeScene.nUes, activeScene.seed)
        .then(setCzml)
        .catch((err) => {
          console.debug("[Canvas] live czml load failed, falling back to offline", err);
          setIsLive(false);
        });
      return;
    }

    loadCzml(activeScene.file)
      .then(setCzml)
      .catch((err) => {
        console.debug("[Canvas] czml load failed", err);
        setError(true);
      });
  }, [activeScene, isLive, apiConfig]);

  function handleSceneChange(nUes: number, seed: number) {
    if (isLive) {
      setActiveScene({ nUes, seed, file: "" });
      return;
    }
    const scene = findScene(scenes, nUes, seed);
    if (scene) setActiveScene(scene);
  }

  function handleSimulateResults(results: JobRelationResult[] | null) {
    setResultsByRelation(results ? indexResultsByRelation(results) : null);
    setShowAfter(false);
  }

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
        onSceneChange={handleSceneChange}
        relationsThreshold={relationsThreshold}
        onRelationsThresholdChange={setRelationsThreshold}
        dimBasemap={dimBasemap}
        onDimBasemapChange={setDimBasemap}
        isLive={isLive}
        apiConfig={isLive ? apiConfig : null}
        showAfter={showAfter}
        onShowAfterChange={setShowAfter}
        onSimulateResults={handleSimulateResults}
      />
      <CesiumCanvas
        sites={sites}
        relations={relations}
        czml={czml}
        layers={layers}
        relationsThreshold={relationsThreshold}
        dimBasemap={dimBasemap}
        resultsByRelation={resultsByRelation}
        showAfter={showAfter}
      />
    </main>
  );
}
