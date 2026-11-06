import { defineConfig, devices } from "@playwright/test"

/**
 * End-to-end smoke tests run against the real FastAPI + Vite stack.
 * Both servers are started automatically unless already running.
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], channel: "chromium" },
    },
  ],
  webServer: [
    {
      command: "./venv/bin/uvicorn main:app --port 8000",
      cwd: "../api",
      url: "http://127.0.0.1:8000/",
      reuseExistingServer: true,
      timeout: 60_000,
    },
    {
      command: "npm run dev -- --port 5173",
      url: "http://127.0.0.1:5173/",
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
})
