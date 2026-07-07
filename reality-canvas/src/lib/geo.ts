import type { SceneManifestEntry } from "../types";

/** RGBA (0-255) color ramp for handover success rate: red(<75%) -> amber -> green(>95%). */
export function successRateColor(rate: number): [number, number, number, number] {
  const pct = Math.max(0, Math.min(1, rate)) * 100;
  if (pct < 75) return [220, 53, 69, 220]; // red
  if (pct < 95) {
    // amber gradient 75-95
    const t = (pct - 75) / 20;
    const r = Math.round(255 - t * (255 - 255));
    const g = Math.round(170 + t * (200 - 170));
    return [r, g, 0, 220];
  }
  return [40, 200, 120, 220]; // green
}

/** Great-circle-ish flat-earth destination point (fine at city scale) for wedge vertices. */
export function destinationPoint(
  lat: number,
  lon: number,
  bearingDeg: number,
  distanceM: number,
): [number, number] {
  const R = 6378137; // WGS84 equatorial radius, m
  const bearing = (bearingDeg * Math.PI) / 180;
  const latRad = (lat * Math.PI) / 180;
  const lonRad = (lon * Math.PI) / 180;

  const angularDist = distanceM / R;
  const newLat = Math.asin(
    Math.sin(latRad) * Math.cos(angularDist) +
      Math.cos(latRad) * Math.sin(angularDist) * Math.cos(bearing),
  );
  const newLon =
    lonRad +
    Math.atan2(
      Math.sin(bearing) * Math.sin(angularDist) * Math.cos(latRad),
      Math.cos(angularDist) - Math.sin(latRad) * Math.sin(newLat),
    );

  return [(newLat * 180) / Math.PI, (newLon * 180) / Math.PI];
}

/**
 * Build a fan of [lon, lat] points for a sector wedge: apex at the site,
 * arc spanning azimuth +/- beamwidth/2, at the given radius.
 */
export function sectorWedgePoints(
  lat: number,
  lon: number,
  azimuthDeg: number,
  beamwidthDeg: number,
  radiusM = 120,
  arcSteps = 12,
): Array<[number, number]> {
  const half = beamwidthDeg / 2;
  const start = azimuthDeg - half;
  const end = azimuthDeg + half;
  const points: Array<[number, number]> = [[lon, lat]];
  for (let i = 0; i <= arcSteps; i++) {
    const bearing = start + ((end - start) * i) / arcSteps;
    const [pLat, pLon] = destinationPoint(lat, lon, bearing, radiusM);
    points.push([pLon, pLat]);
  }
  points.push([lon, lat]);
  return points;
}

/** Frequency band -> stable UI color (band names are free text in the site DB). */
const BAND_COLORS: Record<string, [number, number, number, number]> = {};
const PALETTE: Array<[number, number, number, number]> = [
  [34, 193, 214, 90],
  [255, 176, 32, 90],
  [199, 125, 255, 90],
  [96, 165, 250, 90],
  [244, 114, 182, 90],
];
export function frequencyBandColor(band: string): [number, number, number, number] {
  if (!(band in BAND_COLORS)) {
    const idx = Object.keys(BAND_COLORS).length % PALETTE.length;
    BAND_COLORS[band] = PALETTE[idx];
  }
  return BAND_COLORS[band];
}

/** Find the manifest entry matching a requested UE count + seed (falls back to seed-42 variant). */
export function findScene(
  manifest: SceneManifestEntry[],
  nUes: number,
  seed: number,
): SceneManifestEntry | undefined {
  return (
    manifest.find((s) => s.nUes === nUes && s.seed === seed) ??
    manifest.find((s) => s.nUes === nUes)
  );
}
