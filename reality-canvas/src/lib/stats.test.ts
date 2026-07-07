import { describe, expect, it } from "vitest";
import { computeStats } from "./stats";
import type { RelationRecord, SiteRecord } from "../types";

const sites: SiteRecord[] = [
  { cellId: "A-1", siteName: "Site-A", latitude: 0, longitude: 0, antennaHeightM: 30, azimuthDeg: 0, beamwidthDeg: 65, frequencyBand: "B1", technology: "LTE", status: "Active" },
  { cellId: "A-2", siteName: "Site-A", latitude: 0, longitude: 0, antennaHeightM: 30, azimuthDeg: 120, beamwidthDeg: 65, frequencyBand: "B1", technology: "LTE", status: "Active" },
  { cellId: "B-1", siteName: "Site-B", latitude: 1, longitude: 1, antennaHeightM: 30, azimuthDeg: 0, beamwidthDeg: 65, frequencyBand: "B1", technology: "LTE", status: "Active" },
];

const relations: RelationRecord[] = [
  { servingCell: "A-1", neighborCell: "A-2", servingLat: 0, servingLon: 0, neighborLat: 0, neighborLon: 0, relationType: "Intra", successRate: 0.9 },
];

const czml = [
  { id: "document" },
  { id: "site/Site-A" },
  { id: "site/Site-B" },
  { id: "UE-1" },
  { id: "UE-2" },
  { id: "ho/0" },
  { id: "ho/1" },
];

describe("computeStats", () => {
  it("counts distinct sites, all cells, relations, UEs, and handovers", () => {
    expect(computeStats(sites, relations, czml)).toEqual({
      sites: 2,
      cells: 3,
      relations: 1,
      ues: 2,
      handovers: 2,
    });
  });
});
