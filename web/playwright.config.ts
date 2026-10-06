import { defineConfig, devices } from '@playwright/test';

// MM_E2E_PORT lets parallel worktrees run e2e side by side; each must use its own
// port, or `reuseExistingServer` would test another worktree's Vite.
const port = Number(process.env.MM_E2E_PORT ?? 5174);

// Headless pinning tests for behavior first evaluated headed (F9). The API is
// replaced by recorded fixtures (e2e/fixtures) and card images are stubbed, so
// the suite is offline and deterministic — no `mm serve` or network needed.
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  reporter: [['list']],
  use: {
    baseURL: `http://localhost:${port}`,
    permissions: ['clipboard-read', 'clipboard-write'],
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1600, height: 900 } } }],
  webServer: {
    command: `npx vite --port ${port} --strictPort`,
    url: `http://localhost:${port}`,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
