import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright configuration for cs2-analytics frontend E2E tests.
 *
 * Local prerequisites (NOT auto-started by this config):
 *   1. Backend running:   cd packages/backend && uv run uvicorn src.main:app --reload
 *      (or `docker compose -f infra/docker-compose.yml up -d` for postgres+redis+api)
 *   2. Frontend running:  cd packages/frontend && pnpm dev
 *      (or `pnpm build && pnpm start` for prod-mode E2E)
 *
 * Environment variables:
 *   PLAYWRIGHT_BASE_URL      — frontend URL (default http://localhost:3000)
 *   PLAYWRIGHT_API_BASE_URL  — backend URL  (default http://localhost:8000)
 *   E2E_USER_EMAIL           — pre-existing user email (optional, falls back to per-test register)
 *   E2E_USER_PASSWORD        — pre-existing user password
 *   CI                       — when set, enables retries and fail-on-only
 *
 * The config does NOT use `webServer` so the dev/prod server lifecycle is owned
 * by the developer (or the CI workflow). This avoids slow cold starts on every
 * `playwright test` invocation and allows running against any environment.
 */

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000'

export default defineConfig({
  testDir: './e2e',
  testMatch: ['**/*.spec.ts'],
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 2,
  workers: process.env.CI ? 1 : undefined,
  timeout: 30_000,
  expect: {
    timeout: 5_000,
  },
  reporter: process.env.CI
    ? [['html', { open: 'never' }], ['list']]
    : [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: BASE_URL,
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
    video: 'retain-on-failure',
    actionTimeout: 10_000,
    navigationTimeout: 15_000,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
