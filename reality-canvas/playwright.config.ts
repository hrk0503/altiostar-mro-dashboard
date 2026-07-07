import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:5183",
    screenshot: "on",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "npm run dev -- --port 5183",
    url: "http://localhost:5183",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
    // P4: bake a fake live-API config into the dev build so e2e tests can
    // exercise the live-mode UI by mocking these exact URLs via page.route —
    // no real backend needed. Points at an address nothing listens on; every
    // test that exercises live mode MUST mock the routes it needs.
    env: {
      VITE_API_URL: "http://localhost:8601",
      VITE_API_TOKEN: "e2e-test-token",
    },
  },
});
