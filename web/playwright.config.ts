import { defineConfig } from '@playwright/test';

const port = Number(process.env.WEB_PORT ?? 3100);

export default defineConfig({
  testDir: 'tests/e2e',
  use: {
    baseURL: process.env.WEB_BASE_URL ?? `http://localhost:${port}`,
    // Point at a system Chrome where the bundled browser cannot run (for example NixOS).
    launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROME_PATH || undefined },
  },
  // The app must be built first (`pnpm build`).
  webServer: process.env.WEB_BASE_URL
    ? undefined
    : {
        command: `pnpm exec next start -p ${port}`,
        url: `http://localhost:${port}`,
        reuseExistingServer: !process.env.CI,
        env: { LIVEKIT_URL: '', LIVEKIT_API_KEY: '', LIVEKIT_API_SECRET: '' },
      },
});
