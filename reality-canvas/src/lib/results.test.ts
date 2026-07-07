import { describe, expect, it } from "vitest";
import type { JobRelationResult } from "./api";
import { indexResultsByRelation, relationKey, resultColor } from "./results";

const sample: JobRelationResult = {
  source_cell: "CELL_A",
  target_cell: "CELL_B",
  current_cio_db: 2,
  before_success_pct: 60,
  optimal_cio_db: 5,
  after_success_pct: 97,
  improvement_pp: 37,
  source: "counterfactual_sim",
};

describe("relationKey", () => {
  it("joins serving and neighbor cell ids", () => {
    expect(relationKey("CELL_A", "CELL_B")).toBe("CELL_A->CELL_B");
  });
});

describe("indexResultsByRelation", () => {
  it("indexes results by serving->neighbor key", () => {
    const map = indexResultsByRelation([sample]);
    expect(map.get("CELL_A->CELL_B")).toEqual(sample);
    expect(map.size).toBe(1);
  });
});

describe("resultColor", () => {
  it("returns null when no result is mapped for a relation", () => {
    expect(resultColor(undefined, false)).toBeNull();
  });

  it("colors by before_success_pct when showAfter is false", () => {
    // 60% -> red band
    expect(resultColor(sample, false)).toEqual([220, 53, 69, 220]);
  });

  it("colors by after_success_pct when showAfter is true", () => {
    // 97% -> green band
    expect(resultColor(sample, true)).toEqual([40, 200, 120, 220]);
  });
});
