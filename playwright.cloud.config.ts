import { defineConfig } from '@playwright/test';

/**
 * M3.1-A — browser-level e2e for the CLOUD app, against a local Supabase stack.
 *
 *     npx playwright test --config playwright.cloud.config.ts
 *
 * WHY A SECOND CONFIG RATHER THAN A SECOND PROJECT IN THE FIRST ONE.
 * `/` dispatches between two whole applications on a RUNTIME env var (app/page.tsx reads
 * STORAGE_BACKEND), so the cloud suite needs its own server with that var set. The obvious shape
 * — one config, two `webServer` entries — was tried and DOES NOT WORK: Next refuses to run two
 * `next dev` servers in the same project directory whatever port they are given
 * ("Another next dev server is already running", measured 2026-08-13). Splitting the config makes
 * the conflict impossible instead of intermittent, and mirrors the existing jest split.
 *
 * WHY NOT THE DEPLOYED URL. M3.1 asks for the deployed URL and that cannot be automated:
 * `/dev-login` is 404 in prod by design (a security gate with deploy guards) and Google OAuth
 * cannot be driven by Playwright. A prod read-only smoke using a manually captured session is
 * tracked separately as M3.1-B. What THIS config buys is the thing a manual pass cannot:
 * it runs unattended, every time, for free.
 *
 * NO MONEY IS SPENT ANYWHERE IN THIS SUITE, and `globalSetup` MEASURES that rather than asserting
 * it — see tests/e2e/cloud-global.ts. It reads the spend ledger before any project runs and checks
 * it again as the run's teardown, so the window covers the setup project too and survives a setup
 * failure that stops the dependent project from ever being scheduled.
 */
export default defineConfig({
  testDir: './tests/e2e',
  outputDir: './test-results',
  // The run-level money guard, and the reason a stale fixture cannot be read: it deletes both
  // fixture files on every invocation that reaches it — including a partial
  // `--project=cloud --no-deps` one. It does NOT reach that far if the webServer fails to start,
  // because plugin setup is ordered first; cloud-global.ts has the full list of what it cannot see.
  globalSetup: './tests/e2e/cloud-global.ts',
  // Local Supabase is one shared stack — parallel specs would race each other's rows.
  workers: 1,
  use: {
    baseURL: 'http://localhost:3001',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'setup', testMatch: /cloud\.setup\.ts$/ },
    {
      name: 'cloud',
      testMatch: /cloud-.*\.spec\.ts$/,
      dependencies: ['setup'],
      use: { storageState: 'playwright/.auth/cloud-user.json' },
    },
  ],
  webServer: {
    // DEV_LOGIN_ENABLED is safe here and only here: lib/supabase/dev-login.ts fails closed unless
    // the flag is true AND the runtime Supabase URL is local, so it cannot open against prod.
    command: 'STORAGE_BACKEND=supabase DEV_LOGIN_ENABLED=true next dev --port 3001',
    url: 'http://localhost:3001/login',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
