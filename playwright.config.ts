import { defineConfig } from '@playwright/test';

/** The LOCAL app (single-user tool). The cloud app is a separate config — see
 *  playwright.cloud.config.ts and the note there: Next refuses two `next dev` servers in one
 *  project directory, so the two suites cannot share a config. Mirrors the jest split
 *  (jest.config.ts / jest.integration.config.ts). */
export default defineConfig({
  testDir: './tests/e2e',
  // cloud.* belongs to the cloud config; running it here would hit LocalApp and fail for
  // reasons that have nothing to do with the cloud app.
  testIgnore: /cloud[.-]/,
  outputDir: './test-results',
  use: {
    baseURL: 'http://localhost:3000',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
});
