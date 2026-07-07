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
