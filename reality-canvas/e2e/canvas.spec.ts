import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ARTIFACTS_DIR = path.join(__dirname, "..", "e2e-artifacts");

async function login(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.getByLabel("Enter demo password").fill("Winniio-2019");
  await page.getByRole("button", { name: "Enter" }).click();
  await expect(page.getByTestId("cesium-container")).toBeVisible({ timeout: 15_000 });
}

test.beforeAll(() => {
  fs.mkdirSync(ARTIFACTS_DIR, { recursive: true });
});

test("app loads and renders the Cesium canvas", async ({ page }) => {
  await login(page);
  const canvas = page.locator("#main canvas").first();
  await expect(canvas).toBeVisible({ timeout: 15_000 });
  await page.screenshot({ path: path.join(ARTIFACTS_DIR, "loaded.png") });
});

test("clicking play toggles clock.shouldAnimate", async ({ page }) => {
  await login(page);
  await page.waitForFunction(() => Boolean((window as any).__viewer));

  const before = await page.evaluate(() => (window as any).__viewer.clock.shouldAnimate);

  // Invoke the "Play Forward" command bound to the Animation widget's play button —
  // this is the exact code path the button's onclick handler triggers via knockout.
  await page.evaluate(() => {
    const vm = (window as any).__viewer.animation.viewModel;
    vm.playForwardViewModel._command();
  });

  await page.waitForTimeout(300);
  const after = await page.evaluate(() => (window as any).__viewer.clock.shouldAnimate);
  expect(after).not.toBe(before);
});

test("changing the UE-count slider switches the czml source", async ({ page }) => {
  await login(page);
  await page.waitForFunction(() => Boolean((window as any).__viewer));

  const select = page.locator("#ue-count");
  await select.selectOption("500");
  await page.waitForTimeout(1000);

  const ueCount = await page.evaluate(() => {
    const viewer = (window as any).__viewer;
    let count = 0;
    for (const ds of viewer.dataSources._dataSources ?? []) {
      if (ds.name && ds.name !== "beams" && ds.name !== "relations") {
        for (const e of ds.entities.values) {
          if (e.id !== "document" && !e.id.startsWith("site/") && !e.id.startsWith("ho/")) count++;
        }
      }
    }
    return count;
  });
  expect(ueCount).toBeGreaterThan(100);
});

test("dim-basemap toggle changes imagery alpha", async ({ page }) => {
  await login(page);
  await page.waitForFunction(() => Boolean((window as any).__viewer));

  const before = await page.evaluate(
    () => (window as any).__viewer.imageryLayers.get(0).alpha,
  );
  await page.getByLabel("Dim basemap").click();
  await page.waitForTimeout(200);
  const after = await page.evaluate(
    () => (window as any).__viewer.imageryLayers.get(0).alpha,
  );
  expect(after).not.toBe(before);
});

test("unchecking relations layer hides polylines", async ({ page }) => {
  await login(page);
  await page.waitForFunction(() => Boolean((window as any).__viewer));

  await page.getByLabel("Neighbor relations").click();
  await page.waitForTimeout(200);
  const anyVisible = await page.evaluate(() => {
    const viewer = (window as any).__viewer;
    const relDs = viewer.dataSources._dataSources.find((d: any) => d.name === "relations");
    if (!relDs) return true;
    return relDs.entities.values.some((e: any) => e.show);
  });
  expect(anyVisible).toBe(false);
});

// ── P4: live API mode ──
//
// The dev server (see playwright.config.ts webServer.env) always bakes in
// VITE_API_URL=http://localhost:8601 — an address nothing listens on. That
// means every test above naturally exercises the "API unreachable, offline
// fallback" path with zero extra setup. The tests below mock that exact
// origin with page.route so live mode can be exercised without a real
// backend process.

const API = "http://localhost:8601";

const FAKE_CZML = [
  { id: "document", name: "e2e-live", version: "1.0" },
  {
    id: "site/RKSB-001-1",
    position: { cartographicDegrees: [139.68735, 35.662183, 30] },
    point: { pixelSize: 8 },
  },
];

function mockHealthOk(page: import("@playwright/test").Page) {
  return page.route(`${API}/`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "healthy" }) }),
  );
}

function mockCzml(page: import("@playwright/test").Page) {
  return page.route(`${API}/api/v1/czml**`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(FAKE_CZML) }),
  );
}

test("offline mode: API unreachable, mode indicator shows offline, scenes still render", async ({ page }) => {
  await login(page);
  await expect(page.getByTestId("cesium-container")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("mode-indicator")).toHaveText("Pre-generated (offline)");
  await expect(
    page.getByText("MRO Optimization requires the live API — offline mode active."),
  ).toBeVisible();
});

test("live mode: healthy API flips the mode indicator and enables the simulate button", async ({ page }) => {
  await mockHealthOk(page);
  await mockCzml(page);
  await login(page);
  await expect(page.getByTestId("mode-indicator")).toHaveText("Live API", { timeout: 10_000 });
  await expect(page.getByRole("button", { name: "Run MRO Optimization (synthetic)" })).toBeVisible();
});

test("live mode: simulate button shows the summary card with the honesty banner", async ({ page }) => {
  await mockHealthOk(page);
  await mockCzml(page);
  await page.route(`${API}/api/v1/simulate`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        job_id: "e2e-job-1",
        status: "done",
        summary: {
          relations: 2,
          avg_before: 81.0,
          avg_after: 96.5,
          banner: "NOT_A_PERFORMANCE_CLAIM — synthetic counterfactuals",
        },
      }),
    }),
  );
  await page.route(`${API}/api/v1/jobs/e2e-job-1/result`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          source_cell: "RKSB-001-1",
          target_cell: "RKSB-001-2",
          current_cio_db: 2,
          before_success_pct: 81.61,
          optimal_cio_db: 6,
          after_success_pct: 98.0,
          improvement_pp: 16.39,
          source: "counterfactual_sim",
        },
      ]),
    }),
  );

  await login(page);
  await expect(page.getByTestId("mode-indicator")).toHaveText("Live API", { timeout: 10_000 });

  await page.getByRole("button", { name: "Run MRO Optimization (synthetic)" }).click();
  await expect(page.getByTestId("simulate-summary")).toBeVisible({ timeout: 10_000 });
  await expect(
    page.getByText("NOT_A_PERFORMANCE_CLAIM — synthetic counterfactuals"),
  ).toBeVisible();
});

test("live mode: before/after toggle recolors the mapped relation polyline", async ({ page }) => {
  await mockHealthOk(page);
  await mockCzml(page);
  await page.route(`${API}/api/v1/simulate`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        job_id: "e2e-job-2",
        status: "done",
        summary: { relations: 1, avg_before: 81.61, avg_after: 98.0, banner: "NOT_A_PERFORMANCE_CLAIM" },
      }),
    }),
  );
  await page.route(`${API}/api/v1/jobs/e2e-job-2/result`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          // matches the first entry in public/data/relations.json (before=81.61% -> amber,
          // after=98% -> green), so the toggle produces a visibly different color.
          source_cell: "RKSB-001-1",
          target_cell: "RKSB-001-2",
          current_cio_db: 2,
          before_success_pct: 81.61,
          optimal_cio_db: 6,
          after_success_pct: 98.0,
          improvement_pp: 16.39,
          source: "counterfactual_sim",
        },
      ]),
    }),
  );

  await login(page);
  await expect(page.getByTestId("mode-indicator")).toHaveText("Live API", { timeout: 10_000 });
  await page.getByRole("button", { name: "Run MRO Optimization (synthetic)" }).click();
  await expect(page.getByTestId("simulate-summary")).toBeVisible({ timeout: 10_000 });

  const relationColor = () =>
    page.evaluate(() => {
      const viewer = (window as any).__viewer;
      const relDs = viewer.dataSources._dataSources.find((d: any) => d.name === "relations");
      const entity = relDs.entities.getById("relation/RKSB-001-1->RKSB-001-2");
      const c = entity.polyline.material.color.getValue(viewer.clock.currentTime);
      return [c.red, c.green, c.blue, c.alpha];
    });

  const beforeColor = await relationColor();
  // Button label is the destination state, so from the initial "before" view
  // the button reads "Show: After".
  await page.getByRole("button", { name: "Show: After" }).click();
  await page.waitForTimeout(200);
  const afterColor = await relationColor();
  expect(afterColor).not.toEqual(beforeColor);
});
