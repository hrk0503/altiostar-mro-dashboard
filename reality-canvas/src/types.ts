export interface SiteRecord {
  cellId: string;
  siteName: string;
  latitude: number;
  longitude: number;
  antennaHeightM: number;
  azimuthDeg: number;
  beamwidthDeg: number;
  frequencyBand: string;
  technology: string;
  status: string;
}

export interface RelationRecord {
  servingCell: string;
  neighborCell: string;
  servingLat: number;
  servingLon: number;
  neighborLat: number;
  neighborLon: number;
  relationType: string;
  successRate: number; // 0..1
}

export interface SceneManifestEntry {
  nUes: number;
  seed: number;
  file: string;
}

export interface Stats {
  sites: number;
  cells: number;
  relations: number;
  ues: number;
  handovers: number;
}
