import type { RelationRecord, SiteRecord, Stats } from "../types";

interface CzmlPacket {
  id: string;
  availability?: string;
}

export function computeStats(
  sites: SiteRecord[],
  relations: RelationRecord[],
  czml: CzmlPacket[],
): Stats {
  const siteNames = new Set(sites.map((s) => s.siteName));
  const ueCount = czml.filter(
    (p) => p.id !== "document" && !p.id.startsWith("site/") && !p.id.startsWith("ho/"),
  ).length;
  const handoverCount = czml.filter((p) => p.id.startsWith("ho/")).length;

  return {
    sites: siteNames.size,
    cells: sites.length,
    relations: relations.length,
    ues: ueCount,
    handovers: handoverCount,
  };
}
