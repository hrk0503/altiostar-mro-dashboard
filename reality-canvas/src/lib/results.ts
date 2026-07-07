import type { JobRelationResult } from "./api";
import { successRateColor } from "./geo";

/** relationKey used both here and in CesiumCanvas entity ids: "src->tgt". */
export function relationKey(servingCell: string, neighborCell: string): string {
  return `${servingCell}->${neighborCell}`;
}

export type RelationResultMap = Map<string, JobRelationResult>;

/** Index a simulate job's per-relation results by "serving->neighbor" for O(1) lookup. */
export function indexResultsByRelation(results: JobRelationResult[]): RelationResultMap {
  const map: RelationResultMap = new Map();
  for (const r of results) {
    map.set(relationKey(r.source_cell, r.target_cell), r);
  }
  return map;
}

/** RGBA color for a relation given the before/after toggle state. Falls back to `null` if unmapped. */
export function resultColor(
  result: JobRelationResult | undefined,
  showAfter: boolean,
): [number, number, number, number] | null {
  if (!result) return null;
  const pct = showAfter ? result.after_success_pct : result.before_success_pct;
  return successRateColor(pct / 100);
}
