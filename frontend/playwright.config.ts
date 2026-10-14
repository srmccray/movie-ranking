import { defineConfig, devices } from '@playwright/test'

// Dedicated ports so e2e never collides with (or reuses) a dev server that is
// pointed at real data.
const FRONTEND_PORT = 3100
const BACKEND_PORT = 8100
const BASE_URL = `http://localhost:${FRONTEND_PORT}`

export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.spec.ts',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  timeout: 30_000,
  expect: { timeout: 5_000 },
  reporter: process.env.CI
    ? [['list'], ['html', { open: 'never' }]]
    : [['list']],
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    actionTimeout: 10_000,
    navigationTimeout: 15_000,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      // Real FastAPI app on a throwaway SQLite file (see e2e/support/run_backend.py).
      command: `PYTHONPATH=. venv/bin/python frontend/e2e/support/run_backend.py ${BACKEND_PORT}`,
      cwd: '..',
      url: `http://127.0.0.1:${BACKEND_PORT}/openapi.json`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      // Real Vite dev server, proxying /api to the e2e backend.
      command: `npx vite --port ${FRONTEND_PORT} --strictPort`,
      url: BASE_URL,
      reuseExistingServer: false,
      timeout: 60_000,
      env: { API_PROXY_TARGET: `http://127.0.0.1:${BACKEND_PORT}` },
    },
  ],
})
