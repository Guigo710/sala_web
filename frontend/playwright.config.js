import { defineConfig, devices } from '@playwright/test';

/**
 * E2E contra o sistema real (frontend + API + Postgres com seed). Ver e2e/README.md.
 *   E2E_BASE_URL  frontend (padrão http://localhost:5173)
 *   E2E_API_URL   API      (padrão http://localhost:8000)
 *   E2E_ADMIN_RM / E2E_ADMIN_SENHA  admin do seed (padrão ADMIN_RM / ADMIN_SENHA)
 *   E2E_SCREENSHOTS pasta para as capturas do fluxo (padrão test-results/telas)
 */
export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.spec.js',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [['list']],
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:5173',
    locale: 'pt-BR',
    timezoneId: 'America/Sao_Paulo',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
