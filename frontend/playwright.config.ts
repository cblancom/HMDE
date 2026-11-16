import { defineConfig, devices } from '@playwright/test'
import process from 'node:process'

const apiPort = 8011
const webPort = 5183

export default defineConfig({
  testDir: './e2e',
  testIgnore: ['**/performance.spec.ts'],
  fullyParallel: false,
  workers: process.env.CI ? 1 : undefined,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: `http://127.0.0.1:${webPort}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    viewport: { width: 1440, height: 900 },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: `cd ../backend && uv run uvicorn hmde.main:app --host 127.0.0.1 --port ${apiPort}`,
      url: `http://127.0.0.1:${apiPort}/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        DATABASE_URL:
          process.env.E2E_DATABASE_URL ??
          'postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde_e2e',
        APP_ENV: 'test',
        LOG_LEVEL: 'WARNING',
        CORS_ORIGINS: `http://127.0.0.1:${webPort}`,
      },
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${webPort} --strictPort`,
      url: `http://127.0.0.1:${webPort}/bands`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        VITE_API_PROXY_TARGET: `http://127.0.0.1:${apiPort}`,
      },
    },
  ],
})
