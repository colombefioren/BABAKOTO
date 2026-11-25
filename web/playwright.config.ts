import { randomBytes } from 'node:crypto';
import { defineConfig } from '@playwright/test';

const password = process.env.WEB_BASE_URL
  ? process.env.WEB_PLAYGROUND_PASSWORD
  : (process.env.BABAKOTO_E2E_PLAYGROUND_PASSWORD ??= randomBytes(32).toString('hex'));
const port = Number(process.env.WEB_PORT ?? 3100);

export default defineConfig({
  testDir: 'tests/e2e',
  use: {
    baseURL: process.env.WEB_BASE_URL ?? `http://localhost:${port}`,
    httpCredentials: { username: 'babakoto', password: password ?? '' },
    // Point at a system Chrome where the bundled browser cannot run (for example NixOS).
    launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROME_PATH || undefined },
  },
  // The app must be built first (`pnpm build`).
  webServer: process.env.WEB_BASE_URL
    ? undefined
    : {
        command: `pnpm exec next start -p ${port}`,
        url: `http://localhost:${port}`,
        reuseExistingServer: false,
        env: {
          WEB_PLAYGROUND_PASSWORD: password ?? '',
          LIVEKIT_URL: '',
          LIVEKIT_API_KEY: '',
          LIVEKIT_API_SECRET: '',
        },
      },
});
