import { useEffect, useRef } from "react";
import * as Cesium from "cesium";
import type { RelationRecord, SiteRecord } from "../types";
import { frequencyBandColor, sectorWedgePoints, successRateColor } from "../lib/geo";

export interface LayerVisibility {
  sites: boolean;
  beams: boolean;
  relations: boolean;
  ues: boolean;
  handovers: boolean;
}

interface Props {
  sites: SiteRecord[];
  relations: RelationRecord[];
  czml: unknown[] | null;
  layers: LayerVisibility;
  relationsThreshold: number; // 0..1 — hide relations with successRate above this
  dimBasemap: boolean;
  onReady?: (viewer: Cesium.Viewer) => void;
}

// Extend the DOM Window type for the e2e test hook, without using `any`.
declare global {
  interface Window {
    __viewer?: Cesium.Viewer;
  }
}

export function CesiumCanvas({
  sites,
  relations,
  czml,
  layers,
  relationsThreshold,
  dimBasemap,
  onReady,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<Cesium.Viewer | null>(null);
  const beamsDsRef = useRef<Cesium.CustomDataSource | null>(null);
  const relationsDsRef = useRef<Cesium.CustomDataSource | null>(null);
  const czmlDsRef = useRef<Cesium.CzmlDataSource | null>(null);

  // ── one-time viewer setup ──
  useEffect(() => {
    if (!containerRef.current) return;

    const viewer = new Cesium.Viewer(containerRef.current, {
      baseLayerPicker: false,
      geocoder: false,
      homeButton: true,
      sceneModePicker: false,
      navigationHelpButton: false,
      fullscreenButton: false,
      animation: true,
      timeline: true,
      baseLayer: new Cesium.ImageryLayer(
        new Cesium.OpenStreetMapImageryProvider({ url: "https://tile.openstreetmap.org/" }),
      ),
      terrainProvider: new Cesium.EllipsoidTerrainProvider(),
    });

    const googleKey = import.meta.env.VITE_GOOGLE_3DTILES_KEY;
    if (googleKey) {
      Cesium.Cesium3DTileset.fromUrl(
        `https://tile.googleapis.com/v1/3dtiles/root.json?key=${googleKey}`,
      )
        .then((tileset) => viewer.scene.primitives.add(tileset))
        .catch((err) => console.debug("[CesiumCanvas] 3D tiles unavailable", err));
    }

    const beamsDs = new Cesium.CustomDataSource("beams");
    const relationsDs = new Cesium.CustomDataSource("relations");
    viewer.dataSources.add(beamsDs);
    viewer.dataSources.add(relationsDs);
    beamsDsRef.current = beamsDs;
    relationsDsRef.current = relationsDs;
    viewerRef.current = viewer;

    window.__viewer = viewer;
    onReady?.(viewer);

    return () => {
      viewer.destroy();
      viewerRef.current = null;
      if (window.__viewer === viewer) delete window.__viewer;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── sites + sector beams ──
  useEffect(() => {
    const beamsDs = beamsDsRef.current;
    if (!beamsDs) return;
    beamsDs.entities.removeAll();
    for (const site of sites) {
      const wedge = sectorWedgePoints(site.latitude, site.longitude, site.azimuthDeg, site.beamwidthDeg);
      const color = frequencyBandColor(site.frequencyBand);
      beamsDs.entities.add({
        id: `beam/${site.cellId}`,
        name: site.cellId,
        show: layers.beams,
        polygon: {
          hierarchy: Cesium.Cartesian3.fromDegreesArray(wedge.flat()),
          material: Cesium.Color.fromBytes(color[0], color[1], color[2], color[3]),
          height: 0,
          outline: false,
        },
        properties: { frequencyBand: site.frequencyBand },
      });
    }
  }, [sites, layers.beams]);

  useEffect(() => {
    const czmlDs = czmlDsRef.current;
    // toggle site points/labels loaded via the CZML itself
    if (czmlDs) {
      for (const entity of czmlDs.entities.values) {
        if (entity.id?.startsWith("site/")) entity.show = layers.sites;
      }
    }
  }, [layers.sites]);

  // ── relations layer ──
  useEffect(() => {
    const relationsDs = relationsDsRef.current;
    if (!relationsDs) return;
    relationsDs.entities.removeAll();
    for (const rel of relations) {
      if (rel.successRate > relationsThreshold) continue;
      const color = successRateColor(rel.successRate);
      relationsDs.entities.add({
        id: `relation/${rel.servingCell}->${rel.neighborCell}`,
        show: layers.relations,
        polyline: {
          positions: Cesium.Cartesian3.fromDegreesArray([
            rel.servingLon,
            rel.servingLat,
            rel.neighborLon,
            rel.neighborLat,
          ]),
          width: 2,
          material: Cesium.Color.fromBytes(color[0], color[1], color[2], color[3]),
        },
        properties: { successRate: rel.successRate },
      });
    }
  }, [relations, relationsThreshold, layers.relations]);

  // ── CZML scene (UEs + handovers) ──
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || !czml) return;
    let cancelled = false;

    (async () => {
      if (czmlDsRef.current) {
        viewer.dataSources.remove(czmlDsRef.current, true);
        czmlDsRef.current = null;
      }
      const ds = await Cesium.CzmlDataSource.load(czml);
      if (cancelled) return;
      viewer.dataSources.add(ds);
      viewer.clock.currentTime = viewer.clock.startTime.clone();
      czmlDsRef.current = ds;
      applyLayerVisibility(ds, layers);
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [czml]);

  useEffect(() => {
    const ds = czmlDsRef.current;
    if (ds) applyLayerVisibility(ds, layers);
  }, [layers]);

  // ── dim basemap ──
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.imageryLayers.length === 0) return;
    const base = viewer.imageryLayers.get(0);
    base.alpha = dimBasemap ? 0.35 : 1.0;
    base.brightness = dimBasemap ? 0.5 : 1.0;
  }, [dimBasemap]);

  return <div ref={containerRef} style={{ width: "100%", height: "100%" }} data-testid="cesium-container" />;
}

function applyLayerVisibility(ds: Cesium.CzmlDataSource, layers: LayerVisibility): void {
  for (const entity of ds.entities.values) {
    if (entity.id?.startsWith("site/")) entity.show = layers.sites;
    else if (entity.id?.startsWith("ho/")) entity.show = layers.handovers;
    else if (entity.id !== "document") entity.show = layers.ues;
  }
}
