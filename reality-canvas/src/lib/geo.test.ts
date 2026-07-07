import { describe, expect, it } from "vitest";
import { destinationPoint, findScene, frequencyBandColor, sectorWedgePoints, successRateColor } from "./geo";

describe("successRateColor", () => {
  it("returns red below 75%", () => {
    expect(successRateColor(0.5)).toEqual([220, 53, 69, 220]);
  });
  it("returns amber between 75% and 95%", () => {
    const [r, g, b] = successRateColor(0.85);
    expect(b).toBe(0);
    expect(r).toBeGreaterThan(0);
    expect(g).toBeGreaterThan(0);
  });
  it("returns green above 95%", () => {
    expect(successRateColor(0.99)).toEqual([40, 200, 120, 220]);
  });
  it("clamps out-of-range input", () => {
    expect(successRateColor(-1)).toEqual(successRateColor(0));
    expect(successRateColor(2)).toEqual(successRateColor(1));
  });
});

describe("destinationPoint", () => {
  it("moving north increases latitude, keeps longitude ~same", () => {
    const [lat, lon] = destinationPoint(35.66, 139.68, 0, 1000);
    expect(lat).toBeGreaterThan(35.66);
    expect(lon).toBeCloseTo(139.68, 2);
  });
  it("moving east increases longitude, keeps latitude ~same", () => {
    const [lat, lon] = destinationPoint(35.66, 139.68, 90, 1000);
    expect(lon).toBeGreaterThan(139.68);
    expect(lat).toBeCloseTo(35.66, 2);
  });
});

describe("sectorWedgePoints", () => {
  it("returns apex, arc points, and closes back to apex", () => {
    const pts = sectorWedgePoints(35.66, 139.68, 90, 65, 120, 4);
    expect(pts[0]).toEqual([139.68, 35.66]);
    expect(pts[pts.length - 1]).toEqual([139.68, 35.66]);
    expect(pts.length).toBe(1 + 5 + 1); // apex + (steps+1) arc points + closing apex
  });

  it("arc points fall within the azimuth +/- half-beamwidth range", () => {
    const pts = sectorWedgePoints(35.66, 139.68, 0, 60, 120, 6);
    // all arc points (excluding apex bookends) should be north-ish (positive lat delta)
    const arc = pts.slice(1, -1);
    for (const [, lat] of arc) {
      expect(lat).toBeGreaterThanOrEqual(35.66);
    }
  });
});

describe("frequencyBandColor", () => {
  it("is stable for the same band", () => {
    const a = frequencyBandColor("Band 41 (2500MHz)");
    const b = frequencyBandColor("Band 41 (2500MHz)");
    expect(a).toEqual(b);
  });
  it("differs across distinct bands (until palette wraps)", () => {
    const a = frequencyBandColor("Band 3 (1800MHz)");
    const b = frequencyBandColor("Band 78 (3500MHz)");
    expect(a).not.toEqual(b);
  });
});

describe("findScene", () => {
  const manifest = [
    { nUes: 21, seed: 42, file: "scene-21-42.czml" },
    { nUes: 100, seed: 42, file: "scene-100-42.czml" },
    { nUes: 100, seed: 99, file: "scene-100-99.czml" },
    { nUes: 500, seed: 42, file: "scene-500-42.czml" },
  ];

  it("finds exact ues+seed match", () => {
    expect(findScene(manifest, 100, 99)?.file).toBe("scene-100-99.czml");
  });

  it("falls back to any seed for the requested ue count", () => {
    expect(findScene(manifest, 21, 7)?.file).toBe("scene-21-42.czml");
  });

  it("returns undefined when no scene matches the ue count", () => {
    expect(findScene(manifest, 999, 42)).toBeUndefined();
  });
});
